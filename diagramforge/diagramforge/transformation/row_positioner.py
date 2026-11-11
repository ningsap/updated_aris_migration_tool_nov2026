from collections import defaultdict
from typing import Dict, List, Literal

import networkx as nx

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.schema.base import ShapeBase
from diagramforge.SETUP import forge_logger


class RowPositioner:
    """
    Class to position rows in a BPMN-like arrangement of diagram nodes.

    This class handles lane-based arrangement (including nested lanes) and
    applies crossing minimization algorithms to produce a more compact layout.

    Attributes:
        G (nx.MultiDiGraph): The multi-directed graph containing the nodes.
        bpmn_adjusted_columns (Dict[int, List[str]]): Mapping of column indices to lists of node ids.
        lane_positions_by_pool (Dict[str, List[str]]): Mapping of pool ids to ordered lane lists.
        lane_positions_by_lane (Dict[str, List[str]]): Mapping of lane ids to lists of nested lanes (if any).
        node_resource_id_to_parent_mapping (Dict[str, ShapeBase]): Mapping of node IDs to their lane/pool parents.
        bpmn_adjusted_grid (Dict[str, Dict[str, Dict[Literal["col", "row"], int]]]): Stores the final positions of nodes in each lane.
    """

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        bpmn_adjusted_columns: Dict[int, List[str]],
        pool_order_dict: Dict[int, str],
        lane_positions_by_pool: Dict[str, List[str]],
        lane_positions_by_lane: Dict[str, List[str]],
        node_resource_id_to_parent_mapping: Dict[str, ShapeBase],
    ) -> None:
        """
        Initializes RowPositioner with references to the graph, lanes, columns, and node mappings.

        Args:
            graph (nx.MultiDiGraph): The multi-directed graph containing the nodes to arrange.
            bpmn_adjusted_columns (Dict[int, List[str]]: Mapping of column indices to lists of node ids.
            lane_positions_by_pool (dict): Mapping of pool ids to ordered lane lists.
            lane_positions_by_lane (dict): Mapping of lane ids to lists of nested lanes (if any).
            node_resource_id_to_parent_mapping (Dict[str, ShapeBase]): Mapping of node IDs to their lane/pool parents.
        """
        self.G: nx.MultiDiGraph = graph
        self.bpmn_adjusted_columns = bpmn_adjusted_columns
        self.pool_order_dict = pool_order_dict
        
        self.pool_order_list = sorted(pool_order_dict, key=pool_order_dict.get)
        
        self.lane_positions_by_pool = lane_positions_by_pool
        self.lane_positions_by_lane = lane_positions_by_lane
        self.node_resource_id_to_parent_mapping = node_resource_id_to_parent_mapping

        # Cross-methodical class instance variables in order of usage
        self.bpmn_adjusted_grid: Dict[str, Dict[str, Dict[Literal["col", "row"], int]]] = {}

    def position_rows(self) -> dict:
        """
        Positions the rows by creating a BPMN-adjusted grid.

        Returns:
            dict: A dictionary  representing the BPMN-adjusted grid, mapping lane IDs
            to their respective node position dictionaries.
        """

        for pool_index, pool in enumerate(self.pool_order_list):
            forge_logger.debug(f"Processing pool: {pool} at index {pool_index}")

            # Create a grid for the BPMN-like arrangement
            self.optimize_flow_layout(pool)

        return self.bpmn_adjusted_grid

    def optimize_flow_layout(self, current_pool) -> dict:
        """
        Optimizes the flow layout for the given pool by organizing columns and lanes,
        then minimizing crossings within each lane.

        Args:
            current_pool (str): The identifier for the current pool used to determine lane order.

        Returns:
            dict: The BPMN-adjusted grid containing node positions after lane-based arrangement.
        """

        # Lane order from top to bottom for all pools
        top_to_bottom_lane_order: list = [
            lane for pool_id in self.pool_order_list for lane in self.lane_positions_by_pool[pool_id]
        ]

        # Insert nested lanes into the lane order
        if self.lane_positions_by_lane:
            for lane in top_to_bottom_lane_order:
                if nested_lanes := self.lane_positions_by_lane.get(lane):
                    lane_index = top_to_bottom_lane_order.index(lane)
                    top_to_bottom_lane_order.pop(lane_index)
                    top_to_bottom_lane_order[lane_index:lane_index] = nested_lanes

        # Initialize the BPMN-adjusted grid
        self.bpmn_adjusted_grid = {}

        # Create a flat dictionary mapping node to its column index
        node_to_column_mapping = defaultdict(int)
        for col_index, node_list in self.bpmn_adjusted_columns.items():
            for node in node_list:
                node_to_column_mapping[node] = col_index

        # Dictionary with lane as key and list of nodes in that lane as value
        nodes_by_lanes = defaultdict(list)
        for node, parent_dict in self.node_resource_id_to_parent_mapping.items():
            nodes_by_lanes[parent_dict["nested_lane"] or parent_dict["lane"]].append(node)

        # Compact globally used columns
        all_used_columns = set(node_to_column_mapping.values())
        sorted_columns = sorted(all_used_columns)
        global_column_mapping = {old_col: new_col for new_col, old_col in enumerate(sorted_columns)}
        node_to_column_mapping = {node: global_column_mapping[col] for node, col in node_to_column_mapping.items()}

        used_cols = set()

        for lane_id, lane_nodes in nodes_by_lanes.items():
            forge_logger.debug(f"Optimizing row positions for lane: {lane_id}")
            lane_subgraph: nx.MultiDiGraph = self.G.subgraph(lane_nodes)

            forge_logger.debug(
                f"Created subgraph with {len(lane_subgraph.nodes())} nodes and {len(lane_subgraph.edges())} edges."
            )

            # Extract the columns into a dictionary with column index as key and list of nodes in that column
            lane_columns = defaultdict(list)
            for node in lane_nodes:
                lane_columns[node_to_column_mapping[node]].append(node)
                used_cols.add(node_to_column_mapping[node])

            lane_node_positions = defaultdict(dict)

            # Assign initial positions
            for col in lane_columns:
                nodes_in_column = lane_columns[col]
                for i, node in enumerate(nodes_in_column):
                    lane_node_positions[node] = {
                        "col": col,
                        "row": i,
                        "all_predecessors_in_another_lane_above_or_below": None,
                    }

                    node_general_preds = list(self.G.predecessors(node))

                    # Skip nodes without predecessors
                    if not node_general_preds:
                        continue

                    if self.node_resource_id_to_parent_mapping.get(node, {}).get("nested_lane") is None:
                        forge_logger.debug(f"Node {node} has no nested lane, checking predecessors in the same lane.")
                        continue

                    all_preds_actual_lane = [
                        self.node_resource_id_to_parent_mapping[pred]["nested_lane"]
                        or self.node_resource_id_to_parent_mapping[pred]["lane"]
                        for pred in node_general_preds
                    ]
                    all_preds_in_diff_lane = all(pred_lane != lane_id for pred_lane in all_preds_actual_lane)

                    # If all predecessors are in another lane, check if they are above/below
                    if all_preds_in_diff_lane:
                        preds_lane_order_indices = [
                            top_to_bottom_lane_order.index(
                                self.node_resource_id_to_parent_mapping[pred]["nested_lane"]
                                or self.node_resource_id_to_parent_mapping[pred]["lane"]
                            )
                            for pred in node_general_preds
                        ]

                        if all(
                            pred_lane_index < top_to_bottom_lane_order.index(lane_id)
                            for pred_lane_index in preds_lane_order_indices
                        ):
                            lane_node_positions[node]["all_predecessors_in_another_lane_above_or_below"] = "above"
                            forge_logger.debug(
                                f"All predecessors of node {node} are in a different lane and above the current node's lane."
                            )
                        elif all(
                            pred_lane_index > top_to_bottom_lane_order.index(lane_id)
                            for pred_lane_index in preds_lane_order_indices
                        ):
                            lane_node_positions[node]["all_predecessors_in_another_lane_above_or_below"] = "below"
                            forge_logger.debug(
                                f"All predecessors of node {node} are in a different lane and below the current node's lane."
                            )

            forge_logger.debug(f"Initial positions assigned to nodes in lane {lane_id}")

            def minimize_crossings(
                lane_subgraph: nx.MultiDiGraph,
                node_positions: Dict[str, Dict[Literal["col", "row"], int]],
                columns: Dict[int, List[str]],
                iterations=FORGE_CONFIG.ROW_POSITIONING_CROSSING_MINIMIZATION_MAX_ITERATIONS,
            ):
                """
                Minimizes edge crossings by performing a series of
                left-to-right and right-to-left sweeps aligning nodes
                with their predecessors and successors respectively.

                Args:
                    lane_subgraph (nx.MultiDiGraph): Subgraph of nodes in the current lane.
                    node_positions (Dict[str, Dict[Literal["col", "row"], int]]): Current positions of nodes in the lane, including row and column.
                    columns (Dict[int, List[str]]): Grouping of nodes by column indices in the lane.
                    iterations (int, optional): Number of iterations for repeated sweeps.
                        Defaults to FORGE_CONFIG.ROW_POSITIONING_CROSSING_MINIMIZATION_MAX_ITERATIONS.

                Returns:
                    None. Modifies node_positions in place.
                """

                max_row_by_lane = defaultdict(int)

                for i in range(iterations):
                    # Left-to-Right Sweep
                    for col in sorted(columns.keys()):
                        if col == min(columns.keys()):
                            continue

                        current_column_nodes = columns[col]
                        desired_rows = {}

                        for current_column_node in current_column_nodes:
                            preds = [
                                n
                                for n in lane_subgraph.predecessors(current_column_node)
                                if node_to_column_mapping.get(n, -1) < col
                            ]
                            available_preds = [pred for pred in preds if pred in node_positions]

                            # Check if lane-based above/below positioning is needed
                            if lane_based_positioning := node_positions[current_column_node].get(
                                "all_predecessors_in_another_lane_above_or_below"
                            ):
                                if lane_based_positioning == "above":
                                    desired_rows[current_column_node] = 0
                                elif lane_based_positioning == "below":
                                    desired_rows[current_column_node] = max_row_by_lane[lane_id]
                            elif len(available_preds) == 1:
                                pred_row = node_positions[available_preds[0]]["row"]
                                desired_rows[current_column_node] = pred_row
                            elif len(available_preds) > 1:
                                barycenter = sum(node_positions[pred]["row"] for pred in available_preds) / len(
                                    available_preds
                                )
                                desired_rows[current_column_node] = barycenter
                            else:
                                desired_rows[current_column_node] = node_positions[current_column_node]["row"]

                        sorted_current_column_nodes = sorted(current_column_nodes, key=lambda n: desired_rows[n])
                        assigned_rows = set()

                        for sorted_current_column_node in sorted_current_column_nodes:
                            desired_row = int(round(desired_rows[sorted_current_column_node]))
                            forge_logger.debug(
                                f"LtR Sweep | Desired row for node {sorted_current_column_node}: "
                                f"{desired_row} | Iteration: {i + 1}"
                            )
                            row = desired_row
                            while row in assigned_rows:
                                row += 1

                            node_positions[sorted_current_column_node]["row"] = row
                            assigned_rows.add(row)
                            forge_logger.debug(
                                f"LtR Sweep | Node {sorted_current_column_node} > Row {row} "
                                f"(Col {col}) | Iteration: {i + 1}"
                            )
                            max_row_by_lane[lane_id] = max(max_row_by_lane[lane_id], row)

                        columns[col] = sorted(sorted_current_column_nodes, key=lambda n: node_positions[n]["row"])

                    # Right-to-Left Sweep
                    for col in sorted(columns.keys(), reverse=True):
                        if col == max(columns.keys()):
                            continue

                        current_column_nodes = columns[col]
                        desired_rows = {}

                        for current_column_node in current_column_nodes:
                            succs = [
                                n
                                for n in lane_subgraph.successors(current_column_node)
                                if node_to_column_mapping.get(n, -1) > col
                            ]
                            available_succs = [succ for succ in succs if succ in node_positions]

                            if len(available_succs) == 1:
                                succ_row = node_positions[available_succs[0]]["row"]
                                desired_rows[current_column_node] = succ_row
                            elif len(available_succs) > 1:
                                barycenter = sum(node_positions[succ]["row"] for succ in available_succs) / len(
                                    available_succs
                                )
                                desired_rows[current_column_node] = barycenter
                            else:
                                desired_rows[current_column_node] = node_positions[current_column_node]["row"]

                        sorted_current_column_nodes = sorted(current_column_nodes, key=lambda n: desired_rows[n])
                        assigned_rows = set()

                        for sorted_current_column_node in sorted_current_column_nodes:
                            desired_row = int(round(desired_rows[sorted_current_column_node]))
                            forge_logger.debug(
                                f"RtL Sweep | Desired row for node {sorted_current_column_node}: "
                                f"{desired_row} | Iteration: {i + 1}"
                            )
                            row = desired_row
                            while row in assigned_rows:
                                row += 1

                            node_positions[sorted_current_column_node]["row"] = row
                            assigned_rows.add(row)
                            max_row_by_lane[lane_id] = max(max_row_by_lane[lane_id], row)

                            forge_logger.debug(
                                f"RtL Sweep | Node {sorted_current_column_node} > Row {row} "
                                f"(Col {col}) | Iteration: {i + 1}"
                            )
                        columns[col] = sorted(sorted_current_column_nodes, key=lambda n: node_positions[n]["row"])

            def compact_rows(node_positions):
                """
                Compacts row positions to remove any unused or empty rows,
                ensuring the row indices are consecutive.

                Args:
                    node_positions (dict): Node positions dictionary where each value is a dict
                        containing 'row' and 'col' attributes, among others.

                Returns:
                    None. Modifies node_positions in place.
                """
                used_rows = set(pos["row"] for pos in node_positions.values())
                sorted_rows = sorted(used_rows)
                row_mapping = {old_row: new_row for new_row, old_row in enumerate(sorted_rows)}

                for node in node_positions:
                    old_row = node_positions[node]["row"]
                    node_positions[node]["row"] = row_mapping[old_row]
                    forge_logger.debug(f"Node {node} moved from row {old_row} to row {row_mapping[old_row]}")

            minimize_crossings(
                lane_subgraph=lane_subgraph,
                node_positions=lane_node_positions,
                columns=lane_columns,
                iterations=FORGE_CONFIG.ROW_POSITIONING_CROSSING_MINIMIZATION_MAX_ITERATIONS,
            )

            compact_rows(lane_node_positions)

            self.bpmn_adjusted_grid[lane_id] = lane_node_positions

        # Compact globally used columns again (collapsed pools should be disregarded but could dictate gaps in columns)
        all_used_columns = used_cols
        sorted_columns = sorted(all_used_columns)
        old_to_new_column_mapping = {old_col: new_col for new_col, old_col in enumerate(sorted_columns)}

        for lane_id, lane_node_positions in self.bpmn_adjusted_grid.items():
            for node_id, position in lane_node_positions.items():
                old_col = position["col"]
                new_col = old_to_new_column_mapping[old_col]
                position["col"] = new_col

        return self.bpmn_adjusted_grid
