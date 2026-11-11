from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.schema.base import Coordinates


class CoordsCalculator:
    """
    This class is responsible for calculating the coordinates of the shapes in the diagram.
    It's rather a helper class that provides static methods so the formulas are not scattered around the code.
    """

    @staticmethod
    def calculate_col_mid_x(col: int) -> float:
        return SC.LANE_HEADER + (col * SC.COL_WIDTH) + (SC.COL_WIDTH / 2)

    @staticmethod
    def calculate_row_mid_y(row: int) -> float:
        return SC.LANE_V_BUFFER + (row * SC.COL_HEIGHT) + (SC.COL_HEIGHT / 2)

    @staticmethod
    def calculate_lane_width(lane_max_x: float) -> float:
        return lane_max_x + (SC.H_SHAPE_SPACER * 2)

    @staticmethod
    def calculate_lane_height(lane_max_y: float) -> float:
        return lane_max_y + (SC.LANE_V_BUFFER * 2)

    @staticmethod
    def calculate_vertical_corridor_start_x(center_x: float) -> float:
        return center_x + (SC.DEFAULT_SHAPE_WIDTH / 2)

    @staticmethod
    def calculate_horizontal_corridor_start_y(center_y: float) -> float:
        return center_y + (SC.DEFAULT_SHAPE_HEIGHT / 2) + SC.HORIZONTAL_CORRIDOR_START_BUFFER

    @staticmethod
    def calculate_source_branching_start_docker(
        v_corridor_lane_start_x: float,
        source_row_center_y: float,
    ) -> Coordinates:
        return Coordinates(x=v_corridor_lane_start_x, y=source_row_center_y)

    @staticmethod
    def calculate_source_branching_end_docker_upwards(
        source_row_center_x: float,
        h_corridor_lane_center_y: float,
    ):
        return Coordinates(x=source_row_center_x - SC.DOCKER_BRANCHING_DIAGONAL, y=h_corridor_lane_center_y)

    def calculate_source_branching_end_docker_downwards(
        source_row_center_x: float,
        h_corridor_lane_center_y: float,
    ):
        return Coordinates(x=source_row_center_x - SC.DOCKER_BRANCHING_DIAGONAL, y=h_corridor_lane_center_y)

    @staticmethod
    def calculate_source_branching_end_docker(
        v_corridor_lane_center_x: float,
        source_row_center_y: float,
        target_row_center_y: float,
    ) -> Coordinates:
        return Coordinates(
            x=v_corridor_lane_center_x,
            y=source_row_center_y
            + (
                SC.DOCKER_BRANCHING_DIAGONAL
                if target_row_center_y > source_row_center_y
                else -SC.DOCKER_BRANCHING_DIAGONAL
            ),
        )

    @staticmethod
    def calculate_target_merging_start_docker(
        v_corridor_lane_center_x: float,
        source_row_center_y: float,
        target_row_center_y: float,
        is_top_over_connection: bool = False,
    ) -> Coordinates:
        top_over_y = None
        if is_top_over_connection:
            top_over_y = target_row_center_y + (
                -SC.DOCKER_BRANCHING_DIAGONAL
                if target_row_center_y >= source_row_center_y
                else SC.DOCKER_BRANCHING_DIAGONAL
            )

        return Coordinates(
            x=v_corridor_lane_center_x,
            y=top_over_y
            or target_row_center_y
            + (
                -SC.DOCKER_BRANCHING_DIAGONAL
                if target_row_center_y > source_row_center_y
                else SC.DOCKER_BRANCHING_DIAGONAL
            ),
        )
