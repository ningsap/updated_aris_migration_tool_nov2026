from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List

from diagramforge.rendering.coords_calculator import CoordsCalculator as CC

if TYPE_CHECKING:
    from diagramforge.rendering.coordinates_handler import CoordinatesHandler
    from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup

from uuid import uuid4

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.flows.horizontal_corridor_lane import HorizontalCorridorLane
from diagramforge.rendering.render_helpers import AuxCoordY
from diagramforge.SETUP import forge_logger


class HorizontalCorridor:
    """
    Represents a horizontal corridor designed to hold multiple lanes for horizontal shape flow.

    This class manages the creation, arrangement, and retrieval of horizontal lanes
    so that shapes organized by rows can be connected or routed appropriately.
    """

    class ADD_WHERE(Enum):
        """
        Defines where to add a new lane in this corridor.

        Attributes:
            FIRST_TOP (str): Add a new lane at the top (highest Y-value).
            LAST_BOTTOM (str): Add a new lane at the bottom (lowest Y-value).
        """

        FIRST_TOP = "FIRST_TOP"
        LAST_BOTTOM = "LAST_BOTTOM"

    def __init__(
        self, from_row: int, coordinates_handler: CoordinatesHandler, global_grid_lookup: GlobalGridLookup
    ) -> None:
        """
        Initializes the horizontal corridor with row index, a coordinate manager,
        and a global grid lookup reference.

        Args:
            from_row (int): The starting row index from which the corridor should begin.
            coordinates_handler (CoordinatesHandler): Handler to manage shape coordinates.
            global_grid_lookup (GlobalGridLookup): Central reference to grid and shape data.
        """

        self.id = str(uuid4())
        self.from_row: int = from_row
        self.coordinates_handler = coordinates_handler
        self.global_grid_lookup = global_grid_lookup

        self.active_horizontal_lanes: List[HorizontalCorridorLane] = []

    @property
    def corridor_start_y(self):
        """
        float: The Y-coordinate at which this corridor starts.

        This value is computed based on the specified row or a default configuration.
        """

        if self.from_row == -1:
            return CC.calculate_horizontal_corridor_start_y(
                center_y=FORGE_CONFIG.TOP_HORIZONTAL_CORRIDOR_LANE_START_Y_SAVE
            )

        random_shape_coords_record_of_row = self.coordinates_handler.shape_coords_record_by_resource_id[
            self.global_grid_lookup.get_shapes_in_row(self.from_row)[0]
        ]

        shape_height = (
            random_shape_coords_record_of_row.global_bounds.lowerRight.y
            - random_shape_coords_record_of_row.global_bounds.upperLeft.y
        )

        center_y = random_shape_coords_record_of_row.global_bounds.lowerRight.y - shape_height / 2

        return CC.calculate_horizontal_corridor_start_y(center_y=center_y)

    @property
    def corridor_end_y(self):
        """
        float: The Y-coordinate at which this corridor ends.

        Calculated by adding the total height of active horizontal lanes to the start Y.
        """

        return self.corridor_start_y + (len(self.active_horizontal_lanes) * SC.HORIZONTAL_CORRIDOR_LANE_HEIGHT)

    def __repr__(self):
        """
        str: Provides a textual representation of the corridor.

        Includes the row index, the corridor's start Y, and the count of active lanes.
        """

        return f"HorizontalCorridor at row {self.from_row} -> Start Y: {self.corridor_start_y} | Active Lanes: {len(self.active_horizontal_lanes)}"

    def get_available_horizontal_corridor_lane(self, source_col, target_col, add_where=ADD_WHERE.LAST_BOTTOM):
        """
        Retrieves or creates a horizontal corridor lane that can accommodate the
        busy section spanning from source_col to target_col.

        If no lane is available, a new one is added based on the specified position.

        Args:
            source_col (int): The column index where the busy section starts.
            target_col (int): The column index where the busy section ends.
            add_where (HorizontalCorridor.ADD_WHERE, optional): Position to add
                a new lane if needed. Defaults to ADD_WHERE.LAST_BOTTOM.

        Returns:
            HorizontalCorridorLane: A suitable or newly created lane for the specified columns.
        """

        lane = self.check_lane_availability(source_col, target_col, add_where=add_where)

        if lane is None:
            lane = self.add_horizontal_corridor_lane()

        lane.add_busy_section(source_col=source_col, target_col=target_col)

        return lane

    def check_lane_availability(self, source_col, target_col, add_where=ADD_WHERE.LAST_BOTTOM):
        """
        Checks if an existing lane can accommodate the busy section from source_col
        to target_col without conflicts.

        Args:
            source_col (int): The start column index of the busy section.
            target_col (int): The end column index of the busy section.
            add_where (HorizontalCorridor.ADD_WHERE, optional): Position to add a new
                lane if none is available. Defaults to ADD_WHERE.LAST_BOTTOM.

        Returns:
            HorizontalCorridorLane or None: An existing lane if one is available, else None.
        """

        requested_direction = self.global_grid_lookup.get_horizontal_busy_direction(source_col, target_col)
        requested_section = range(min(source_col, target_col), max(source_col, target_col) + 1)

        if add_where == HorizontalCorridor.ADD_WHERE.FIRST_TOP:
            sorted_lane_list = sorted(self.active_horizontal_lanes, key=lambda x: x.lane_start_y.y, reverse=True)
        elif add_where == HorizontalCorridor.ADD_WHERE.LAST_BOTTOM:
            sorted_lane_list = sorted(self.active_horizontal_lanes, key=lambda x: x.lane_start_y.y, reverse=False)

        for lane in sorted_lane_list:
            viable = True

            for busy_section in lane.busy_sections:
                busy_section_start = busy_section[0]
                busy_section_end = busy_section[1]
                busy_section_direction = busy_section[2]

                busy_section = range(
                    min(busy_section_start, busy_section_end), max(busy_section_start, busy_section_end) + 1
                )

                range_cross_section = set(busy_section) & set(requested_section)

                if len(range_cross_section) >= 1:
                    viable = False
                    break

            if viable:
                return lane
            else:
                continue

    def add_horizontal_corridor_lane(self, add_where=ADD_WHERE.LAST_BOTTOM):
        """
        Creates a new horizontal corridor lane and inserts it into the existing corridor layout,
        either at the top or bottom position.

        Args:
            add_where (HorizontalCorridor.ADD_WHERE, optional): The position at which to add
                the new lane. Defaults to ADD_WHERE.LAST_BOTTOM.

        Returns:
            HorizontalCorridorLane: The newly created lane in the designated position.
        """

        if add_where == HorizontalCorridor.ADD_WHERE.FIRST_TOP:
            lane_start_y = AuxCoordY(self.corridor_start_y)

            # Shift elements by lane width down
            self.coordinates_handler.shift_elements(
                axis="y",
                threshold=lane_start_y.y,
                shift_amount=SC.HORIZONTAL_CORRIDOR_LANE_HEIGHT,
                include_threshold=True,
            )

            new_lane = HorizontalCorridorLane(
                lane_start_y=lane_start_y,
            )

            self.coordinates_handler.add_additional_y_to_shift(y=new_lane.lane_start_y)

            self.active_horizontal_lanes.append(new_lane)

            forge_logger.debug(f"Added new horizontal corridor lane {new_lane} to corridor {self} at {add_where.value}")

        elif add_where == HorizontalCorridor.ADD_WHERE.LAST_BOTTOM:
            lane_start_y = AuxCoordY(self.corridor_end_y + 1)

            # Shift elements by lane width down
            self.coordinates_handler.shift_elements(
                axis="y", threshold=lane_start_y.y, shift_amount=SC.HORIZONTAL_CORRIDOR_LANE_HEIGHT
            )

            new_lane = HorizontalCorridorLane(
                lane_start_y=lane_start_y,
            )

            self.coordinates_handler.add_additional_y_to_shift(y=new_lane.lane_start_y)

            self.active_horizontal_lanes.append(new_lane)

            forge_logger.debug(f"Added new horizontal corridor lane {new_lane} to corridor {self} at {add_where.value}")

        return new_lane
