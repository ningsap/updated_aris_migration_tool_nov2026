from copy import deepcopy
from typing import Dict

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.helpers.STATICS import CARDINAL_DIRECTIONS as CD
from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.coordinates_handler import CoordinatesHandler
from diagramforge.rendering.flows.flow_corridor_manager import FlowCorridorManager
from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup
from diagramforge.rendering.flows.port_adapter import PortAdapter
from diagramforge.rendering.flows.port_connection import PortConnection
from diagramforge.rendering.flows.vertical_corridor import VerticalCorridor
from diagramforge.rendering.flows.vertical_corridor_lane import VerticalCorridorLane
from diagramforge.schema.base import AssociationLabel, GatewayLabel
from diagramforge.schema.shapes import CollapsedPool, Gateway, ShapeBase
from diagramforge.SETUP import forge_logger


class LabelPlacer:
    """
    A class to place labels on sequence flows and gateways in a BPMN diagram.

    Attributes:
        coordinates_handler (CoordinatesHandler): Handler for managing coordinates.
        association_resource_id_to_port_connection_mapping (dict[str, PortConnection]): Mapping of association resource IDs to port connections.
        shape_resource_id_to_port_adapter_mapping (dict[str, PortAdapter]): Mapping of shape resource IDs to port adapters.
        flow_corridor_manager (FlowCorridorManager): Manager for flow corridors.
        global_grid_lookup (GlobalGridLookup): Lookup utility for global grid.
        resource_id_to_shape_mapping (Dict[str, ShapeBase]): Mapping of resource IDs to shape objects.
        label_x_space_created_per_col_above_or_below_shape (dict): Tracks label space created per column above or below shape.
        label_x_space_created_per_col_vertical_corridor_index (dict): Tracks label space created per column vertical corridor index.
    """

    def __init__(
        self,
        coordinates_handler: CoordinatesHandler,
        association_resource_id_to_port_connection_mapping: Dict[str, PortConnection],
        shape_resource_id_to_port_adapter_mapping: Dict[str, PortAdapter],
        flow_corridor_manager: FlowCorridorManager,
        global_grid_lookup: GlobalGridLookup,
        resource_id_to_shape_mapping: Dict[str, ShapeBase],
    ):
        """
        Initializes the LabelPlacer with necessary mappings and handlers.

        Args:
            coordinates_handler (CoordinatesHandler): Handler for managing coordinates.
            association_resource_id_to_port_connection_mapping (dict[str, PortConnection]): Mapping of association resource IDs to port connections.
            shape_resource_id_to_port_adapter_mapping (dict[str, PortAdapter]): Mapping of shape resource IDs to port adapters.
            flow_corridor_manager (FlowCorridorManager): Manager for flow corridors.
            global_grid_lookup (GlobalGridLookup): Lookup utility for global grid.
            resource_id_to_shape_mapping (Dict[str, ShapeBase]): Mapping of resource IDs to shape objects.
        """

        self.coordinates_handler = coordinates_handler
        self.association_resource_id_to_port_connection_mapping = association_resource_id_to_port_connection_mapping
        self.shape_resource_id_to_port_adapter_mapping = shape_resource_id_to_port_adapter_mapping
        self.flow_corridor_manager = flow_corridor_manager
        self.global_grid_lookup = global_grid_lookup
        self.resource_id_to_shape_mapping = resource_id_to_shape_mapping

        self.label_x_space_created_per_col_above_or_below_shape = {}
        self.label_x_space_created_per_col_vertical_corridor_index = {}

    def place_sequence_flow_labels(self):
        """
        Places labels on sequence flows in the diagram.
        """

        # All labels on sequence flows that are NOT direct must be placed first

        for association_id, port_connection in self.association_resource_id_to_port_connection_mapping.items():
            if port_connection.is_straight_direct_connection:
                continue

            if port_connection.relative_position_to_source in [CD.EAST, CD.NORTHEAST, CD.SOUTHEAST]:
                self.__place_label_on_east_bound_connection(port_connection)

            elif port_connection.relative_position_to_source in [
                CD.NORTH,
                CD.NORTHWEST,
                CD.SOUTH,
                CD.SOUTHWEST,
                CD.WEST,
            ]:
                self.__place_label_on_south_and_north_bound_connection(port_connection)

        # Place labels of direct connections
        for association_id, port_connection in self.association_resource_id_to_port_connection_mapping.items():
            if not port_connection.is_straight_direct_connection:
                continue

            self.__place_label_on_direct_connection(port_connection)

        # Place labels on special connections
        for association_id, port_connection in self.association_resource_id_to_port_connection_mapping.items():
            if port_connection.relative_position_to_source in [CD.SOURCE_COLLAPSED_POOL]:
                self.__place_label_on_special_connection(port_connection)

    def __place_label_on_east_bound_connection(self, con: PortConnection):
        """
        Places a label on an east-bound connection.

        Args:
            con (PortConnection): The port connection to place the label on.
        """

        available_label_names = con.association.properties.get_all_names()

        if not available_label_names:
            return

        association_label = AssociationLabel()
        source_multiple_outgoings = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.source].east_port_connections) > 1
        )
        target_multiple_incomings = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.target].west_port_connections) > 1
        )

        # FIX: Check whether it's a connection from collapsed pool to collapsed pool
        if isinstance(self.resource_id_to_shape_mapping[con.source], CollapsedPool) and isinstance(
            self.resource_id_to_shape_mapping[con.target], CollapsedPool
        ):
            return

        # Get X - Start X of the most left lane used for that connection, basically the one directly after a gateway/shape
        most_left_vertical_corridor_lane: VerticalCorridorLane = sorted(
            con.used_vertical_corridor_lanes, key=lambda x: x.lane_start_x.x
        )[0]

        # FOR NOT SPLITTING FLOWS
        if not target_multiple_incomings:
            # Get X
            x_anchor = most_left_vertical_corridor_lane.lane_x_label_anchor_right.x

            # Get Y
            if con.used_horizontal_corridor_lane:
                y_anchor = con.used_horizontal_corridor_lane[0].lane_center_y.y
            else:
                y_anchor = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_y

            target_from_count = 0
            target_from_count += 2 if source_multiple_outgoings else 1

            if con.col_distance == 1:
                target_from_count += 2 if target_multiple_incomings else 1
            else:
                target_from_count += 1

            if FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
                target_from_count += 1

            association_label.x = deepcopy(x_anchor)
            association_label.y = deepcopy(y_anchor)
            association_label.distance = SC.DEFAULT_LABEL_DISTANCE
            association_label.from_ = deepcopy(target_from_count)
            association_label.to = target_from_count + 1

            con.association.labels = [association_label]

            # Determine space for label

            x_space = self.__get_max_label_width(available_label_names)

            if not most_left_vertical_corridor_lane.label_space_created_right_from_vertical_flow:
                most_left_vertical_corridor_lane.added_label_spacer_right_from_vertical_flow += x_space

                self.coordinates_handler.shift_elements(axis="x", shift_amount=x_space, threshold=association_label.x)

        # FOR MERGING FLOWS
        elif target_multiple_incomings:
            # Get X
            x_anchor = most_left_vertical_corridor_lane.lane_x_label_anchor_left.x

            # Get Y
            if con.used_horizontal_corridor_lane:
                y_anchor = con.used_horizontal_corridor_lane[0].lane_center_y.y
            else:
                y_anchor = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_y

            target_from_count = 0

            # Determine space for label

            x_space = self.__get_max_label_width(available_label_names)

            # Assign label later
            association_label.x = deepcopy(x_anchor)
            association_label.y = deepcopy(y_anchor)
            association_label.distance = SC.DEFAULT_LABEL_DISTANCE
            association_label.from_ = deepcopy(target_from_count)
            association_label.to = target_from_count + 1
            association_label.orientation = "ur"

            con.association.labels = [association_label]
            if not most_left_vertical_corridor_lane.label_space_created_left_from_vertical_flow:
                most_left_vertical_corridor_lane.added_label_spacer_left_from_vertical_flow += x_space

                self.coordinates_handler.shift_elements(
                    axis="x",
                    shift_amount=x_space,
                    threshold=association_label.x,
                    include_threshold=True,
                )

        forge_logger.debug(
            f"Placing label with ID {con.association.resource_id} on merging east-bound connection at ({association_label.x}, {association_label.y})"
        )

    def __place_label_on_south_and_north_bound_connection(self, con: PortConnection):
        """
        Places a label on a south or north-bound connection.

        Args:
            con (PortConnection): The port connection to place the label on.
        """

        available_label_names = con.association.properties.get_all_names()

        if not available_label_names:
            return

        association_label = AssociationLabel()
        association_label.align = "right"
        association_label.orientation = "lr"

        source_multiple_outgoings = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.source].south_port_connections) > 1
        )

        target_from_count = 0
        if source_multiple_outgoings:
            target_from_count += 2
            relevant_docker = con.association.dockers[1]
        else:
            target_from_count += 1
            relevant_docker = con.association.dockers[0]

        association_label.x = relevant_docker.x - SC.DOCKER_BRANCHING_DIAGONAL
        association_label.y = deepcopy(relevant_docker.y)
        association_label.distance = (
            SC.DEFAULT_LABEL_DISTANCE
            if con.relative_position_to_source in [CD.NORTH, CD.NORTHWEST]
            else -SC.DEFAULT_LABEL_DISTANCE
        )
        association_label.from_ = deepcopy(target_from_count)
        association_label.to = target_from_count + 1

        con.association.labels = [association_label]

        source_col = self.global_grid_lookup.get_col(con.source)

        if not self.label_x_space_created_per_col_above_or_below_shape.get(source_col):
            self.label_x_space_created_per_col_above_or_below_shape[source_col] = True

            x_shift_threshold = (
                self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_x
                - SC.DEFAULT_SHAPE_WIDTH / 2
            )

            self.coordinates_handler.shift_elements(
                axis="x", shift_amount=SC.LABEL_MAX_WIDTH, threshold=x_shift_threshold, include_threshold=True
            )

        forge_logger.debug(
            f"Placing label with ID {con.association.resource_id} on south/north-bound connection at ({association_label.x}, {association_label.y})"
        )

        pass

    def __place_label_on_direct_connection(self, con: PortConnection):
        """
        Places a label on a direct connection.

        Args:
            con (PortConnection): The port connection to place the label on.
        """

        available_label_names = con.association.properties.get_all_names()

        if not available_label_names:
            return

        association_label = AssociationLabel()
        association_label.distance = SC.DEFAULT_LABEL_DISTANCE
        association_label.from_ = 0
        association_label.to = 1

        source_multiple_outgoings = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.source].east_port_connections) > 1
        )

        target_multiple_incomings = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.target].west_port_connections) > 1
        )

        source_col = self.global_grid_lookup.get_col(con.source)

        source_vertical_corridor: VerticalCorridor = self.flow_corridor_manager.vertical_corridors_by_col[source_col]

        x_space = self.__get_max_label_width(available_label_names)

        if not source_vertical_corridor.active_vertical_lanes:
            source_vertical_corridor.add_vertical_corridor_lane(add_where=VerticalCorridor.ADD_WHERE.FIRST_LEFT)

        most_right_vertical_corridor_lane: VerticalCorridorLane = sorted(
            source_vertical_corridor.active_vertical_lanes,
            key=lambda x: x.lane_start_x.x,
        )[0]

        if not target_multiple_incomings:
            x_anchor = most_right_vertical_corridor_lane.lane_x_label_anchor_right.x
        else:
            x_anchor = most_right_vertical_corridor_lane.lane_x_label_anchor_left.x

        y_anchor = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_y

        association_label.x = deepcopy(x_anchor)
        association_label.y = deepcopy(y_anchor)

        association_label.orientation = "ur" if target_multiple_incomings else "ll"

        con.association.labels = [association_label]

        if (
            not most_right_vertical_corridor_lane.label_space_created_right_from_vertical_flow
            and not target_multiple_incomings
        ):
            most_right_vertical_corridor_lane.added_label_spacer_right_from_vertical_flow += x_space

            self.coordinates_handler.shift_elements(axis="x", shift_amount=x_space, threshold=association_label.x)
        elif (
            not most_right_vertical_corridor_lane.label_space_created_left_from_vertical_flow
            and target_multiple_incomings
        ):
            most_right_vertical_corridor_lane.added_label_spacer_left_from_vertical_flow += x_space

            self.coordinates_handler.shift_elements(
                axis="x",
                shift_amount=x_space,
                threshold=association_label.x,
                include_threshold=True,
            )

        forge_logger.debug(
            f"Placing label with ID {con.association.resource_id} on merging direct east-bound connection at ({association_label.x}, {association_label.y})"
        )

    def __place_label_on_special_connection(self, con: PortConnection):
        """
        Places a label on a special connection.

        Args:
            con (PortConnection): The port connection to place the label on.
        """

        available_label_names = con.association.properties.get_all_names()

        if not available_label_names:
            return

        association_label = AssociationLabel()
        association_label.distance = SC.DEFAULT_LABEL_DISTANCE
        association_label.from_ = 2
        association_label.to = 3

        target_col = self.global_grid_lookup.get_col(con.target)

        if target_col == 0:
            target_col = -1

        target_vertical_corridor: VerticalCorridor = self.flow_corridor_manager.vertical_corridors_by_col[target_col]

        x_space = self.__get_max_label_width(available_label_names)

        x_anchor = con.association.dockers[-1].x

        y_anchor = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_y

        association_label.x = deepcopy(x_anchor) + SC.DOCKER_BRANCHING_DIAGONAL
        association_label.y = deepcopy(y_anchor)
        association_label.distance = SC.DEFAULT_LABEL_DISTANCE

        association_label.orientation = "ul"

        con.association.labels = [association_label]

        if not self.label_x_space_created_per_col_above_or_below_shape.get(target_col):
            self.label_x_space_created_per_col_above_or_below_shape[target_col] = True

            self.coordinates_handler.shift_elements(
                axis="x",
                shift_amount=x_space,
                threshold=association_label.x,
            )

        forge_logger.debug(
            f"Placing label with ID {con.association.resource_id} on special connection at ({association_label.x}, {association_label.y})"
        )

    def __get_max_label_width(self, label_name_dict: dict[str, str]) -> float:
        """
        Calculates the maximum width of a label based on its name.

        Args:
            label_name_dict (dict[str, str]): Dictionary of label names.

        Returns:
            float: The maximum width of the label.
        """

        label_name_split_by_language = [name.split("\n") for name in label_name_dict.values()]

        x_space = (
            len(max([name for name_list in label_name_split_by_language for name in name_list], key=len))
            * SC.AVERAGE_CHAR_WIDTH
        )

        return x_space if x_space < SC.LABEL_MAX_WIDTH else SC.LABEL_MAX_WIDTH

    def place_gateway_labels(self):
        """
        Places labels on gateways in the diagram.
        """

        for shape_id, shape in self.resource_id_to_shape_mapping.items():
            if isinstance(shape, Gateway):
                all_label_names = shape.properties.get_all_names()

                if not all_label_names:
                    continue

                max_label_width = self.__get_max_label_width(all_label_names)

                if max_label_width > SC.DEFAULT_SHAPE_WIDTH:
                    gateway_center_x = self.coordinates_handler.shape_coords_record_by_resource_id[
                        shape_id
                    ].global_center_x

                    left_move_point_x = gateway_center_x - SC.DEFAULT_SHAPE_WIDTH / 2
                    right_move_point_x = gateway_center_x + SC.DEFAULT_SHAPE_WIDTH / 2

                    abs_side_shift_amount = abs((max_label_width - SC.DEFAULT_SHAPE_WIDTH) / 2)

                    self.coordinates_handler.shift_elements(
                        axis="x", shift_amount=abs_side_shift_amount, threshold=right_move_point_x
                    )
                    self.coordinates_handler.shift_elements(
                        axis="x",
                        shift_amount=abs_side_shift_amount,
                        threshold=left_move_point_x,
                        include_threshold=True,
                    )

                shape.labels = [GatewayLabel()]
