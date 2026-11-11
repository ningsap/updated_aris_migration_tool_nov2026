from typing import List, Tuple
from uuid import uuid4

from diagramforge.helpers.STATICS import H_CORRIDOR_LANE_BUSY_DIRECTION
from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup
from diagramforge.rendering.render_helpers import AuxCoordY
from diagramforge.schema.base import Coordinates


class HorizontalCorridorLane:
    """
    Represents a horizontal corridor lane used for routing flows.

    Manages busy sections, dockers, and layout computations.

    Attributes:
        busy_sections (List[tuple[int, int, H_CORRIDOR_LANE_BUSY_DIRECTION]]):
            A list of tuples tracking which columns are busy (start, end, direction).
        dockers_in_lane (List[Coordinates]):
            A list of docker coordinates already placed in this lane.
        added_label_spacer (float):
            Additional vertical space allocated for lane labeling.
        lane_start_y (AuxCoordY):
            The vertical starting point of the lane.
    """

    def __init__(
        self,
        lane_start_y: AuxCoordY,
    ) -> None:
        """
        Initializes a new HorizontalCorridorLane.

        Args:
            lane_start_y (AuxCoordY):
                The vertical starting position of the lane.
        """

        self.id = str(uuid4())
        self.busy_sections: List[Tuple[int, int, H_CORRIDOR_LANE_BUSY_DIRECTION]] = []
        self.dockers_in_lane: List[Coordinates] = []
        self.added_label_spacer: float = 0.0

        self.lane_start_y: AuxCoordY = lane_start_y

    @property
    def label_space_created(self) -> bool:
        """
        Checks if additional label space has been allocated.

        Returns:
            bool: True if label space is allocated, otherwise False.
        """

        return self.added_label_spacer > 0.0

    @property
    def lane_height(self) -> float:
        """
        Calculates the total lane height, including any label spacing.

        Returns:
            float: The total height of the lane.
        """

        return SC.HORIZONTAL_CORRIDOR_LANE_HEIGHT + self.added_label_spacer

    @property
    def lane_end_y(self) -> AuxCoordY:
        """
        Determines the vertical end coordinate of this lane.

        Returns:
            AuxCoordY: The vertical ending position of the lane.
        """

        return AuxCoordY(self.lane_start_y.y + SC.HORIZONTAL_CORRIDOR_LANE_HEIGHT + self.added_label_spacer)

    @property
    def lane_center_y(self) -> AuxCoordY:
        """
        Computes the vertical center of the lane.

        Returns:
            AuxCoordY: The vertical center position of the lane.
        """

        return AuxCoordY(self.lane_start_y.y + (SC.HORIZONTAL_CORRIDOR_LANE_HEIGHT / 2))

    @property
    def lane_top_docker_anchor(self) -> AuxCoordY:
        """
        Determines the vertical anchor point for top dockers.

        Returns:
            AuxCoordY: The vertical anchor coordinate for top dockers.
        """

        return AuxCoordY(self.lane_start_y.y + SC.HORIZONTAL_LANE_BORDER_TO_DOCKER_ANCHOR_BUFFER)

    @property
    def lane_bottom_docker_anchor(self) -> AuxCoordY:
        """
        Determines the vertical anchor point for bottom dockers.

        Returns:
            AuxCoordY: The vertical anchor coordinate for bottom dockers.
        """

        return AuxCoordY(
            self.lane_end_y.y - SC.HORIZONTAL_LANE_BORDER_TO_DOCKER_ANCHOR_BUFFER - self.added_label_spacer
        )

    @property
    def lane_label_y_label_anchor(self) -> AuxCoordY:
        """
        Determines the vertical anchor point for lane labeling.

        Returns:
            AuxCoordY: The anchor coordinate to place a label in the lane.
        """

        return AuxCoordY(self.lane_end_y.y - (SC.HORIZONTAL_CORRIDOR_LANE_HEIGHT / 2) - self.added_label_spacer)

    def __repr__(self) -> str:
        """
        Returns a string representation of the lane with details about positions and busy sections.

        Returns:
            str: A description of the HorizontalCorridorLane object.
        """

        return (
            f"HorizontalCorridorLane at {self.lane_start_y} to {self.lane_end_y} -> Busy Sections: {self.busy_sections}"
        )

    @staticmethod
    def get_busy_tuple(source_col: int, target_col: int) -> tuple[int, int, H_CORRIDOR_LANE_BUSY_DIRECTION]:
        """
        Creates a tuple indicating which columns are busy and in which direction they extend.

        Args:
            source_col (int):
                The starting column index.
            target_col (int):
                The ending column index.

        Returns:
            tuple[int, int, H_CORRIDOR_LANE_BUSY_DIRECTION]:
                A tuple containing the source column, target column, and busy direction.
        """

        return (source_col, target_col, GlobalGridLookup.get_horizontal_busy_direction(source_col, target_col))

    def add_busy_section(self, source_col: int, target_col: int):
        """
        Adds a new busy section to this lane.

        Args:
            source_col (int):
                The starting column index.
            target_col (int):
                The ending column index.
        """

        self.busy_sections.append(self.get_busy_tuple(source_col, target_col))

    def add_used_docker(self, docker: Coordinates):
        """
        Adds a docker coordinate to this lane, indicating it's used.

        Args:
            docker (Coordinates):
                The coordinate of the used docker.
        """

        self.dockers_in_lane.append(docker)
