from collections import defaultdict, deque
from typing import Dict, List

import matplotlib.pyplot as plt
import networkx as nx

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.exceptions.column_positioner import MaxColumnPositionLimitExceeded, RootNodesNotFound
from diagramforge.schema.shapes import CollapsedPool, Event, Pool
from diagramforge.SETUP import forge_logger
from diagramforge.transformation.rule_book import RuleBook


class ColumnPositioner:
    """Positions nodes in a diagram's graph by columns using BFS and rule-based heuristics."""

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        """Initializes the ColumnPositioner with the given graph.

        Args:
            graph (nx.MultiDiGraph): The graph to be processed

        Populates:
            bfs_with_levels (Dict[str, List[str]]): A dictionary of nodes grouped by level
            graph_cycles_sorted_desc (List[List[str]]): A list of graph cycles sorted by length
            bpmn_adjusted_columns (Dict[int, List[str]]): A dictionary of nodes grouped by column
        """
        self.G: nx.MultiDiGraph = graph
        self.placed_nodes: set[str] = set()

        # Cross-methodical class instance variables in order of usage
        self.removed_edges: List[tuple[str, str]] = []
        self.main_start_events: List[str] = []
        self.secondary_start_events: List[str] = []
        self.bfs_with_levels: Dict[str, List[str]] = None
        self.graph_cycles_sorted_desc: List[List[str]] = None
        self.bpmn_adjusted_columns: Dict[int, List[str]] = None

    def position_columns(self) -> Dict[str, List[str]]:
        """Executes the entire integrated column positioning process."""

        # Remove edges between pools and events to allow events to be seen as start nodes.
        self.__remove_and_store_pool_event_edges()

        # Identify main vs. secondary start events using intelligent DAG analysis.
        self.__determine_main_start_event_via_intelligent_dag()

        # Create a provisional layout with only the main flow.
        self.__layout_main_flow_with_bfs()

        # Inject secondary flows into the layout plan with correct spacing.
        self.__inject_secondary_flows_into_bfs_levels()

        # Run the RuleBook on the final, unified layout plan to get the near-final columns.
        self.__recalculate_columns_with_rulebook()

        # Perform the final cleanup pass to fix any gaps for secondary start events.
        self.__reposition_secondary_start_events_post_rules()

        # Restore previously removed edges to maintain original graph integrity.
        for source, target in self.removed_edges:
            self.G.add_edge(source, target)

        return self.bpmn_adjusted_columns

    def __remove_and_store_pool_event_edges(self):
        for source, target, _ in self.G.edges:
            source_node_shape = self.G.nodes[source].get("shape")
            target_node_shape = self.G.nodes[target].get("shape")

            # Remove edges from pools to events
            if isinstance(source_node_shape, (Pool, CollapsedPool)) and isinstance(target_node_shape, Event):
                self.removed_edges.append((source, target))

        for source, target in self.removed_edges:
            if self.G.has_edge(source, target):
                self.G.remove_edge(source, target)

    def __determine_main_start_event_via_intelligent_dag(self):
        """
        Determines the main start event using a definitive, BPMN-aware method.
        It identifies and removes only true back-edges, then finds the longest path
        that is guaranteed to start from a valid start event.
        """

        all_start_nodes = [n for n in self.G.nodes() if self.G.in_degree(n) == 0]
        if not all_start_nodes:
            raise RootNodesNotFound()
        if len(all_start_nodes) == 1:
            self.main_start_events = all_start_nodes
            self.secondary_start_events = []
            return

        try:
            # Check for cycles in the graph
            cycles = [c for c in nx.simple_cycles(self.G)]

            back_edges = []

            if cycles:
                # Discover Process Levels and Identify Back-Edges
                levels = {}
                queue = deque([(node, 0) for node in all_start_nodes])
                visited_for_leveling = set(all_start_nodes)

                for node in all_start_nodes:
                    levels[node] = 0
                while queue:
                    node, level = queue.popleft()
                    for successor in self.G.successors(node):
                        if successor not in visited_for_leveling:
                            visited_for_leveling.add(successor)
                            levels[successor] = level + 1
                            queue.append((successor, level + 1))

                for u, v in self.G.edges():
                    # An edge is a back-edge if it goes to the same or an earlier level.
                    # We need to handle nodes that might not be reachable from any start event.
                    if levels.get(u, -1) >= levels.get(v, -1) and levels.get(v, -1) != -1:
                        back_edges.append((u, v))
                        forge_logger.debug(f"Identified back-edge: {u} -> {v}")

                forge_logger.debug(f"Identified {len(back_edges)} true back-edges to remove for analysis.")

            # Create a "Pure Forward Flow" DAG
            dag_proxy = self.G.copy()
            dag_proxy.remove_edges_from(back_edges)

            # Find the longest path starting from each valid start event.
            longest_path_found = []
            max_len = -1

            for start_node in all_start_nodes:
                # Create a subgraph containing only nodes reachable from this specific start_node in the DAG
                # This is crucial to ensure paths are evaluated correctly.
                try:
                    descendants = nx.descendants(dag_proxy, start_node)
                    nodes_for_subgraph = descendants | {start_node}
                    subgraph = dag_proxy.subgraph(nodes_for_subgraph)

                    # Find the longest path within this start-event-specific subgraph
                    path = nx.dag_longest_path(subgraph)

                    if len(path) > max_len:
                        max_len = len(path)
                        longest_path_found = path
                except nx.NetworkXUnfeasible:  # Happens if a start node has no paths in the DAG
                    if max_len == -1:  # If this is the first start node and it has no paths
                        max_len = 0
                        longest_path_found = [start_node]
                    continue

            if longest_path_found:
                self.main_start_events = [longest_path_found[0]]
            else:
                # This is a safety fallback, but the logic above should prevent it.
                raise Exception("Could not determine a valid main path.")

        except Exception as e:
            forge_logger.error(
                f"A critical error occurred during intelligent DAG analysis: {e}. Reverting to fallback."
            )
            raise NotImplementedError(
                "The intelligent DAG analysis method is not fully implemented yet. Fallback to simpler heuristics."
            )
            # TODO Implement a more robust fallback mechanism
            # self.__fallback_to_descendants(all_start_nodes)

        self.secondary_start_events = [n for n in all_start_nodes if n not in self.main_start_events]
        forge_logger.success(f"Definitive main start event identified: {self.main_start_events}")

    def __layout_main_flow_with_bfs(self):
        """Creates a PROVISIONAL self.bfs_with_levels containing only the main flow."""
        if not self.main_start_events:
            return

        queue = deque()
        visited = set()

        self.bfs_with_levels = defaultdict(list)

        for node in self.main_start_events:
            queue.append((node, 0))
            visited.add(node)

        while queue:
            node, level = queue.popleft()
            self.bfs_with_levels.setdefault(level, []).append(node)
            for successor in self.G.successors(node):
                if successor not in visited:
                    visited.add(successor)
                    queue.append((successor, level + 1))
        forge_logger.debug("Provisional layout of main flow complete.")

    def __inject_secondary_flows_into_bfs_levels(self):
        """
        Takes the provisional layout containing the main flow and intelligently merges in all secondary flows.

        This method works by:
        1. Identifying where each secondary flow "connects" to the main flow by checking the column/level of its successors.
        2. Calculating the correct starting column for the secondary start event (typically one column before its first successor).
        3. Performing a separate BFS for each secondary flow, starting at its calculated column, and adding its nodes
           to the main `self.bfs_with_levels` structure.
        """
        if not self.secondary_start_events:
            forge_logger.debug("No secondary flows to inject.")
            return

        forge_logger.debug(f"Starting injection of {len(self.secondary_start_events)} secondary flows...")

        # Helper to find a node's level in the provisional layout created from the main flow.
        def get_provisional_level(node_id: str) -> int | None:
            for level, nodes in self.bfs_with_levels.items():
                if node_id in nodes:
                    return level
            return None

        # Pre-populate a set of all nodes that are already part of the main flow.
        # This is critical to ensure we don't re-process or misplace these nodes.
        visited = {node for nodes in self.bfs_with_levels.values() for node in nodes}

        for start_node in self.secondary_start_events:
            # A secondary start event should, by definition, not be in the main flow.
            # This is a safety check.
            if start_node in visited:
                continue

            successors = list(self.G.successors(start_node))

            # Case 1: The secondary start event is isolated or starts a completely separate flow.
            if not successors:
                # If isolated, place it in column 0 by default.
                self.bfs_with_levels[0].append(start_node)
                visited.add(start_node)
                forge_logger.debug(f"Placed isolated secondary start node {start_node} in column 0.")
                continue

            # Case 2: The secondary flow connects to the main flow.
            # Find the minimum column/level among all successors that exist in the main flow.
            min_successor_level = float("inf")
            for succ in successors:
                level = get_provisional_level(succ)
                if level is not None:
                    min_successor_level = min(min_successor_level, level)

            # Calculate the target starting column. If no successors connect to the main flow,
            # it's treated as a separate flow and starts at column 0.
            start_level = max(0, min_successor_level - 1) if min_successor_level != float("inf") else 0
            forge_logger.debug(f"Secondary start node {start_node} will be injected starting at column {start_level}.")

            # Now, perform a targeted BFS for this secondary flow and merge its nodes into the main layout plan.
            queue = deque([(start_node, start_level)])

            # Add the start node itself to the visited set and the layout plan.
            visited.add(start_node)
            self.bfs_with_levels[start_level].append(start_node)

            while queue:
                node, level = queue.popleft()
                for successor in self.G.successors(node):
                    if successor not in visited:
                        visited.add(successor)
                        target_level = level + 1
                        # Ensure the list for the target level exists before appending.
                        self.bfs_with_levels.setdefault(target_level, []).append(successor)
                        queue.append((successor, target_level))

        forge_logger.success("All secondary flows have been successfully integrated into the layout plan.")

    def __recalculate_columns_with_rulebook(self) -> None:
        """Recalculates column positioning using sorting of graph cycles and applying a set of rules.

        Raises:
            MaxColumnPositionLimitExceeded: If the iteration limit is exceeded during column positioning.
        """
        forge_logger.debug("Recalculating columns")

        self.graph_cycles_sorted_desc = sorted(nx.recursive_simple_cycles(self.G), key=len, reverse=True)

        self.bpmn_adjusted_columns = defaultdict(list)

        level = 0
        level_nodes_queue = deque(self.bfs_with_levels[level])

        placed_nodes = set()

        while level_nodes_queue:
            node: str = level_nodes_queue.popleft()

            RB = RuleBook(
                G=self.G,
                graph_cycles_sorted_desc=self.graph_cycles_sorted_desc,
                bfs_with_levels=self.bfs_with_levels,
                node=node,
                bpmn_adjusted_columns=self.bpmn_adjusted_columns,
                placed_nodes=placed_nodes,
                level=level,
            )

            forge_logger.debug(f"Processing node {node} with at level {level}")

            if RB.RULE_0():
                forge_logger.debug(f"RULE 0 applied to node {node}")

            elif RB.RULE_1():
                forge_logger.debug(f"RULE 1 applied to node {node}")

            elif RB.RULE_2():
                forge_logger.debug(f"RULE 2 applied to node {node}")

            elif RB.RULE_3():
                forge_logger.debug(f"RULE 3 applied to node {node}")

            elif RB.RULE_4():
                forge_logger.debug(f"RULE 4 applied to node {node}")

            elif RB.RULE_5():
                forge_logger.debug(f"RULE 5 applied to node {node}")

            elif RB.RULE_6():
                forge_logger.debug(f"RULE 6 applied to node {node}")

            elif RB.RULE_7():
                forge_logger.debug(f"RULE 7 applied to node {node}")

            elif RB.FALLBACK():
                pass

            else:
                forge_logger.debug(f"Node {node} could not be placed at level {level}")
                if node not in placed_nodes:
                    self.bfs_with_levels[level + 1].append(node)

            if not level_nodes_queue and level < len(self.bfs_with_levels) - 1:
                level += 1
                level_nodes_queue = deque(self.bfs_with_levels[level])

            if level > FORGE_CONFIG.COLUMN_POSITIONING_MAX_ITERATIONS:
                raise MaxColumnPositionLimitExceeded()

        forge_logger.debug(f"Column positioning complete. Columns: {len(self.bpmn_adjusted_columns)}")

    def __reposition_secondary_start_events_post_rules(self):
        """
        Final cleanup step. Iterates through all secondary start events and adjusts their
        final column position in `bpmn_adjusted_columns` to be immediately before their
        closest successor, correcting any gaps introduced by the RuleBook.
        """
        forge_logger.debug("Starting final repositioning of secondary start events...")
        if not self.secondary_start_events:
            return

        # For efficient lookups, create a reverse map from a node ID to its final column.
        node_to_column_map = {node: col for col, nodes in self.bpmn_adjusted_columns.items() for node in nodes}

        nodes_to_move = []

        # First, determine the new position for each node without modifying the dictionary in-place.
        for start_node in self.secondary_start_events:
            successors = list(self.G.successors(start_node))
            if not successors:
                continue  # This node has nothing to align to, so leave it.

            # Find the minimum column index among all successors.
            min_successor_col = float("inf")
            for succ in successors:
                succ_col = node_to_column_map.get(succ)
                if succ_col is not None:
                    min_successor_col = min(min_successor_col, succ_col)

            # If none of its successors were placed, we can't align it.
            if min_successor_col == float("inf"):
                continue

            # Calculate the desired new column.
            target_col = max(0, min_successor_col - 1)

            # Get the node's current column.
            current_col = node_to_column_map.get(start_node)

            # If it's not in the map or already in the right place, do nothing.
            if current_col is None or current_col == target_col:
                continue

            # Schedule the move.
            nodes_to_move.append({"node": start_node, "from_col": current_col, "to_col": target_col})

        # Now, execute all the scheduled moves.
        if not nodes_to_move:
            forge_logger.debug("All secondary start events are already in their optimal positions.")
            return

        for move in nodes_to_move:
            node = move["node"]
            from_col = move["from_col"]
            to_col = move["to_col"]

            # Perform the move in the final data structure.
            if node in self.bpmn_adjusted_columns[from_col]:
                self.bpmn_adjusted_columns[from_col].remove(node)
                # If the old column is now empty, remove it to keep things clean.
                if not self.bpmn_adjusted_columns[from_col]:
                    del self.bpmn_adjusted_columns[from_col]

            self.bpmn_adjusted_columns.setdefault(to_col, []).append(node)
            forge_logger.debug(f"Repositioned node '{node}' from column {from_col} to {to_col}.")

        forge_logger.success("Final cleanup of secondary start events complete.")
