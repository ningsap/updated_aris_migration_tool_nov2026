from typing import List, Union

from diagramforge.helpers.STATICS import CARDINAL_DIRECTIONS as CD
from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup
from diagramforge.rendering.flows.horizontal_corridor_lane import HorizontalCorridorLane
from diagramforge.rendering.flows.vertical_corridor_lane import VerticalCorridorLane
from diagramforge.schema.shapes import Association, CollapsedPool


class PortConnection:
    """
    A class representing a connection between ports in the diagram.
    """

    def __init__(self, source: str, association: Association, global_grid_lookup: GlobalGridLookup) -> None:
        """
        Initializes a PortConnection object.

        Args:
            source (str): Resource ID of the source shape.
            association (Association): The association object representing the connection.
            global_grid_lookup (GlobalGridLookup): Helper for grid-based position lookups.
        """

        self.source = source
        self.target = association.target.resource_id
        self.association = association
        self.global_grid_lookup = global_grid_lookup
        self.is_straight_direct_connection = False

        self.used_vertical_corridor_lanes: List[VerticalCorridorLane] = []
        self.used_horizontal_corridor_lane: List[HorizontalCorridorLane] = []
        self.possible_label_y_positions: List[float] = []

        self.is_source_collapsed_pool: bool = self.global_grid_lookup.is_node_collapsed_pool(self.source)
        self.is_target_collapsed_pool: bool = self.global_grid_lookup.is_node_collapsed_pool(self.target)

        self.is_target_pool: bool = self.global_grid_lookup.is_node_pool(self.target)

        # Calculated and assigned properties

        # The order index gives the branching point from closest to furthest from the source node
        # 0 means it's a direct connection to the target node without any branching (only for the EAST port)
        # The order can become negative for the EAST port as it covers connections above and below the resprctive shape's row
        self.order: int = 0

        self.row_distance: int = self.global_grid_lookup.get_row_distance(self.source, self.target)
        self.col_distance: int = self.global_grid_lookup.get_col_distance(self.source, self.target)

        self.row_distance_abs: int = abs(self.row_distance)
        self.col_distance_abs: int = abs(self.col_distance)

        # Determine the relative position of the target shape to the source shape

        self.relative_position_to_source: CD = self.global_grid_lookup.determine_relative_direction(
            self.source, self.target
        )

    def __repr__(self) -> str:
        """
        Returns a string representation of the PortConnection.

        Returns:
            str: String representation in the format "PortConnection (source -> target) | Association ID: ... | CD to source: ... | Order: ..."
        """

        return f"PortConnection ({self.source} -> {self.target}) | Association ID: {self.association.resource_id} | CD to source: {self.relative_position_to_source} | Order: {self.order}"

    def append_used_lanes(
        self,
        used_lanes: Union[
            list[Union[VerticalCorridorLane, HorizontalCorridorLane]], VerticalCorridorLane, HorizontalCorridorLane
        ],
    ) -> None:
        """
        Appends used lanes to the connection.

        Args:
            used_lanes (Union[list[Union[VerticalCorridorLane, HorizontalCorridorLane]], VerticalCorridorLane, HorizontalCorridorLane]): Lanes to append.
        """

        if not isinstance(used_lanes, list):
            used_lanes = [used_lanes]

        for lane in used_lanes:
            if isinstance(lane, VerticalCorridorLane):
                self.used_vertical_corridor_lanes.append(lane)

            elif isinstance(lane, HorizontalCorridorLane):
                self.used_horizontal_corridor_lane.append(lane)
