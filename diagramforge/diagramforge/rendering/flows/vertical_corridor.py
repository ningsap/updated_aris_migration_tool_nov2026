from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from diagramforge.rendering.coords_calculator import CoordsCalculator as CC

if TYPE_CHECKING:
    from diagramforge.rendering.coordinates_handler import CoordinatesHandler
    from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup

from uuid import uuid4

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.helpers.STATICS import BUSY_SECTION_PERSPECTIVE, V_CORRIDOR_LANE_BUSY_DIRECTION
from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.flows.vertical_corridor_lane import VerticalCorridorLane
from diagramforge.rendering.render_helpers import AuxCoordX
from diagramforge.SETUP import forge_logger


class VerticalCorridor:
    """
    Represents a vertical corridor used for routing flows.

    This class manages busy sections, dockers, and layout computations for
    vertical flows. It also handles label spacing and positioning.

    Attributes:
        from_col (int): The column index from which the corridor starts.
        coordinates_handler (CoordinatesHandler): Manages coordinate transformations and shifts.
        global_grid_lookup (GlobalGridLookup): Provides access to global grid information.
        active_vertical_lanes (List[VerticalCorridorLane]): List of active lanes within the corridor.
    """

    class ADD_WHERE(Enum):
        """
        Defines where to add a new lane in the vertical corridor.

        Attributes:
            FIRST_LEFT (str): Add a new lane at the first left position.
            LAST_RIGHT (str): Add a new lane at the last right position.
        """

        FIRST_LEFT = "FIRST_LEFT"
        LAST_RIGHT = "LAST_RIGHT"

    def __init__(
        self, from_col: int, coordinates_handler: CoordinatesHandler, global_grid_lookup: GlobalGridLookup
    ) -> None:
        """
        Initializes the VerticalCorridor with specified column, coordinate handler, and grid lookup.

        Args:
            from_col (int): The column index from which the corridor starts.
            coordinates_handler (CoordinatesHandler): Handler to manage shape coordinates.
            global_grid_lookup (GlobalGridLookup): Reference to global grid data.
        """

        self.id = str(uuid4())
        self.from_col: int = from_col
        self.coordinates_handler = coordinates_handler
        self.global_grid_lookup = global_grid_lookup

        self.active_vertical_lanes: list[VerticalCorridorLane] = []

    @property
    def corridor_start_x(self):
        """
        float: The X-coordinate at which this corridor starts.

        This value is computed based on the specified column and shape dimensions.
        """

        if self.from_col == -1:
            return CC.calculate_vertical_corridor_start_x(
                center_x=FORGE_CONFIG.LEFT_VERTICAL_CORRIDOR_LANE_START_X_SAVE
            )

        random_shape_coords_record_of_col = self.coordinates_handler.shape_coords_record_by_resource_id[
            self.global_grid_lookup.get_shapes_in_col(self.from_col)[0]
        ]

        shape_width = (
            random_shape_coords_record_of_col.global_bounds.lowerRight.x
            - random_shape_coords_record_of_col.global_bounds.upperLeft.x
        )

        center_x = random_shape_coords_record_of_col.global_bounds.lowerRight.x - shape_width / 2

        return CC.calculate_vertical_corridor_start_x(center_x=center_x)

    @property
    def corridor_end_x(self):
        """
        float: The X-coordinate at which this corridor ends.

        Calculated by adding the total width of active vertical lanes to the start X.
        """

        return self.corridor_start_x + (len(self.active_vertical_lanes) * SC.VERTICAL_CORRIDOR_LANE_WIDTH)

    def __repr__(self) -> str:
        """
        Provides a string representation of the corridor.

        Returns:
            str: A formatted string indicating the corridor's column, start X, and number of active lanes.
        """

        return f"VerticalCorridor at col {self.from_col} -> Start X: {self.corridor_start_x} | Active Lanes: {len(self.active_vertical_lanes)}"

    def get_available_vertical_corridor_lane(
        self,
        busy_source_row: int,
        busy_target_row: int,
        original_source_row: int,
        original_target_row: int,
        add_where: ADD_WHERE = ADD_WHERE.FIRST_LEFT,
        perspective: BUSY_SECTION_PERSPECTIVE = BUSY_SECTION_PERSPECTIVE.SOURCE,
    ) -> VerticalCorridorLane:
        """
        Retrieves or creates a vertical corridor lane that can accommodate the busy section spanning from source_row to target_row.

        If no lane is available, a new one is added based on the specified position and perspective.

        Args:
            busy_source_row (int): The source row index of the busy section.
            busy_target_row (int): The target row index of the busy section.
            original_source_row (int): The original source row index referenced in the flow.
            original_target_row (int): The original target row index referenced in the flow.
            add_where (ADD_WHERE, optional): Position to add a new lane if needed. Defaults to ADD_WHERE.FIRST_LEFT.
            perspective (BUSY_SECTION_PERSPECTIVE, optional): Perspective from which the busy section is assigned (source/target). Defaults to BUSY_SECTION_PERSPECTIVE.SOURCE.

        Returns:
            VerticalCorridorLane: A suitable or newly created lane for the specified busy section.
        """

        lane = None

        if not FORGE_CONFIG.VERTICAL_FLOWS_ONE_LANE_PER_FLOW:
            lane = self.check_lane_availability(
                busy_source_row=busy_source_row,
                busy_target_row=busy_target_row,
                original_source_row=original_source_row,
                original_target_row=original_target_row,
                add_where=add_where,
                perspective=perspective,
            )

            if lane is None:
                lane = self.add_vertical_corridor_lane(add_where=add_where)

            lane.add_busy_section(
                busy_source_row=busy_source_row,
                busy_target_row=busy_target_row,
                original_source_row=original_source_row,
                original_target_row=original_target_row,
                perspective=perspective,
            )

        else:
            lane = self.add_vertical_corridor_lane(add_where=add_where)

            lane.add_busy_section(
                busy_source_row=busy_source_row,
                busy_target_row=busy_target_row,
                original_source_row=original_source_row,
                original_target_row=original_target_row,
                perspective=perspective,
            )

        return lane

    def check_lane_availability(
        self,
        busy_source_row: int,
        busy_target_row: int,
        original_source_row: int,
        original_target_row: int,
        add_where: ADD_WHERE = ADD_WHERE.FIRST_LEFT,
        perspective: BUSY_SECTION_PERSPECTIVE = BUSY_SECTION_PERSPECTIVE.SOURCE,
    ) -> VerticalCorridorLane:
        """
        Checks if an existing lane can accommodate the busy section from source_row to target_row without conflicts.

        Args:
            busy_source_row (int): The source row index of the busy section.
            busy_target_row (int): The target row index of the busy section.
            original_source_row (int): The original source row index referenced in the flow.
            original_target_row (int): The original target row index referenced in the flow.
            add_where (ADD_WHERE, optional): Position to add a new lane if none is available. Defaults to ADD_WHERE.FIRST_LEFT.
            perspective (BUSY_SECTION_PERSPECTIVE, optional): Perspective from which the busy section is assigned (source/target). Defaults to BUSY_SECTION_PERSPECTIVE.SOURCE.

        Returns:
            VerticalCorridorLane or None: An existing lane if one is available, else None.
        """

        requested_direction: V_CORRIDOR_LANE_BUSY_DIRECTION = VerticalCorridorLane.get_busy_tuple(
            busy_source_row=busy_source_row,
            busy_target_row=busy_target_row,
            original_source_row=original_source_row,
            original_target_row=original_target_row,
            perspective=perspective,
        )[2]

        requested_section = range(min(busy_source_row, busy_target_row), max(busy_source_row, busy_target_row) + 1)

        if add_where == VerticalCorridor.ADD_WHERE.FIRST_LEFT:
            sorted_lane_list = sorted(self.active_vertical_lanes, key=lambda x: x.lane_start_x.x, reverse=True)
        elif add_where == VerticalCorridor.ADD_WHERE.LAST_RIGHT:
            sorted_lane_list = sorted(self.active_vertical_lanes, key=lambda x: x.lane_start_x.x, reverse=False)

        for lane in sorted_lane_list:
            viable = True

            for busy_section in lane.busy_sections:
                busy_section_start = busy_section[0]
                busy_section_stop = busy_section[1]
                busy_section_direction = busy_section[2]

                busy_section = range(
                    min(busy_section_start, busy_section_stop), max(busy_section_start, busy_section_stop) + 1
                )

                set_busy_section = set(busy_section)
                set_requested_section = set(requested_section)

                range_cross_section = set_busy_section & set_requested_section

                if len(range_cross_section) == 1:
                    if busy_source_row == busy_target_row:
                        viable = False
                        break

                    if busy_section_direction == requested_direction:
                        viable = False
                        break

                    if original_source_row != busy_source_row and original_source_row in busy_section:
                        viable = False
                        break

                    if original_target_row != busy_target_row and original_target_row in busy_section:
                        viable = False
                        break

                    if perspective == BUSY_SECTION_PERSPECTIVE.TARGET:
                        viable = False
                        break

                    # elif next(iter(range_cross_section)) not in [busy_section_start]:
                    #     viable = False
                    #     break

                elif len(range_cross_section) > 1:
                    viable = False
                    break

            if viable:
                return lane
            else:
                continue

        return None

    def add_vertical_corridor_lane(self, add_where: ADD_WHERE = ADD_WHERE.FIRST_LEFT) -> VerticalCorridorLane:
        """
        Adds a new vertical corridor lane at the specified position.

        Args:
            add_where (ADD_WHERE, optional): Position at which to add the new lane. Defaults to ADD_WHERE.FIRST_LEFT.

        Returns:
            VerticalCorridorLane: The newly created lane.
        """

        if add_where == VerticalCorridor.ADD_WHERE.FIRST_LEFT:
            lane_start_x = AuxCoordX(self.corridor_start_x)

            # Create room for lane by shifting all elements to the right by lane width
            self.coordinates_handler.shift_elements(
                axis="x",
                threshold=self.corridor_start_x,
                shift_amount=SC.VERTICAL_CORRIDOR_LANE_WIDTH,
                include_threshold=True,
            )

            new_lane = VerticalCorridorLane(
                lane_start_x=lane_start_x,
            )
            self.coordinates_handler.add_additional_x_to_shift(x=new_lane.lane_start_x)

            self.active_vertical_lanes.append(new_lane)

            forge_logger.debug(f"Added new vertical corridor lane {new_lane} to corridor {self} at {add_where.value}")

            return new_lane

        elif add_where == VerticalCorridor.ADD_WHERE.LAST_RIGHT:
            lane_start_x = AuxCoordX(self.corridor_end_x + 1)

            # Create room for lane by shifting all elements to the right by lane width
            self.coordinates_handler.shift_elements(
                axis="x", threshold=self.corridor_end_x, shift_amount=SC.VERTICAL_CORRIDOR_LANE_WIDTH
            )

            new_lane = VerticalCorridorLane(
                lane_start_x=lane_start_x,
            )

            self.coordinates_handler.add_additional_x_to_shift(x=new_lane.lane_start_x)

            self.active_vertical_lanes.append(new_lane)

            forge_logger.debug(f"Added new vertical corridor lane {new_lane} to corridor {self} at {add_where.value}")

            return new_lane
