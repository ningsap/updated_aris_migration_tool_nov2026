from typing import List, Tuple
from uuid import uuid4

from diagramforge.helpers.STATICS import BUSY_SECTION_PERSPECTIVE, V_CORRIDOR_LANE_BUSY_DIRECTION
from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.render_helpers import AuxCoordX, AuxCoordY
from diagramforge.schema.base import Coordinates


class VerticalCorridorLane:
    """
    Represents a vertical corridor lane for routing flows.

    This class manages busy sections, dockers, and layout computations for
    vertical flows. It also handles label spacing and positioning.

    Attributes:
        busy_sections (List[tuple[int, int, V_CORRIDOR_LANE_BUSY_DIRECTION]]):
            A list tracking which rows are busy (start row, end row, direction).
        dockers_in_lane (List[Coordinates]):
            A list of docker coordinates already placed in this lane.
        added_label_spacer (float):
            Additional horizontal space allocated for lane labeling.
        lane_start_x (AuxCoordX):
            The horizontal starting coordinate of the lane.
    """

    def __init__(
        self,
        lane_start_x: AuxCoordX,
    ) -> None:
        """
        Initializes a new VerticalCorridorLane.

        Args:
            lane_start_x (AuxCoordX): The horizontal start position for this lane.
        """

        self.id = str(uuid4())
        self.busy_sections: List[Tuple[int, int, V_CORRIDOR_LANE_BUSY_DIRECTION]] = []
        self.dockers_in_lane: List[Coordinates] = []
        self.added_label_spacer_right_from_vertical_flow: float = 0.0
        self.added_label_spacer_left_from_vertical_flow: float = 0.0

        self.lane_start_x: AuxCoordX = lane_start_x

    @property
    def label_space_created_left_from_vertical_flow(self) -> bool:
        """
        Indicates whether additional label space has been allocated on the left side.

        Returns:
            bool: True if label space has been created on the left, otherwise False.
        """

        return self.added_label_spacer_left_from_vertical_flow > 0.0

    @property
    def label_space_created_right_from_vertical_flow(self) -> bool:
        """
        Indicates whether additional label space has been allocated.

        Returns:
            bool: True if label space has been created, otherwise False.
        """

        return self.added_label_spacer_right_from_vertical_flow > 0.0

    @property
    def lane_width(self) -> float:
        """
        Computes the total lane width, including the label spacer.

        Returns:
            float: The combined lane width with added label spacer.
        """

        return (
            SC.VERTICAL_CORRIDOR_LANE_WIDTH
            + self.added_label_spacer_right_from_vertical_flow
            + self.added_label_spacer_left_from_vertical_flow
        )

    @property
    def lane_end_x(self) -> AuxCoordX:
        """
        Determines the horizontal end coordinate of this lane.

        Returns:
            AuxCoordX: The horizontal ending position of the lane.
        """

        return AuxCoordX(
            self.lane_start_x.x
            + SC.VERTICAL_CORRIDOR_LANE_WIDTH
            + self.added_label_spacer_right_from_vertical_flow
            + self.added_label_spacer_left_from_vertical_flow
        )

    @property
    def lane_center_x(self):
        """
        Computes the horizontal center of this lane.

        Returns:
            AuxCoordX: The horizontal center position of the lane.
        """

        return AuxCoordX(self.lane_start_x.x + (SC.VERTICAL_CORRIDOR_LANE_WIDTH / 2))

    @property
    def lane_left_docker_anchor(self) -> AuxCoordX:
        """
        Provides the horizontal anchor coordinate for left-aligned dockers.

        Returns:
            AuxCoordX: The coordinate at which left dockers can be placed.
        """

        return AuxCoordX(self.lane_start_x.x + SC.VERTICAL_CORRIDOR_BETWEEN_LANE_BUFFER)

    @property
    def lane_right_docker_anchor(self) -> AuxCoordX:
        """
        Provides the horizontal anchor coordinate for right-aligned dockers.

        Returns:
            AuxCoordX: The coordinate at which right dockers can be placed.
        """

        return AuxCoordX(
            self.lane_end_x.x
            - SC.VERTICAL_CORRIDOR_BETWEEN_LANE_BUFFER
            - self.added_label_spacer_right_from_vertical_flow
            - self.added_label_spacer_left_from_vertical_flow
        )

    @property
    def lane_x_label_anchor_right(self) -> AuxCoordX:
        """
        Determines the horizontal coordinate to place a label within the lane right from
        flow.

        Returns:
            AuxCoordX: The coordinate for label placement in the lane.
        """

        return AuxCoordX(
            self.lane_end_x.x
            - (SC.VERTICAL_CORRIDOR_BETWEEN_LANE_BUFFER / 2)
            - self.added_label_spacer_right_from_vertical_flow
            - self.added_label_spacer_left_from_vertical_flow
        )

    @property
    def lane_x_label_anchor_left(self) -> AuxCoordX:
        """
        Determines the horizontal coordinate to place a label within the lane left from
        flow.

        Returns:
            AuxCoordX: The coordinate for label placement in the lane.
        """

        return AuxCoordX(
            self.lane_start_x.x
            + (SC.VERTICAL_CORRIDOR_BETWEEN_LANE_BUFFER / 2)
            + self.added_label_spacer_left_from_vertical_flow
        )

    @property
    def lane_label_y_anchor(self) -> AuxCoordY:
        """
        Determines the vertical coordinate to place a label in this lane.

        Returns:
            AuxCoordY: The vertical position where labels may be anchored.
        """

        pass

    def __repr__(self) -> str:
        """
        Provides a string representation of the lane, including its spans.

        Returns:
            str: A formatted description of the lane's start coordinate, end
            coordinate, and busy sections.
        """

        return (
            f"VerticalCorridorLane at {self.lane_start_x} to {self.lane_end_x} -> Busy Sections: {self.busy_sections}"
        )

    @staticmethod
    def get_busy_tuple(
        busy_source_row: int,
        busy_target_row: int,
        original_source_row: int,
        original_target_row: int,
        perspective: BUSY_SECTION_PERSPECTIVE = BUSY_SECTION_PERSPECTIVE.SOURCE,
    ) -> tuple[int, int, V_CORRIDOR_LANE_BUSY_DIRECTION]:
        """
        Creates a tuple indicating which rows are busy and in which direction.

        Args:
            busy_source_row (int): The starting row index for the busy section.
            busy_target_row (int): The ending row index for the busy section.
            original_source_row (int): The original start row in the flow.
            original_target_row (int): The original target row in the flow.
            perspective (BUSY_SECTION_PERSPECTIVE):
                Whether the rows are busy from the source or target perspective.

        Returns:
            tuple[int, int, V_CORRIDOR_LANE_BUSY_DIRECTION]:
                A tuple containing the source row, target row, and busy direction.
        """

        busy_tuple = (busy_source_row, busy_target_row)

        if perspective == BUSY_SECTION_PERSPECTIVE.SOURCE:
            if original_source_row <= original_target_row:
                direction = V_CORRIDOR_LANE_BUSY_DIRECTION.DOWN
            else:
                direction = V_CORRIDOR_LANE_BUSY_DIRECTION.UP

        elif perspective == BUSY_SECTION_PERSPECTIVE.TARGET:
            if original_source_row < original_target_row:
                direction = V_CORRIDOR_LANE_BUSY_DIRECTION.UP
            else:
                direction = V_CORRIDOR_LANE_BUSY_DIRECTION.DOWN

        busy_tuple += (direction,)

        return busy_tuple

    def add_busy_section(
        self,
        busy_source_row: int,
        busy_target_row: int,
        original_source_row: int,
        original_target_row: int,
        perspective: BUSY_SECTION_PERSPECTIVE = BUSY_SECTION_PERSPECTIVE.SOURCE,
    ):
        """
        Registers a new busy section in this lane.

        Args:
            busy_source_row (int): The starting row index of the busy section.
            busy_target_row (int): The ending row index of the busy section.
            original_source_row (int): The original starting row referenced in the flow.
            original_target_row (int): The original target row referenced in the flow.
            perspective (BUSY_SECTION_PERSPECTIVE):
                The perspective from which the busy section is assigned (source/target).
        """

        self.busy_sections.append(
            self.get_busy_tuple(
                busy_source_row=busy_source_row,
                busy_target_row=busy_target_row,
                original_source_row=original_source_row,
                original_target_row=original_target_row,
                perspective=perspective,
            )
        )

    def add_used_docker(self, docker: Coordinates):
        """
        Adds a docker coordinate to this lane.

        Args:
            docker (Coordinates): The coordinate of a docker used in this lane.
        """

        self.dockers_in_lane.append(docker)
