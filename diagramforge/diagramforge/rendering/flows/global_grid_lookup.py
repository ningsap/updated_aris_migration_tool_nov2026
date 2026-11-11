from typing import Dict, List, Literal

from diagramforge.exceptions.flow_positioning import SourceToTargetRelativePositionException
from diagramforge.helpers.STATICS import CARDINAL_DIRECTIONS as CD
from diagramforge.helpers.STATICS import COLLAPSED_POOL_RELATIVE_POSITION, H_CORRIDOR_LANE_BUSY_DIRECTION
from diagramforge.schema.shapes import CollapsedPool, Pool, ShapeBase, Task
from diagramforge.SETUP import forge_logger


class GlobalGridLookup:
    """Handles the global grid positioning and lookups for BPMN nodes.

    This class creates a global coordinate system that merges local lane-based
    node positions into a single global grid. It provides helper methods to
    retrieve and manipulate node positions in grid form.
    """

    def __init__(
        self,
        bpmn_adjusted_grid: Dict[str, Dict[str, Dict[Literal["col", "row"], int]]],
        pool_order: Dict[str, str],
        lane_positions_by_pool: Dict[str, List[str]],
        lane_positions_by_lane: Dict[str, List[str]],
        resource_id_to_shape_mapping: Dict[str, ShapeBase],
        node_resource_id_to_parent_mapping: Dict[str, str],
    ) -> None:
        """Initializes the GlobalGridLookup with BPMN positioning data.

        Args:
            bpmn_adjusted_grid (Dict[str, Dict[str, Dict[Literal["col", "row"], int]]]): Adjusted BPMN grid mapping lane IDs to node positions.
            lane_positions_by_pool (Dict[str, List[str]]): Structure defining lane placement within pools.
            lane_positions_by_lane (Dict[str, List[str]]): Structure defining nested lanes for each lane ID.
            resource_id_to_shape_mapping (Dict[str, ShapeBase]): Mapping of resource IDs to shape objects.
            node_resource_id_to_parent_mapping (Dict[str, str]): Mapping of node resource IDs to their parent shapes.
        """

        self.bpmn_adjusted_grid = bpmn_adjusted_grid
        self.pool_order = pool_order
        # Order pools dict by their priority
        self.pool_order = {k: v for k, v in sorted(self.pool_order.items(), key=lambda item: item[0], reverse=True)}
        self.pool_order_by_index = {v: k for k, v in self.pool_order.items()}

        self.lane_positions_by_pool = lane_positions_by_pool
        self.lane_positions_by_lane = lane_positions_by_lane
        self.resource_id_to_shape_mapping = resource_id_to_shape_mapping
        self.node_resource_id_to_parent_mapping = node_resource_id_to_parent_mapping

        self.pool_order_by_index_without_collapsed_pools = {
            k: v for k, v in self.pool_order_by_index.items() if not self.is_node_collapsed_pool(v)
        }
        # Global grid positions for all nodes
        self.grid_positions: dict = {}

        self.__create_global_grid_positions()

        self.max_col = max([node["col"] for node in self.grid_positions.values()])
        self.max_row = max([node["row"] for node in self.grid_positions.values()])

        # Map out occupied lanes with their respective min and max rows
        self.lane_occupied_rows: Dict[str, Dict[Literal["min", "max"], int]] = {}

        for lane_id, nodes in self.bpmn_adjusted_grid.items():
            if lane_id not in self.lane_occupied_rows:
                self.lane_occupied_rows[lane_id] = {"min": float("inf"), "max": float("-inf")}

            for node_id in nodes.keys():
                node_global_row = self.grid_positions[node_id]["row"]
                if node_global_row < self.lane_occupied_rows[lane_id]["min"]:
                    self.lane_occupied_rows[lane_id]["min"] = node_global_row
                if node_global_row > self.lane_occupied_rows[lane_id]["max"]:
                    self.lane_occupied_rows[lane_id]["max"] = node_global_row
        forge_logger.debug(f"Lane occupied rows: {self.lane_occupied_rows}")

        self.pool_occupied_rows: Dict[str, Dict[Literal["min", "max"], int]] = {}
        for pool_id, lanes in self.lane_positions_by_pool.items():
            if pool_id not in self.pool_occupied_rows and lanes:
                self.pool_occupied_rows[pool_id] = {"min": float("inf"), "max": float("-inf")}

            for lane in lanes:
                if lane in self.lane_occupied_rows:
                    lane_min = self.lane_occupied_rows[lane]["min"]
                    lane_max = self.lane_occupied_rows[lane]["max"]

                    if lane_min < self.pool_occupied_rows[pool_id]["min"]:
                        self.pool_occupied_rows[pool_id]["min"] = lane_min
                    if lane_max > self.pool_occupied_rows[pool_id]["max"]:
                        self.pool_occupied_rows[pool_id]["max"] = lane_max
        forge_logger.debug(f"Pool occupied rows: {self.pool_occupied_rows}")

    def __create_global_grid_positions(self) -> None:
        """Builds the global grid positions for all nodes.

        This method merges individual lane node positions into a single
        global coordinate system. It calculates row shifts per lane and
        updates the global grid positions accordingly.

        Returns:
            None
        """

        forge_logger.debug("Creating global grid positions by resource id")

        max_rows_in_lane_by_lane_id = {
            lane_id: max([(node["row"] + 1) for node in nodes.values()])
            for lane_id, nodes in self.bpmn_adjusted_grid.items()
        }

        row_shift_by_lane_id = {}

        current_lane_order = [
            lane for pool_id, _ in self.pool_order.items() for lane in self.lane_positions_by_pool[pool_id]
        ]

        # Insert nested lanes into the lane order if any.
        if self.lane_positions_by_lane:
            for lane in current_lane_order:
                if nested_lanes := self.lane_positions_by_lane.get(lane):
                    lane_index = current_lane_order.index(lane)
                    current_lane_order.pop(lane_index)
                    current_lane_order[lane_index:lane_index] = nested_lanes

        # Calculate row shift for each lane.
        for lane_id in current_lane_order:
            if lane_id == current_lane_order[0]:
                row_shift_by_lane_id[lane_id] = 0
            else:
                row_shift_by_lane_id[lane_id] = sum(
                    [
                        max_rows_in_lane_by_lane_id[lane]
                        for lane in current_lane_order[: current_lane_order.index(lane_id)]
                    ]
                )
            forge_logger.debug(f"Row shift for lane {lane_id}: {row_shift_by_lane_id[lane_id]}")

        # Assign global positions to nodes.
        for lane_id, nodes in self.bpmn_adjusted_grid.items():
            for node_id, node in nodes.items():
                list_lanes_above = current_lane_order[: current_lane_order.index(lane_id)]
                node_row_shift = sum([max_rows_in_lane_by_lane_id[lane] for lane in list_lanes_above])

                self.grid_positions[node_id] = {"row": node["row"] + node_row_shift, "col": node["col"]}

                forge_logger.debug(
                    f"Global Grid: Node {node_id} is at row {node['row'] + node_row_shift} "
                    f"and col {node['col']} in lane {lane_id}"
                )

    def get_col_row(self, resource_id: str) -> tuple:
        """Retrieves the column and row of a given node.

        Args:
            resource_id (str): The resource ID of the node.

        Returns:
            tuple: (column index, row index).
        """

        return self.grid_positions[resource_id]["col"], self.grid_positions[resource_id]["row"]

    def get_col(self, resource_id: str) -> int:
        """Gets the column index of a node.

        Args:
            resource_id (str): The resource ID of the node.

        Returns:
            int: The column index where the node is positioned.
        """

        if self.is_node_pool(resource_id) or self.is_node_collapsed_pool(resource_id):
            forge_logger.debug(f"Resource ID {resource_id} is a CollapsedPool, returning column 0.")
            return 0

        return self.grid_positions[resource_id]["col"]

    def get_row(self, resource_id: str) -> int:
        """Gets the row index of a node.

        Args:
            resource_id (str): The resource ID of the node.

        Returns:
            int: The row index where the node is positioned.
        """

        if self.is_node_collapsed_pool(resource_id) or self.is_node_pool(resource_id):
            forge_logger.debug(f"Resource ID {resource_id} is a CollapsedPool, returning row 0.")
            return 0

        return self.grid_positions[resource_id]["row"]

    def get_row_distance(self, source: str, target: str) -> int:
        """Calculates the vertical distance in rows between two nodes.
        Returns 0 if either node is a CollapsedPool.

        Args:
            source (str): Resource ID of the source node.
            target (str): Resource ID of the target node.

        Returns:
            int: The difference in rows (target row - source row).
        """

        if self.is_node_pool(target) or self.is_node_collapsed_pool(target) or self.is_node_collapsed_pool(source):
            forge_logger.debug(f"Source or target is a CollapsedPool: source={source}, target={target}")
            return 0

        return self.get_row(target) - self.get_row(source)

    def get_col_distance(self, source: str, target: str) -> int:
        """Calculates the horizontal distance in columns between two nodes.
        Returns 0 if either node is a CollapsedPool.


        Args:
            source (str): Resource ID of the source node.
            target (str): Resource ID of the target node.

        Returns:
            int: The difference in columns (target column - source column).
        """

        if self.is_node_pool(target) or self.is_node_collapsed_pool(target) or self.is_node_collapsed_pool(source):
            forge_logger.debug(f"Source or target is a CollapsedPool: source={source}, target={target}")
            return 0

        return self.get_col(target) - self.get_col(source)

    def get_shapes_in_row(self, row: int) -> list:
        """Lists all node IDs in a given row.

        Args:
            row (int): The row index to check.

        Returns:
            list: A list of resource IDs for nodes in the specified row.
        """

        return [node_id for node_id, node_position in self.grid_positions.items() if node_position["row"] == row]

    def is_node_task(self, node_id: str) -> bool:
        """Checks if a node ID corresponds to any Task type.

        Args:
            node_id (str): The resource ID of the node.
        Returns:
            bool: True if the node is any Task type, False otherwise.
        """

        return isinstance(self.resource_id_to_shape_mapping.get(node_id), Task)

    def is_node_pool(self, node_id: str) -> bool:
        """Checks if a node ID corresponds to a Pool.

        Args:
            node_id (str): The resource ID of the node.

        Returns:
            bool: True if the node is a Pool, False otherwise.
        """

        return isinstance(self.resource_id_to_shape_mapping.get(node_id), Pool)

    def is_node_collapsed_pool(self, node_id: str) -> bool:
        """Checks if a node ID corresponds to a CollapsedPool.

        Args:
            node_id (str): The resource ID of the node.

        Returns:
            bool: True if the node is a CollapsedPool, False otherwise.
        """

        return isinstance(self.resource_id_to_shape_mapping.get(node_id), CollapsedPool)

    def get_shapes_in_col(self, col: int) -> list:
        """Lists all node IDs in a given column.

        Args:
            col (int): The column index to check.

        Returns:
            list: A list of resource IDs for nodes in the specified column.
        """

        return [node_id for node_id, node_position in self.grid_positions.items() if node_position["col"] == col]

    def determine_relative_direction(self, source: str, target: str) -> CD:
        """Determines the relative direction of a target node from a source node.

        Directions are derived from the positions of source and target in
        the global grid. If source is the same as target, a warning is logged.

        Args:
            source (str): Resource ID of the source node.
            target (str): Resource ID of the target node.

        Returns:
            str: A cardinal or intercardinal direction (e.g., 'EAST', 'NORTHWEST').

        Raises:
            SourceToTargetRelativePositionException: If no valid direction can be determined.
        """

        if self.is_node_collapsed_pool(source) and self.is_node_collapsed_pool(target):
            forge_logger.debug(
                f"Source {source} and target {target} are both CollapsedPools, returning "
                f"SOURCE_AND_TARGET_COLLAPSED_POOLS direction."
            )
            return CD.SOURCE_AND_TARGET_COLLAPSED_POOLS

        if self.is_node_collapsed_pool(target) or self.is_node_pool(target):
            forge_logger.debug(f"Target {target} is a CollapsedPool, returning EAST direction.")
            return CD.EAST

        if self.is_node_collapsed_pool(source):
            forge_logger.debug(f"Source {source} is a CollapsedPool, returning SOURCE_COLLAPSED_POOL direction.")
            return CD.SOURCE_COLLAPSED_POOL

        SOURCE_COL = self.get_col(source)
        SOURCE_ROW = self.get_row(source)

        TARGET_ROW = self.get_row(target)
        TARGET_COL = self.get_col(target)

        if TARGET_ROW == SOURCE_ROW:
            if TARGET_COL > SOURCE_COL:
                return CD.EAST
            elif TARGET_COL < SOURCE_COL:
                return CD.WEST

        elif TARGET_COL == SOURCE_COL:
            if TARGET_ROW > SOURCE_ROW:
                return CD.SOUTH
            elif TARGET_ROW < SOURCE_ROW:
                return CD.NORTH

        elif TARGET_ROW > SOURCE_ROW and TARGET_COL > SOURCE_COL:
            return CD.SOUTHEAST

        elif TARGET_ROW > SOURCE_ROW and TARGET_COL < SOURCE_COL:
            return CD.SOUTHWEST

        elif TARGET_ROW < SOURCE_ROW and TARGET_COL > SOURCE_COL:
            return CD.NORTHEAST

        elif TARGET_ROW < SOURCE_ROW and TARGET_COL < SOURCE_COL:
            return CD.NORTHWEST

        if source == target:
            forge_logger.warning(f"Source and target are the same: {source}")
            return None

        raise SourceToTargetRelativePositionException(source, target)

    def get_node_by_position(self, col: int, row: int) -> str:
        """Finds a node in the grid by its column and row indices.

        Args:
            col (int): The column index.
            row (int): The row index.

        Returns:
            str: The resource ID of the node at the given position, or None if not found.
        """

        for node_id, node_position in self.grid_positions.items():
            if node_position["col"] == col and node_position["row"] == row:
                return node_id

        return None

    def is_a_node_in_between_on_row(self, source: str, target: str) -> bool:
        """Checks if a node exists between the source and target on the same row.

        This method only checks positions forward between the column of the source
        and the column of the target if they share the same row.

        Args:
            source (str): Resource ID of the source node.
            target (str): Resource ID of the target node.

        Returns:
            bool: True if a node lies between source and target in the same row, False if not.
                  Returns None if source and target are not on the same row.
        """

        if self.is_node_collapsed_pool(source) or self.is_node_collapsed_pool(target):
            forge_logger.debug(f"Source or target is a CollapsedPool: source={source}, target={target}")
            return True

        SOURCE_COL = self.get_col(source)
        SOURCE_ROW = self.get_row(source)

        TARGET_ROW = self.get_row(target)
        TARGET_COL = self.get_col(target)

        if TARGET_ROW == SOURCE_ROW:
            for node_id, node_position in self.grid_positions.items():
                if node_position["row"] == SOURCE_ROW and SOURCE_COL < node_position["col"] < TARGET_COL:
                    return True
            return False
        else:
            return None

    def get_occupied_row_for_collapsed_pool_outgoing_connection(self, source: str, target: str) -> int:
        """Determines the occupied row for a collapsed pool's outgoing connection.

        This method checks the pool of the source and target nodes to determine the correct row.

        THE TARGET MUST BE A COLLAPSED POOL.

        Args:
            source (str): Resource ID of the source node.
            target (str): Resource ID of the target node.
        Returns:
            int: The occupied row for the outgoing connection.
        """

        if not (self.is_node_collapsed_pool(target) or self.is_node_pool(target)):
            raise ValueError(f"Target {target} must be a CollapsedPool or Pool for this calculation.")

        source_pool = self.node_resource_id_to_parent_mapping.get(source, {}).get("pool")

        source_pool_index = self.pool_order.get(source_pool)
        target_pool_index = self.pool_order.get(target)

        if source_pool_index is None or target_pool_index is None:
            forge_logger.warning(f"Source or target does not belong to a pool: source={source}, target={target}")
            return None

        relative_position = None

        if source_pool_index < target_pool_index:
            relative_position = COLLAPSED_POOL_RELATIVE_POSITION.BELOW
        elif source_pool_index > target_pool_index:
            relative_position = COLLAPSED_POOL_RELATIVE_POSITION.ABOVE
        else:
            raise ValueError(f"Source and target pools are the same: source={source}, target={target}.")

        # Only non collapsed pools can have occupied rows.
        # If the collapsed pool is above the source = take the top row - 1 of the closest pool below the target
        # collapsed pool.
        # If the collapsed pool is below the source = take the last row  of the closes pool above the target collapsed
        # pool.

        relevant_adjacent_pool_index = (
            target_pool_index - 1
            if relative_position == COLLAPSED_POOL_RELATIVE_POSITION.BELOW
            else target_pool_index + 1
        )

        closest_adjacent_pool_index = None

        adjusted_range = (
            range(relevant_adjacent_pool_index, -1, -1)
            if relative_position == COLLAPSED_POOL_RELATIVE_POSITION.BELOW
            else range(relevant_adjacent_pool_index, len(self.pool_order_by_index_without_collapsed_pools))
        )

        for index in adjusted_range:
            if pool_id := self.pool_order_by_index_without_collapsed_pools.get(index):
                closest_adjacent_pool_index = index
                forge_logger.debug(
                    f"Found closest adjacent pool at index {index} with ID {pool_id} "
                    f"(relative position: {relative_position}, source pool: {source_pool}, target pool: {target})"
                )
                break

        relevant_adjacent_pool_id = self.pool_order_by_index.get(closest_adjacent_pool_index)

        if not relevant_adjacent_pool_id:
            if adjusted_range.start == adjusted_range.stop:
                relevant_adjacent_pool_id = self.pool_order_by_index.get(adjusted_range.start)

        if relevant_adjacent_pool_id in self.pool_occupied_rows:
            occupied_row = (
                self.pool_occupied_rows[relevant_adjacent_pool_id]["min"] - 1
                if relative_position == COLLAPSED_POOL_RELATIVE_POSITION.ABOVE
                else self.pool_occupied_rows[relevant_adjacent_pool_id]["max"]
            )
            forge_logger.debug(
                f"Occupied row for collapsed pool outgoing connection: {occupied_row} "
                f"(relative position: {relative_position}, source pool: {source_pool}, "
                f"target pool: {target})"
            )
            return occupied_row
        else:
            raise ValueError(f"Relevant adjacent pool ID {relevant_adjacent_pool_id} not found in pool occupied rows.")

    def get_occupied_row_for_inc_collapsed_pool_con_or_con_between_pools(
        self,
        source: str,
        target: str,
        both_pools: False,
    ) -> int:
        """Determines the occupied row for a collapsed pool's incoming connection.

        This method checks the pool of the source and target nodes to determine the correct row.

        THE SOURCE MUST BE A COLLAPSED POOL.

        Args:
            source (str): Resource ID of the source node.
            target (str): Resource ID of the target node.
        Returns:
            int: The occupied row for the incoming connection.
        """

        if not self.is_node_collapsed_pool(source):
            raise ValueError(f"Source {source} must be a CollapsedPool for this calculation.")

        if both_pools:
            target_pool = target
        else:
            target_pool = self.node_resource_id_to_parent_mapping.get(target, {}).get("pool")

        source_pool_index = self.pool_order.get(source)
        target_pool_index = self.pool_order.get(target_pool)

        if source_pool_index is None or target_pool_index is None:
            forge_logger.warning(f"Source or target does not belong to a pool: source={source}, target={target}")
            return None

        relative_position = None

        if source_pool_index < target_pool_index:
            relative_position = COLLAPSED_POOL_RELATIVE_POSITION.BELOW
        elif source_pool_index > target_pool_index:
            relative_position = COLLAPSED_POOL_RELATIVE_POSITION.ABOVE
        else:
            raise ValueError(f"Source and target pools are the same: source={source}, target={target}.")

        # Only non collapsed pools can have occupied rows.
        # If the collapsed pool is above the source = take the top row - 1 of the closest pool below the target
        # collapsed pool.
        # If the collapsed pool is below the source = take the last row  of the closes pool above the target collapsed
        # pool.

        relevant_adjacent_pool_index = (
            target_pool_index - 1 if relative_position == COLLAPSED_POOL_RELATIVE_POSITION.BELOW else target_pool_index
        )

        closest_adjacent_pool_index = None

        adjusted_range = (
            range(relevant_adjacent_pool_index, -1, -1)
            if relative_position == COLLAPSED_POOL_RELATIVE_POSITION.BELOW
            else range(relevant_adjacent_pool_index, len(self.pool_order_by_index_without_collapsed_pools))
        )

        for index in adjusted_range:
            if pool_id := self.pool_order_by_index_without_collapsed_pools.get(index):
                closest_adjacent_pool_index = index
                forge_logger.debug(
                    f"Found closest adjacent pool at index {index} with ID {pool_id} "
                    f"(relative position: {relative_position}, source pool: {source}, target pool: {target_pool})"
                )
                break

        if relevant_adjacent_pool_id := self.pool_order_by_index.get(closest_adjacent_pool_index):
            if relevant_adjacent_pool_id in self.pool_occupied_rows:
                occupied_row = (
                    self.pool_occupied_rows[relevant_adjacent_pool_id]["min"] - 1
                    if relative_position == COLLAPSED_POOL_RELATIVE_POSITION.ABOVE
                    else self.pool_occupied_rows[relevant_adjacent_pool_id]["max"]
                )
                forge_logger.debug(
                    f"Occupied row for collapsed pool outgoing connection: {occupied_row} "
                    f"(relative position: {relative_position}, source pool: {target_pool}, "
                    f"target pool: {target})"
                )
                return occupied_row
            
        return 0

    @staticmethod
    def get_horizontal_busy_direction(source_col: int, target_col: int) -> str:
        """Determines which direction is 'busy' when moving horizontally.

        Args:
            source_col (int): Column index of the source node.
            target_col (int): Column index of the target node.

        Returns:
            str: 'RIGHT' if the target is to the right of the source, otherwise 'LEFT'.
        """

        return H_CORRIDOR_LANE_BUSY_DIRECTION.RIGHT if source_col < target_col else H_CORRIDOR_LANE_BUSY_DIRECTION.LEFT
