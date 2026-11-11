from collections import defaultdict
from enum import Enum
from typing import Dict, List, Set, Union

import networkx as nx

from diagramforge.helpers.general import all_elements_in
from diagramforge.schema.shapes import Association, Event, Gateway, Task
from diagramforge.SETUP import forge_logger


class PlacementResult(Enum):
    """Represents the result of a placement operation within the RuleBook."""

    NODE_SKIPPED = False
    ACTION_PERFORMED = "ACTION_PERFORMED"
    NODE_PLACED = "NODE_PLACED"
    PUSHED_BACK = "PUSHED_BACK"


class RuleBook:
    """Wraps rule-based node placement logic for BFS-based arrangement of BPMN nodes.

    This class applies multiple heuristic rules to determine how nodes should be placed
    in a BFS-driven layout. It checks various predecessor relationships, including cycles,
    to place or push nodes to a certain level in the diagram.

    Attributes:
        G (nx.MultiDiGraph): The directed graph representing diagram nodes.
        graph_cycles_sorted_desc (List[List]): List of graph cycles in descending order of length.
        bfs_with_levels (dict): A BFS-level assignment of nodes before adjustments.
        node (str): Current node under placement consideration.
        bpmn_adjusted_columns (dict): Dictionary mapping levels to lists of nodes after placement.
        placed_nodes (set): Set of node IDs already placed.
        level (int): Current BFS level in the iteration.
    """

    def __init__(
        self,
        G: nx.MultiDiGraph,
        graph_cycles_sorted_desc: List[List],
        bfs_with_levels: Dict[str, List[str]],
        node: str,
        bpmn_adjusted_columns: Dict[int, List[str]],
        placed_nodes: Set[str],
        level: int,
    ):
        """Initializes a RuleBook instance with references to graph structures and BFS context.

        Args:
            G (nx.MultiDiGraph): The directed graph of the diagram.
            graph_cycles_sorted_desc (list): Sorted cycles for cycle detection.
            bfs_with_levels (dict): Original BFS levels.
            node (str): The current node under consideration.
            bpmn_adjusted_columns (dict): Column mappings of levels to nodes for final placement.
            placed_nodes (set): Nodes already placed.
            level (int): The current BFS level.
        """

        self.G = G
        self.bfs_with_levels = bfs_with_levels
        self.graph_cycles_sorted_desc = graph_cycles_sorted_desc
        self.node = node
        self.bpmn_adjusted_columns = bpmn_adjusted_columns
        self.placed_nodes = placed_nodes
        self.level = level

    @property
    def node_shape(self) -> Union[Task, Association, Gateway, Event]:
        """Extracts the shape object of the current node.

        Returns:
            Union[Task, Association, Gateway, Event]: The shape object of the node.
        """

        return self.G.nodes[self.node]["shape"]

    @property
    def node_predecessors(self) -> list:
        """Lists all predecessor nodes of the current node.

        Returns:
            list: Predecessor node IDs.
        """

        return list(self.G.predecessors(self.node))

    @property
    def set_predecessors(self) -> list:
        """Lists predecessor nodes that have already been placed.

        Returns:
            list: The subset of predecessor node IDs that are placed.
        """

        return [n for n in self.node_predecessors if n in self.placed_nodes]

    @property
    def cycling_predecessors(self) -> list:
        """Lists predecessor nodes that are part of a cycle.

        Returns:
            list: The predecessor node IDs present in a graph cycle.
        """
        return [n for n in self.node_predecessors if self.__is_node_in_cycle(n)]

    @property
    def set_and_cycling(self) -> list:
        """Lists nodes that are both placed and in a cycle.

        Returns:
            list: The subset of predecessor node IDs that are placed and also in a cycle.
        """

        return [n for n in self.set_predecessors if n in self.cycling_predecessors]

    @property
    def non_cycling_predecessors(self) -> list:
        """Lists predecessor nodes that are not part of a cycle.

        Returns:
            list: The predecessor node IDs not present in any graph cycle.
        """
        return [n for n in self.node_predecessors if not self.__is_node_in_cycle(n)]

    @property
    def set_and_non_cycling(self) -> list:
        """Lists predecessor nodes that are placed and not part of a cycle.

        Returns:
            list: The subset of predecessor node IDs that are placed and not in a cycle.
        """

        return [n for n in self.set_predecessors if n in self.non_cycling_predecessors]

    def RULE_0(self):
        """Rule 0: Skip node if it has already been placed.

        Returns:
            PlacementResult: NODE_SKIPPED if the node is already placed, otherwise False.
        """
        forge_logger.debug(f"Checking Rule 0 for node {self.node}")
        return PlacementResult.NODE_SKIPPED if self.node in self.placed_nodes else False

    def RULE_1(self):
        """Rule 1: Place node if it has no predecessors (i.e., it is a root node).

        Returns:
            Union[PlacementResult, bool]: NODE_PLACED if placed, otherwise False.
        """

        forge_logger.debug(f"Checking Rule 1 for node {self.node}")

        if not self.node_predecessors:
            forge_logger.debug(f"[RULE 1] Placing node {self.node} at level {self.level}")
            return self.__place_node_at_level_in_bpmn_adjusted()
        else:
            return False

    def RULE_2(self):
        """Rule 2: Place node if all predecessors were placed and current node level is
        greater than the max predecessor level.

        Returns:
            Union[PlacementResult, bool]: NODE_PLACED if placed, or PUSHED_BACK if node level is adjusted, otherwise False.
        """

        forge_logger.debug(f"Checking Rule 2 for node {self.node}")

        if all_elements_in(self.node_predecessors, self.placed_nodes):
            max_pred_level = self.__max_pred_level()

            if max_pred_level is None:
                raise ValueError("Max predecessor level is None")

            if self.level > max_pred_level:
                forge_logger.debug(
                    f"[RULE 2] Placing node {self.node} at level {self.level} since max pred level is {max_pred_level}"
                )
                return self.__place_node_at_level_in_bpmn_adjusted()

        return False

    def RULE_3(self):
        """Rule 3: Check if there are shared paths among cycle paths starting from this node
        and place subsequent nodes along those shared paths.

        Returns:
            Union[PlacementResult, bool]: ACTION_PERFORMED if shared paths found and handled, otherwise False.
        """

        forge_logger.debug(f"Checking Rule 3 for node {self.node}")

        shared_paths = self.__find_maximal_combinations()

        if not shared_paths:
            return False

        forge_logger.debug(f"[RULE 3] Shared paths found for node {self.node}")

        for path in shared_paths:
            level_increment = 0

            for path_node in path:
                if path_node not in self.placed_nodes:
                    path_node_predecessors = list(self.G.predecessors(path_node))
                    min_set_predecessor_level = min(
                        [
                            i
                            for i in [self.__get_level_of_placed_node(n) for n in path_node_predecessors]
                            if i is not None
                        ],
                        default=-1,
                    )

                    set_level = self.level + level_increment
                    set_path_node_at_level = (
                        set_level if set_level > min_set_predecessor_level else min_set_predecessor_level + 1
                    )
                    self.__place_node_at_level_in_bpmn_adjusted(node=path_node, level=set_path_node_at_level)

                level_increment += 1

        return PlacementResult.ACTION_PERFORMED

    def RULE_4(self):
        """Rule 4: Place node after the highest level of a non-cycling predecessor.

        Returns:
            Union[PlacementResult, bool]: NODE_PLACED if placed, otherwise False.
        """

        forge_logger.debug(f"Checking Rule 4 for node {self.node}")

        if self.set_and_non_cycling:
            max_level_of_non_cycling_predecessor = max(
                [self.__get_level_of_placed_node(n) for n in self.set_and_non_cycling], default=None
            )

            if max_level_of_non_cycling_predecessor is None:
                forge_logger.debug("[RULE 4] Non-cycling predecessors - level of placed node is None")
                return False

            return self.__place_node_at_level_in_bpmn_adjusted(level=int(max_level_of_non_cycling_predecessor) + 1)

        return False

    def RULE_5(self):
        """Rule 5: If no suitable non-cycling predecessor exists, place the node after the
        junction of cycling predecessors.

        Returns:
            Union[PlacementResult, bool]: NODE_PLACED or PUSHED_BACK if a suitable level is determined, otherwise False.
        """

        forge_logger.debug(f"Checking Rule 5 for node {self.node}")

        if self.set_and_cycling:
            set_and_cycling_junction_predecessors = [n for n in self.set_and_cycling if self.G.out_degree(n) > 1]
            not_set_junction_predecessors = [
                n
                for n in self.node_predecessors
                if self.G.out_degree(n) > 1 and n not in set_and_cycling_junction_predecessors
            ]

            if set_and_cycling_junction_predecessors and not not_set_junction_predecessors:
                min_level_of_set_junction_predecessor = max(
                    [self.__get_level_of_placed_node(n) for n in set_and_cycling_junction_predecessors], default=None
                )

                if min_level_of_set_junction_predecessor is None:
                    forge_logger.debug("[RULE 5] Junction predecessors - level of placed node is None")
                    return False
                else:
                    forge_logger.debug("[RULE 5] Junction predecessors - node set after junction predecessor")
                    return self.__place_node_at_level_in_bpmn_adjusted(
                        level=int(min_level_of_set_junction_predecessor) + 1
                    )

            elif not_set_junction_predecessors:
                max_level_of_not_set_junction_predecessor = max(
                    [self.__get_level_of_node_from_bfs(n) for n in not_set_junction_predecessors], default=None
                )

                if max_level_of_not_set_junction_predecessor is None:
                    forge_logger.debug("[RULE 5] Junction predecessors - level of placed node is None")
                    return False

                elif len(self.node_predecessors) > 1 and self.set_predecessors:
                    # PLACEMENT FIX 11.03.2025
                    # In case the node has more than one predecessor and one them is already placed, check that predecessor whether it is a junction
                    # of any kind (merging or splitting). If the not set node is predecessor and a junction, place the node after the highest level
                    # of already set predecessor.
                    # UNDERLYING ISSUE: Nodes were connected with multiple edges

                    set_junction_predecessors = [
                        n
                        for n in self.node_predecessors
                        if (self.G.out_degree(n) > 1 or self.G.in_degree(n) > 1) and n in self.set_predecessors
                    ]

                    if set_junction_predecessors:
                        max_level_of_set_junction_predecessor = max(
                            [self.__get_level_of_placed_node(n) for n in set_junction_predecessors], default=None
                        )

                        if max_level_of_set_junction_predecessor is not None:
                            return self.__place_node_at_level_in_bpmn_adjusted(
                                level=int(max_level_of_set_junction_predecessor) + 1
                            )

                else:
                    forge_logger.debug("[RULE 5] Junction predecessors - node set after junction predecessor")

                    level_adjustment = 1

                    if max_level_of_not_set_junction_predecessor < self.level:
                        level_adjustment = self.level - max_level_of_not_set_junction_predecessor + 1

                    return self.__push_node_to_level_in_bfs(
                        level=int(max_level_of_not_set_junction_predecessor) + level_adjustment
                    )

        return False

    def RULE_6(self):
        """Rule 6: Place the node after the highest level of a predecessor that shares the
        same cycle with this node.

        Returns:
            Union[PlacementResult, bool]: NODE_PLACED if placed, otherwise False.
        """

        forge_logger.debug(f"Checking Rule 6 for node {self.node}")

        if self.set_predecessors:
            same_cycle_predecessors = []

            for set_predecessor in self.set_predecessors:
                cycles_with_node: List[List] = [cycle for cycle in self.graph_cycles_sorted_desc if self.node in cycle]
                cycles_with_set_predecessor: List[List] = [
                    cycle for cycle in self.graph_cycles_sorted_desc if set_predecessor in cycle
                ]

                part_of_same_cycle = any(cycle in cycles_with_set_predecessor for cycle in cycles_with_node)

                if part_of_same_cycle:
                    same_cycle_predecessors.append(set_predecessor)

            if not same_cycle_predecessors:
                return False

            max_level_of_same_cycle_predecessor = max(
                [self.__get_level_of_placed_node(n) for n in same_cycle_predecessors], default=None
            )

            if max_level_of_same_cycle_predecessor is None:
                forge_logger.debug("[RULE 6] Same cycle predecessors - level of placed node is None")
                return False
            else:
                forge_logger.debug(
                    f"[RULE 6] Node {self.node} and predecessor {set_predecessor} are part of different cycles"
                )
                return self.__place_node_at_level_in_bpmn_adjusted(level=max_level_of_same_cycle_predecessor + 1)

        return False

    def RULE_7(self):
        """Rule 7: Fallback for cycles that do not match. Place node after the highest level
        of any different-cycle predecessor.

        Returns:
            Union[PlacementResult, bool]: NODE_PLACED if placed, otherwise False.
        """

        if self.set_predecessors:
            different_cycle_predecessors = []

            for set_predecessor in self.set_predecessors:
                cycles_with_node: List[List] = [cycle for cycle in self.graph_cycles_sorted_desc if self.node in cycle]
                cycles_with_set_predecessor: List[List] = [
                    cycle for cycle in self.graph_cycles_sorted_desc if set_predecessor in cycle
                ]

                part_of_different_cycle = any(cycle not in cycles_with_set_predecessor for cycle in cycles_with_node)

                if part_of_different_cycle:
                    different_cycle_predecessors.append(set_predecessor)

            if not different_cycle_predecessors:
                return False

            max_level_of_different_cycle_predecessor = max(
                [self.__get_level_of_placed_node(n) for n in different_cycle_predecessors], default=None
            )

            if max_level_of_different_cycle_predecessor is None:
                forge_logger.debug("[RULE 7] Different cycle predecessors - level of placed node is None")
                return False
            else:
                forge_logger.debug(
                    f"[RULE 7] Node {self.node} and predecessor {set_predecessor} are part of different cycles"
                )
                return self.__place_node_at_level_in_bpmn_adjusted(level=max_level_of_different_cycle_predecessor + 1)

        forge_logger.debug(f"Checking Rule 7 for node {self.node}")

    def FALLBACK(self):
        """Fallback rule: Push node to the next level if none of the other rules apply.

        Returns:
            bool: False, indicating no placement action taken.
        """

        forge_logger.debug(f"Node {self.node} could not be placed at level {self.level}")
        return False

    def __get_level_of_placed_node(self, node: str) -> Union[int, None]:
        """Retrieves the level of a placed node in the `bpmn_adjusted_columns`.

        Args:
            node (str): Node to get the level for.

        Returns:
            Union[int, None]: The level of the node if found, otherwise None.
        """

        for level, nodes in self.bpmn_adjusted_columns.items():
            if node in nodes:
                return level

        return None

    def __get_level_of_node_from_bfs(self, node: str) -> Union[int, None]:
        """Looks up a node's BFS level in the original BFS-level dictionary.

        Args:
            node (str): Node to get the BFS level for.

        Returns:
            Union[int, None]: The BFS level of the node if found, otherwise None.
        """

        for level, nodes in self.bfs_with_levels.items():
            if node in nodes:
                return level

        return None

    def __is_node_in_cycle(self, start_node):
        """Determines if a closed loop (cycle) exists in the graph starting from a specified node.

        Args:
            start_node (str): The node from which the cycle search begins.

        Returns:
            bool: True if a cycle exists from the start node, False otherwise.
        """

        def dfs(node, target=set(), visited=set(), is_first_call=True, dfs_recursion_depths=0):
            """Performs a DFS to find a cycle back to the target node.

            Args:
                node (str): Current node under DFS.
                target (set): The node we're checking if we can return to.
                visited (set): Keeps track of visited nodes in this path.
                is_first_call (bool): Whether this is the first call of DFS.
                dfs_recursion_depths (int): Used for debugging recursion depth.

            Returns:
                bool: True if a cycle to target is found, False otherwise.
            """

            if node == target and not is_first_call:
                return True
            if node in visited:
                return False

            visited.add(node)
            for successor in self.G.successors(node):
                if dfs(successor, target, visited, is_first_call=False, dfs_recursion_depths=dfs_recursion_depths + 1):
                    return True
            return False

        return dfs(node=start_node, target=start_node, visited=set())

    def __push_node_to_level_in_bfs(self, node: str = None, level: int = None) -> Union[PlacementResult, bool]:
        """Pushes a node to a given level in the original BFS layers.

        Args:
            node (str, optional): Node to push. Defaults to self.node.
            level (int, optional): Target level. Defaults to self.level + 1.

        Returns:
            Union[PlacementResult, bool]: PUSHED_BACK if successfully moved, otherwise False.
        """

        if node is None:
            node = self.node

        if level is None:
            level = self.level + 1

        if self.node not in self.placed_nodes:
            self.bfs_with_levels[level].append(node)
            forge_logger.debug(f"[BFS Push Back] Node {node} pushed to level {level}")
            return PlacementResult.PUSHED_BACK
        else:
            return False

    def __place_node_at_level_in_bpmn_adjusted(self, node: str = None, level: int = None) -> PlacementResult:
        """Places a node at the given level in bpmn_adjusted_columns.

        Args:
            node (str, optional): Node to place. Defaults to self.node.
            level (int, optional): Target level. Defaults to self.level.

        Returns:
            PlacementResult: NODE_PLACED to indicate successful placement.
        """

        if node is None:
            node = self.node

        if level is None:
            level = self.level

        self.bpmn_adjusted_columns[level].append(node)
        self.placed_nodes.add(node)
        forge_logger.debug(f"[BPMN Adjusted] Node {node} placed at level {level}")
        return PlacementResult.NODE_PLACED

    def __max_pred_level(self, node: str = None) -> Union[int, None]:
        """Finds the maximum level of the predecessors of the given node.

        Args:
            node (str, optional): The node whose predecessors to consider. Defaults to self.node.

        Returns:
            Union[int, None]: Maximum predecessor level or None if no predecessors found.
        """

        if node is None:
            node = self.node

        return max(
            [key for key, ids in self.bpmn_adjusted_columns.items() if any(id in ids for id in self.node_predecessors)],
            default=None,
        )

    def __min_pred_level(self, node: str = None) -> Union[int, None]:
        """Finds the minimum level of the predecessors of the given node.

        Args:
            node (str, optional): The node whose predecessors to consider. Defaults to self.node.

        Returns:
            Union[int, None]: Minimum predecessor level or None if no predecessors found.
        """

        if node is None:
            node = self.node

        return min(
            [key for key, ids in self.bpmn_adjusted_columns.items() if any(id in ids for id in self.node_predecessors)],
            default=None,
        )

    def __find_maximal_combinations(self, node: str = None) -> list:
        """Finds maximal combinations of sublists beginning with the given node in the cycles.

        Args:
            node (str, optional): Node to find sublists for. Defaults to self.node.

        Returns:
            list: List of tuples representing maximal sublists that appear in at least two cycles.
        """

        if node is None:
            node = self.node

        sublist_count = defaultdict(int)

        # Find and count occurrences of sublists starting with start_node
        for lst in self.graph_cycles_sorted_desc:
            if lst[0] == node:
                for i in range(2, len(lst) + 1):
                    sublist = tuple(lst[:i])
                    sublist_count[sublist] += 1

        # Filter sublists appearing in at least 2 lists
        filtered_sublists = {sublist: count for sublist, count in sublist_count.items() if count >= 2}

        # Sort by length and remove smaller overlapping sublists
        sorted_sublists = sorted(filtered_sublists.keys(), key=len, reverse=True)
        maximal_sublists = []
        for sublist in sorted_sublists:
            if not any(sublist == longer_sublist[: len(sublist)] for longer_sublist in maximal_sublists):
                maximal_sublists.append(sublist)

        return maximal_sublists
