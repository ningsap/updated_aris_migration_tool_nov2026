from copy import deepcopy

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.coordinates_handler import CoordinatesHandler
from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup
from diagramforge.rendering.flows.horizontal_corridor import HorizontalCorridor
from diagramforge.rendering.flows.vertical_corridor import VerticalCorridor
from diagramforge.SETUP import forge_logger


class FlowCorridorManager:
    """Manages the creation and organization of corridor objects for flow diagrams.

    This class handles both vertical and horizontal corridors based on the global grid
    and coordinates provided. The corridors are stored in dictionaries, accessible by
    row or column.
    """

    def __init__(
        self,
        global_grid_lookup: GlobalGridLookup,
        coordinates_handler: CoordinatesHandler,
    ) -> None:
        """Initializes the FlowCorridorManager with a global grid lookup and a coordinates handler.

        Args:
            global_grid_lookup (GlobalGridLookup): The global grid lookup instance for row and column details.
            coordinates_handler (CoordinatesHandler): The coordinates handler for managing bounding and positioning.
        """

        self.global_grid_lookup = global_grid_lookup
        self.coordinates_handler = coordinates_handler

        self.vertical_corridors_by_col: dict[int, VerticalCorridor] = {}
        self.horizontal_corridors_by_row: dict[int, HorizontalCorridor] = {}

    def build_corridors(self):
        """Builds both vertical and horizontal corridors.

        This method triggers the creation of corridors in both orientations by
        calling the respective private methods.
        """

        self.__build_vertical_corridors()

        self.__build_horizontal_corridors()

    def __build_vertical_corridors(self):
        """Creates and stores vertical corridors.

        Iterates over each column in the global grid to instantiate and store
        VerticalCorridor objects, mapping them by column index.
        """

        for col in range(self.global_grid_lookup.max_col + 1):
            vertical_corridor = VerticalCorridor(
                from_col=deepcopy(col),
                coordinates_handler=self.coordinates_handler,
                global_grid_lookup=self.global_grid_lookup,
            )

            forge_logger.debug(f"Created: {vertical_corridor}")

            self.vertical_corridors_by_col[col] = vertical_corridor

        # Add -1

        vertical_corridor = VerticalCorridor(
            from_col=-1,
            coordinates_handler=self.coordinates_handler,
            global_grid_lookup=self.global_grid_lookup,
        )

        random_shape_coords_record_of_first_col = self.coordinates_handler.shape_coords_record_by_resource_id[
            self.global_grid_lookup.get_shapes_in_col(0)[0]
        ]

        shape_width = (
            random_shape_coords_record_of_first_col.global_bounds.lowerRight.x
            - random_shape_coords_record_of_first_col.global_bounds.upperLeft.x
        )

        center_x = random_shape_coords_record_of_first_col.global_bounds.lowerRight.x - shape_width / 2
        self.vertical_corridors_by_col[-1] = vertical_corridor

        FORGE_CONFIG.LEFT_VERTICAL_CORRIDOR_LANE_START_X_SAVE = center_x - SC.COL_WIDTH

    def __build_horizontal_corridors(self):
        """Creates and stores horizontal corridors.

        Iterates over each row in the global grid to instantiate and store
        HorizontalCorridor objects, mapping them by row index. Additionally,
        a special horizontal corridor is added at row index -1 to manage
        the top boundary of the diagram.
        """

        for row in range(self.global_grid_lookup.max_row + 1):
            horizontal_corridor = HorizontalCorridor(
                from_row=deepcopy(row),
                coordinates_handler=self.coordinates_handler,
                global_grid_lookup=self.global_grid_lookup,
            )

            forge_logger.debug(f"Created: {horizontal_corridor}")

            self.horizontal_corridors_by_row[row] = horizontal_corridor

        # Add -1

        horizontal_corridor = HorizontalCorridor(
            from_row=-1,
            coordinates_handler=self.coordinates_handler,
            global_grid_lookup=self.global_grid_lookup,
        )

        random_shape_coords_record_of_first_row = self.coordinates_handler.shape_coords_record_by_resource_id[
            self.global_grid_lookup.get_shapes_in_row(0)[0]
        ]

        shape_height = (
            random_shape_coords_record_of_first_row.global_bounds.lowerRight.y
            - random_shape_coords_record_of_first_row.global_bounds.upperLeft.y
        )
        center_y = random_shape_coords_record_of_first_row.global_bounds.lowerRight.y - shape_height / 2
        self.horizontal_corridors_by_row[-1] = horizontal_corridor

        FORGE_CONFIG.TOP_HORIZONTAL_CORRIDOR_LANE_START_Y_SAVE = center_y - SC.COL_HEIGHT
