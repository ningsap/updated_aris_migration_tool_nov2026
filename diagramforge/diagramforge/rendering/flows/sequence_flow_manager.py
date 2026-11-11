from collections import defaultdict
from copy import deepcopy
from typing import Dict

from networkx import MultiDiGraph

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.exceptions.flow_positioning import InvalidColumnDistance
from diagramforge.helpers.STATICS import BUSY_SECTION_PERSPECTIVE
from diagramforge.helpers.STATICS import CARDINAL_DIRECTIONS as CD
from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.coordinates_handler import CoordinatesHandler
from diagramforge.rendering.coords_calculator import CoordsCalculator as CC
from diagramforge.rendering.flows.flow_corridor_manager import FlowCorridorManager
from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup
from diagramforge.rendering.flows.horizontal_corridor import HorizontalCorridor
from diagramforge.rendering.flows.horizontal_corridor_lane import HorizontalCorridorLane
from diagramforge.rendering.flows.port_adapter import PortAdapter
from diagramforge.rendering.flows.port_connection import PortConnection
from diagramforge.rendering.flows.vertical_corridor import VerticalCorridor
from diagramforge.rendering.flows.vertical_corridor_lane import VerticalCorridorLane
from diagramforge.schema.base import Coordinates, ShapeBase
from diagramforge.schema.shapes import Association, Diagram, Lane, Pool
from diagramforge.SETUP import forge_logger


class SequenceFlowManager:
    """Manages sequence flow layout and docker calculations for diagram elements.

    This class handles the creation of port adapters, flow corridors, and calculates
    connection paths (dockers) between diagram elements based on their grid positions.
    """

    def __init__(
        self,
        source_graph: MultiDiGraph,
        diagram: Diagram,
        resource_id_to_shape_mapping: Dict[str, ShapeBase],
        global_grid_lookup: GlobalGridLookup,
        coordinates_handler: CoordinatesHandler,
        node_resource_id_to_parent_mapping: Dict[str, str],
    ) -> None:
        """Initializes SequenceFlowManager with diagram data and helper components.

        Args:
            source_graph (MultiDiGraph): Internal graph representation of the diagram.
            diagram (Diagram): The diagram model containing all shapes and relationships.
            resource_id_to_shape_mapping (Dict[str, ShapeBase]): Maps resource IDs to shape objects.
            global_grid_lookup (GlobalGridLookup): Helper for grid-based position lookups.
            coordinates_handler (CoordinatesHandler): Manages coordinates and bounds for shapes.
            node_resource_id_to_parent_mapping (Dict[str, str]): Maps node resource IDs to their parent shapes.
        """

        self.source_graph = source_graph
        self.diagram = diagram
        self.resource_id_to_shape_mapping = resource_id_to_shape_mapping
        self.global_grid_lookup = global_grid_lookup
        self.coordinates_handler = coordinates_handler
        self.node_resource_id_to_parent_mapping = node_resource_id_to_parent_mapping

        # Cross-methodical class instance variables in order of usage
        self.shape_resource_id_to_port_adapter_mapping: Dict[str, PortAdapter] = None
        self.association_resource_id_to_port_connection_mapping: Dict[str, PortConnection] = None

    def build_port_adapter_mapping(self):
        """Builds port adapters and connection mappings for all shapes.

        Iterates through all shapes in the diagram and creates:
        - PortAdapters for each shape that can have connections
        - PortConnections for all outgoing relationships
        - Cross-references between shapes and their connections

        Populates:
            shape_resource_id_to_port_adapter_mapping
            association_resource_id_to_port_connection_mapping
        """

        # Iterate over all shapes in the diagram since all shapes can be a source or target of a sequence flow
        # and create a mapping of resource_id to PortConnection mapping
        self.shape_resource_id_to_port_adapter_mapping = defaultdict(PortAdapter)
        self.association_resource_id_to_port_connection_mapping = defaultdict(PortConnection)

        # Collect all outgoing connections for each shape and create a PortAdapter object for each shape
        for shape_id, shape in self.resource_id_to_shape_mapping.items():
            if isinstance(shape, (Diagram, Lane, Association)):
                continue

            forge_logger.debug(f"Building port adapter for shape {shape_id}")

            node_outgoing_ids = [out.resource_id for out in shape.outgoing]

            port_connections: list[PortConnection] = []

            for outgoing_id in node_outgoing_ids:
                if not self.resource_id_to_shape_mapping.get(outgoing_id):
                    continue

                port_connection = PortConnection(
                    source=shape_id,
                    association=self.resource_id_to_shape_mapping[outgoing_id],
                    global_grid_lookup=self.global_grid_lookup,
                )

                if not port_connection.relative_position_to_source:
                    forge_logger.warning(f"Port connection {port_connection} has no relative position to source.")
                    continue

                port_connections.append(port_connection)

                self.association_resource_id_to_port_connection_mapping[outgoing_id] = port_connection

            port_adapter = PortAdapter(
                bound_shape=shape, all_outgoing_connections=port_connections, global_grid_lookup=self.global_grid_lookup
            )

            self.shape_resource_id_to_port_adapter_mapping[shape_id] = port_adapter

        # Iterate over all created port adapters and assign and collect all incoming connections
        for shape_id, port_adapter in self.shape_resource_id_to_port_adapter_mapping.items():
            for outgoing_connection in port_adapter.all_outgoing_connections:
                target_port_adapter = self.shape_resource_id_to_port_adapter_mapping[outgoing_connection.target]

                target_port_adapter.west_port_connections.append(outgoing_connection)

    def build_flow_corridors(self):
        """Initializes and builds flow corridor infrastructure.

        Creates vertical and horizontal corridors based on global grid layout.
        """

        self.flow_corridor_manager = FlowCorridorManager(
            global_grid_lookup=self.global_grid_lookup,
            coordinates_handler=self.coordinates_handler,
        )

        self.flow_corridor_manager.build_corridors()

    def calculate_dockers(self):
        """Calculates docker positions for all connections in the diagram.

        Processes columns from right to left (last to first), handling:
        - East-bound connections (same and multiple column distances)
        - North/South-bound connections in subsequent passes

        Delegates detailed calculations to specialized layout methods.
        """

        # Iterate over all shapes of all columns starting from the last column

        for col in range(self.global_grid_lookup.max_col, -1, -1):
            # for col in range(self.global_grid_lookup.max_col + 1):

            shapes_in_col = self.global_grid_lookup.get_shapes_in_col(col)

            for shape_id in shapes_in_col:
                port_adapter: PortAdapter = self.shape_resource_id_to_port_adapter_mapping[shape_id]

                # ----- EAST BOUND CONNECTIONS -----

                east_connections = [
                    con for con in port_adapter.east_port_connections if not con.is_straight_direct_connection
                ]

                for east_con in sorted(east_connections, key=lambda x: abs(x.order)):
                    self.__layout_east_port_connection_dockers(con=east_con)

        for col in range(self.global_grid_lookup.max_col, -1, -1):
            shapes_in_col = self.global_grid_lookup.get_shapes_in_col(col)

            for shape_id in shapes_in_col:
                port_adapter: PortAdapter = self.shape_resource_id_to_port_adapter_mapping[shape_id]

                # ----- NORTH BOUND CONNECTIONS -----

                for north_con in sorted(port_adapter.north_port_connections, key=lambda x: abs(x.order)):
                    self.__layout_north_port_connection_dockers(north_con)

                # ----- SOUTH BOUND CONNECTIONS -----

                for south_con in sorted(port_adapter.south_port_connections, key=lambda x: abs(x.order)):
                    self.__layout_south_port_connection_dockers(south_con)

        # ----- SPECIAL CONNECTIONS -----
        for shape_id, port_adapter in self.shape_resource_id_to_port_adapter_mapping.items():
            # Special connections are those that are not east, north, or south bound
            # but rather have a specific layout requirement (e.g., collapsed pools)
            if not port_adapter.special_connections:
                continue

            for special_con in port_adapter.special_connections:
                self.__layout_special_port_connection_dockers(special_con)

    def append_bounds(self):
        """
        Bounds of associations have no real impact on the visual representation but lead to bugs in the Collaboration
        Hub if left empty (or zeroed).

        The upperLeft and lowerRight are just representing the relative bounds at what is "lower right" and "upper left"
        and are not connected to the start or end points of the association.

        The coordinates of lowerRight and upperLeft are the result of the min and max coordinates of the connected shapes
        as well as the dockers of the association itself.
        """

        association_to_outgoing_mapping = defaultdict(str)
        # Iterate over all shapes and collect all outgoing associations
        for shape_id, shape in self.resource_id_to_shape_mapping.items():
            if isinstance(shape, Association):
                continue

            shape_outgoing_list = getattr(shape, "outgoing", [])

            if not shape_outgoing_list:
                continue

            for outgoing in shape_outgoing_list:
                association_to_outgoing_mapping[outgoing.resource_id] = shape_id

        for association in self.resource_id_to_shape_mapping.values():
            if not isinstance(association, Association):
                continue

            source_shape = self.resource_id_to_shape_mapping.get(
                association_to_outgoing_mapping.get(association.resource_id)
            )
            target_shape = self.resource_id_to_shape_mapping.get(association.target.resource_id)

            if not source_shape or not target_shape:
                forge_logger.debug(
                    f"Association {association.resource_id} has no valid source or target shape. Skipping bounds assignment."
                )
                continue

            source_shape_coords = self.coordinates_handler.shape_coords_record_by_resource_id.get(
                source_shape.resource_id
            )

            target_shape_coords = self.coordinates_handler.shape_coords_record_by_resource_id.get(
                target_shape.resource_id
            )

            if not source_shape_coords or not target_shape_coords:
                forge_logger.debug(
                    f"Association {association.resource_id} has no valid coordinates for source or target shape. Skipping bounds assignment."
                )
                continue

            all_x_coords = [
                source_shape_coords.global_bounds.upperLeft.x,
                target_shape_coords.global_bounds.upperLeft.x,
            ]
            all_y_coords = [
                source_shape_coords.global_bounds.upperLeft.y,
                target_shape_coords.global_bounds.upperLeft.y,
            ]

            if len(association.dockers) > 2:
                # If dockers are present, include their coordinates in the bounds calculation
                all_x_coords.extend(docker.x for docker in association.dockers[1:-1])  # Exclude first and last docker
                all_y_coords.extend(docker.y for docker in association.dockers[1:-1])

            association.bounds.upperLeft = Coordinates(
                x=min(all_x_coords),
                y=min(all_y_coords),
            )
            association.bounds.lowerRight = Coordinates(
                x=max(all_x_coords),
                y=max(all_y_coords),
            )

    def __layout_east_port_connection_dockers(
        self,
        con: PortConnection,
    ):
        """Calculates dockers for east-bound port connections.

        Args:
            con: PortConnection to calculate dockers for

        Raises:
            InvalidColumnDistance: If connection spans <=0 columns
        """

        source_row: int = self.global_grid_lookup.get_row(resource_id=con.source)
        source_col: int = self.global_grid_lookup.get_col(resource_id=con.source)

        target_row: int = self.global_grid_lookup.get_row(resource_id=con.target)
        target_col: int = self.global_grid_lookup.get_col(resource_id=con.target)

        forge_logger.debug(f"Calculating dockers for EAST connection: {con}")

        if con.is_target_collapsed_pool or con.is_target_pool:
            con.col_distance = 1

            target_row = self.global_grid_lookup.get_occupied_row_for_collapsed_pool_outgoing_connection(
                source=con.source,
                target=con.target,
            )

            target_col = source_col

        if con.col_distance == 1:
            vertical_corridor: VerticalCorridor = self.flow_corridor_manager.vertical_corridors_by_col[source_col]

            # UPDATE 08.04.2025
            # Issue: Connections that are merged on gateways = multiple incoming connections
            # are not correctly sorted and overlap one another.
            # Interim solution: In case a node has only one outgoing connection and/or the target node
            # has multiple incoming connections, add_where should be set to FIRST_LEFT

            add_where = None
            source_node_outgoing = len(list(self.source_graph.successors(con.source)))
            target_node_incoming = len(list(self.source_graph.predecessors(con.target)))

            if source_node_outgoing == 1 and target_node_incoming > 1:
                add_where = VerticalCorridor.ADD_WHERE.LAST_RIGHT
            else:
                add_where = VerticalCorridor.ADD_WHERE.FIRST_LEFT

            vertical_corridor_lane = vertical_corridor.get_available_vertical_corridor_lane(
                busy_source_row=source_row,
                busy_target_row=target_row,
                original_source_row=source_row,
                original_target_row=target_row,
                perspective=BUSY_SECTION_PERSPECTIVE.SOURCE,
                add_where=add_where,
            )

            con.append_used_lanes(used_lanes=vertical_corridor_lane)

            # Create dockers in association object
            self.__generate_dockers_for_east_bound_next_column_connection(
                con=con, v_corridor_lane=vertical_corridor_lane
            )

        elif con.col_distance > 1:
            source_vertical_corridor: VerticalCorridor = self.flow_corridor_manager.vertical_corridors_by_col[
                source_col
            ]

            if con.relative_position_to_source == CD.EAST:
                pick_horizontal_corridor_row = source_row - 1
            else:
                pick_horizontal_corridor_row = int(target_row if target_row < source_row else target_row - 1)

            target_horizontal_corridor: HorizontalCorridor = self.flow_corridor_manager.horizontal_corridors_by_row[
                pick_horizontal_corridor_row
            ]
            target_vertical_corridor: VerticalCorridor = self.flow_corridor_manager.vertical_corridors_by_col[
                target_col - 1
            ]

            source_vertical_corridor_lane = source_vertical_corridor.get_available_vertical_corridor_lane(
                busy_source_row=source_row,
                busy_target_row=target_row,
                original_source_row=source_row,
                original_target_row=target_row,
                add_where=VerticalCorridor.ADD_WHERE.LAST_RIGHT
                if con.relative_position_to_source == CD.EAST
                else VerticalCorridor.ADD_WHERE.FIRST_LEFT,
            )

            target_horizontal_corridor_lane = target_horizontal_corridor.get_available_horizontal_corridor_lane(
                source_col=source_col, target_col=target_col - 1
            )

            # UPDATE 08.04.2025 (see above)
            add_where = None
            source_node_outgoing = len(list(self.source_graph.successors(con.source)))
            target_node_incoming = len(list(self.source_graph.predecessors(con.target)))

            if source_node_outgoing == 1 and target_node_incoming > 1:
                add_where = VerticalCorridor.ADD_WHERE.LAST_RIGHT
            else:
                add_where = VerticalCorridor.ADD_WHERE.FIRST_LEFT

            target_vertical_corridor_lane = target_vertical_corridor.get_available_vertical_corridor_lane(
                busy_source_row=pick_horizontal_corridor_row,
                busy_target_row=pick_horizontal_corridor_row,
                original_source_row=source_row,
                original_target_row=target_row,
                perspective=BUSY_SECTION_PERSPECTIVE.TARGET,
                add_where=add_where,
            )

            con.append_used_lanes(
                used_lanes=[
                    source_vertical_corridor_lane,
                    target_horizontal_corridor_lane,
                    target_vertical_corridor_lane,
                ]
            )

            # Create dockers in association object
            self.__generate_dockers_for_east_bound_connections(
                con=con,
                source_vertical_corridor_lane=source_vertical_corridor_lane,
                target_horizontal_corridor_lane=target_horizontal_corridor_lane,
                target_vertical_corridor_lane=target_vertical_corridor_lane,
            )

        else:
            raise InvalidColumnDistance(
                distance=con.col_distance, source_resource_id=con.source, target_resource_id=con.target
            )

    def __generate_dockers_for_east_bound_next_column_connection(
        self, con: PortConnection, v_corridor_lane: VerticalCorridorLane
    ):
        """
        Generates dockers for direct east-bound connections (1 column distance).
        These connections require only a single vertical corridor lane.

        Args:
            con: PortConnection being processed
            v_corridor_lane: Vertical corridor lane used for this connection
        """

        association_docker: list[Coordinates] = con.association.dockers

        source_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_y
        target_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_y

        source_multiple_outgoing = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.source].east_port_connections) > 1
        )
        target_multiple_incoming = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.target].west_port_connections) > 1
        )

        if source_multiple_outgoing or FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
            # Start of branching docker
            source_branching_start_docker = Coordinates(
                x=v_corridor_lane.lane_left_docker_anchor.x, y=source_row_center_y
            )

            association_docker.append(source_branching_start_docker)
            v_corridor_lane.add_used_docker(source_branching_start_docker)

            # End of branching docker
            source_branching_end_docker = CC.calculate_source_branching_end_docker(
                v_corridor_lane_center_x=v_corridor_lane.lane_center_x.x,
                source_row_center_y=source_row_center_y,
                target_row_center_y=target_row_center_y,
            )

            association_docker.append(source_branching_end_docker)
            v_corridor_lane.add_used_docker(source_branching_end_docker)

            con.possible_label_y_positions.append(source_branching_end_docker.y)

        else:
            angled_branching_docker = Coordinates(x=v_corridor_lane.lane_center_x.x, y=source_row_center_y)

            association_docker.append(angled_branching_docker)
            v_corridor_lane.add_used_docker(angled_branching_docker)

            con.possible_label_y_positions.append(angled_branching_docker.y)

        if not (con.is_target_collapsed_pool or con.is_target_pool):
            if target_multiple_incoming or FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
                # Start of merging docker
                target_merging_start_docker = CC.calculate_target_merging_start_docker(
                    v_corridor_lane_center_x=v_corridor_lane.lane_center_x.x,
                    source_row_center_y=source_row_center_y,
                    target_row_center_y=target_row_center_y,
                )

                association_docker.append(target_merging_start_docker)
                v_corridor_lane.add_used_docker(target_merging_start_docker)

                # End of merging docker
                target_merging_end_docker = Coordinates(
                    x=v_corridor_lane.lane_right_docker_anchor.x, y=target_row_center_y
                )
                association_docker.append(target_merging_end_docker)
                v_corridor_lane.add_used_docker(target_merging_end_docker)

            else:
                # Right angle merging docker
                angled_merging_docker = Coordinates(x=v_corridor_lane.lane_center_x.x, y=target_row_center_y)

                association_docker.append(angled_merging_docker)
                v_corridor_lane.add_used_docker(angled_merging_docker)

        forge_logger.debug(f"Dockers for next column connection {con}: {association_docker}")

    def __generate_dockers_for_east_bound_connections(
        self,
        con: PortConnection,
        source_vertical_corridor_lane: VerticalCorridorLane,
        target_horizontal_corridor_lane: HorizontalCorridorLane,
        target_vertical_corridor_lane: VerticalCorridorLane,
    ):
        """
        Generates dockers for multi-column east-bound connections.
        These connections require vertical and horizontal corridor lanes.

        Args:
            con: PortConnection being processed
            source_vertical_corridor_lane: Source vertical corridor lane
            target_horizontal_corridor_lane: Target horizontal corridor lane
            target_vertical_corridor_lane: Target vertical corridor lane
        """

        association_docker: list[Coordinates] = con.association.dockers

        source_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_y
        target_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_y

        source_multiple_outgoing = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.source].east_port_connections) > 1
        )
        target_multiple_incoming = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.target].west_port_connections) > 1
        )

        if source_multiple_outgoing or FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
            # Start of branching docker
            source_branching_start_docker = Coordinates(
                x=source_vertical_corridor_lane.lane_left_docker_anchor.x, y=source_row_center_y
            )

            association_docker.append(source_branching_start_docker)
            source_vertical_corridor_lane.add_used_docker(source_branching_start_docker)

            # End of branching docker
            source_branching_end_docker = CC.calculate_source_branching_end_docker(
                v_corridor_lane_center_x=source_vertical_corridor_lane.lane_center_x.x,
                source_row_center_y=source_row_center_y,
                target_row_center_y=target_row_center_y,
            )

            association_docker.append(source_branching_end_docker)
            source_vertical_corridor_lane.add_used_docker(source_branching_end_docker)

        else:
            # Right angle branching docker
            angled_branching_docker = Coordinates(
                x=source_vertical_corridor_lane.lane_center_x.x, y=source_row_center_y
            )

            association_docker.append(angled_branching_docker)
            source_vertical_corridor_lane.add_used_docker(angled_branching_docker)

        # From source col to target hor. lane cross section
        source_cross_section_h_lane_docker = Coordinates(
            x=source_vertical_corridor_lane.lane_center_x.x, y=target_horizontal_corridor_lane.lane_center_y.y
        )

        con.possible_label_y_positions.append(source_cross_section_h_lane_docker.y)

        association_docker.append(source_cross_section_h_lane_docker)
        source_vertical_corridor_lane.add_used_docker(source_cross_section_h_lane_docker)
        target_horizontal_corridor_lane.add_used_docker(source_cross_section_h_lane_docker)

        # From hor. lane to target col - 1 cross section
        target_cross_section_v_lane_docker = Coordinates(
            x=target_vertical_corridor_lane.lane_center_x.x, y=target_horizontal_corridor_lane.lane_center_y.y
        )

        association_docker.append(target_cross_section_v_lane_docker)
        target_horizontal_corridor_lane.add_used_docker(target_cross_section_v_lane_docker)
        target_vertical_corridor_lane.add_used_docker(target_cross_section_v_lane_docker)

        if target_multiple_incoming or FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
            # Start of merging docker
            target_merging_start_docker = CC.calculate_target_merging_start_docker(
                v_corridor_lane_center_x=target_vertical_corridor_lane.lane_center_x.x,
                source_row_center_y=source_row_center_y,
                target_row_center_y=target_row_center_y,
                is_top_over_connection=con.relative_position_to_source == CD.EAST
                and self.global_grid_lookup.is_a_node_in_between_on_row(source=con.source, target=con.target),
            )

            association_docker.append(target_merging_start_docker)
            target_vertical_corridor_lane.add_used_docker(target_merging_start_docker)

            # End of merging docker
            target_merging_end_docker = Coordinates(
                x=target_vertical_corridor_lane.lane_right_docker_anchor.x, y=target_row_center_y
            )

            association_docker.append(target_merging_end_docker)
            target_vertical_corridor_lane.add_used_docker(target_merging_end_docker)

        else:
            # Right angle merging docker
            angled_merging_docker = Coordinates(x=target_vertical_corridor_lane.lane_center_x.x, y=target_row_center_y)

            association_docker.append(angled_merging_docker)
            target_vertical_corridor_lane.add_used_docker(angled_merging_docker)

        forge_logger.debug(f"Dockers for east-bound connection {con}: {association_docker}")

    def __layout_north_port_connection_dockers(self, con: PortConnection):
        """Calculates dockers for north-bound port connections.

        Args:
            con: North-bound PortConnection to process
        """

        source_row: int = self.global_grid_lookup.get_row(resource_id=con.source)
        source_col: int = self.global_grid_lookup.get_col(resource_id=con.source)

        target_row: int = self.global_grid_lookup.get_row(resource_id=con.target)
        target_col: int = self.global_grid_lookup.get_col(resource_id=con.target)

        forge_logger.debug(f"Calculating dockers for NORTH connection: {con}")

        source_horizontal_corridor: HorizontalCorridor = self.flow_corridor_manager.horizontal_corridors_by_row[
            source_row - 1
        ]
        target_vertical_corridor: VerticalCorridor = self.flow_corridor_manager.vertical_corridors_by_col[
            target_col - 1
        ]

        source_horizontal_corridor_lane = source_horizontal_corridor.get_available_horizontal_corridor_lane(
            source_col=source_col, target_col=target_col - 1, add_where=HorizontalCorridor.ADD_WHERE.LAST_BOTTOM
        )

        target_vertical_corridor_lane = target_vertical_corridor.get_available_vertical_corridor_lane(
            busy_source_row=source_row - 1,
            busy_target_row=target_row,
            original_source_row=source_row,
            original_target_row=target_row,
            perspective=BUSY_SECTION_PERSPECTIVE.TARGET,
            add_where=VerticalCorridor.ADD_WHERE.LAST_RIGHT,
        )

        con.append_used_lanes(used_lanes=[source_horizontal_corridor_lane, target_vertical_corridor_lane])

        self.__generate_dockers_for_north_bound_connection(
            con=con,
            source_horizontal_corridor_lane=source_horizontal_corridor_lane,
            target_vertical_corridor_lane=target_vertical_corridor_lane,
        )

    def __generate_dockers_for_north_bound_connection(
        self,
        con: PortConnection,
        source_horizontal_corridor_lane: HorizontalCorridorLane,
        target_vertical_corridor_lane: VerticalCorridorLane,
    ):
        """Generates dockers for north-bound connections.

        Args:
            con: PortConnection being processed
            source_horizontal_corridor_lane: Source horizontal corridor lane
            target_vertical_corridor_lane: Target vertical corridor lane
        """

        source_row_center_x = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_x
        target_row_center_x = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_x

        source_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_y
        target_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_y

        multiple_outgoing_connections = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.source].north_port_connections) > 1
        )
        multiple_incoming_connections = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.target].west_port_connections) > 1
        )

        association_docker: list[Coordinates] = con.association.dockers

        if multiple_outgoing_connections or FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
            # Start branching docker
            start_branching_docker = Coordinates(
                x=source_row_center_x, y=source_horizontal_corridor_lane.lane_bottom_docker_anchor.y
            )

            association_docker.append(start_branching_docker)
            source_horizontal_corridor_lane.add_used_docker(start_branching_docker)

            # End branching docker
            end_branching_docker = CC.calculate_source_branching_end_docker_upwards(
                source_row_center_x=source_row_center_x,
                h_corridor_lane_center_y=source_horizontal_corridor_lane.lane_center_y.y,
            )

            association_docker.append(end_branching_docker)
            source_horizontal_corridor_lane.add_used_docker(end_branching_docker)

        else:
            # Right angle branching docker
            angled_branching_docker = Coordinates(
                x=source_row_center_x, y=source_horizontal_corridor_lane.lane_center_y.y
            )

            association_docker.append(angled_branching_docker)
            source_horizontal_corridor_lane.add_used_docker(angled_branching_docker)

        # From source row to target vertical lane cross section
        source_cross_section_v_lane_docker = Coordinates(
            x=target_vertical_corridor_lane.lane_center_x.x, y=source_horizontal_corridor_lane.lane_center_y.y
        )

        association_docker.append(source_cross_section_v_lane_docker)
        source_horizontal_corridor_lane.add_used_docker(source_cross_section_v_lane_docker)
        target_vertical_corridor_lane.add_used_docker(source_cross_section_v_lane_docker)

        if multiple_incoming_connections or FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
            # Start merging docker
            start_merging_docker = CC.calculate_target_merging_start_docker(
                v_corridor_lane_center_x=target_vertical_corridor_lane.lane_center_x.x,
                source_row_center_y=source_row_center_y,
                target_row_center_y=target_row_center_y,
            )

            association_docker.append(start_merging_docker)
            target_vertical_corridor_lane.add_used_docker(start_merging_docker)

            # End merging docker
            end_merging_docker = Coordinates(
                x=target_vertical_corridor_lane.lane_right_docker_anchor.x, y=target_row_center_y
            )

            association_docker.append(end_merging_docker)
            target_vertical_corridor_lane.add_used_docker(end_merging_docker)

        else:
            # Right angle merging docker
            angled_merging_docker = Coordinates(x=target_vertical_corridor_lane.lane_center_x.x, y=target_row_center_y)

            association_docker.append(angled_merging_docker)
            target_vertical_corridor_lane.add_used_docker(angled_merging_docker)

    def __layout_south_port_connection_dockers(self, con: PortConnection):
        """Calculates dockers for south-bound port connections.

        Args:
            con: South-bound PortConnection to process
        """

        source_row: int = self.global_grid_lookup.get_row(resource_id=con.source)
        source_col: int = self.global_grid_lookup.get_col(resource_id=con.source)

        target_row: int = self.global_grid_lookup.get_row(resource_id=con.target)
        target_col: int = self.global_grid_lookup.get_col(resource_id=con.target)

        forge_logger.debug(f"Calculating dockers for SOUTH connection: {con}")

        source_horizontal_corridor: HorizontalCorridor = self.flow_corridor_manager.horizontal_corridors_by_row[
            source_row
        ]
        target_vertical_corridor: VerticalCorridor = self.flow_corridor_manager.vertical_corridors_by_col[
            target_col - 1
        ]

        source_horizontal_corridor_lane = source_horizontal_corridor.get_available_horizontal_corridor_lane(
            source_col=source_col, target_col=target_col, add_where=HorizontalCorridor.ADD_WHERE.FIRST_TOP
        )

        target_vertical_corridor_lane = target_vertical_corridor.get_available_vertical_corridor_lane(
            busy_source_row=source_row,
            busy_target_row=target_row,
            original_source_row=source_row,
            original_target_row=target_row,
            perspective=BUSY_SECTION_PERSPECTIVE.TARGET,
            add_where=VerticalCorridor.ADD_WHERE.LAST_RIGHT,
        )

        con.append_used_lanes(used_lanes=[source_horizontal_corridor_lane, target_vertical_corridor_lane])

        self.__generate_dockers_for_south_bound_connection(
            con=con,
            source_horizontal_corridor_lane=source_horizontal_corridor_lane,
            target_vertical_corridor_lane=target_vertical_corridor_lane,
        )

    def __generate_dockers_for_south_bound_connection(
        self,
        con: PortConnection,
        source_horizontal_corridor_lane: HorizontalCorridorLane,
        target_vertical_corridor_lane: VerticalCorridorLane,
    ):
        """Generates dockers for south-bound connections.

        Args:
            con: PortConnection being processed
            source_horizontal_corridor_lane: Source horizontal corridor lane
            target_vertical_corridor_lane: Target vertical corridor lane
        """

        source_row_center_x = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_x
        target_row_center_x = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_x

        source_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_y
        target_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_y

        multiple_outgoing_connections = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.source].south_port_connections) > 1
        )
        multiple_incoming_connections = (
            len(self.shape_resource_id_to_port_adapter_mapping[con.target].west_port_connections) > 1
        )

        association_docker: list[Coordinates] = con.association.dockers

        if multiple_outgoing_connections or FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
            # Start branching docker
            start_branching_docker = Coordinates(
                x=source_row_center_x, y=source_horizontal_corridor_lane.lane_top_docker_anchor.y
            )

            association_docker.append(start_branching_docker)
            source_horizontal_corridor_lane.add_used_docker(start_branching_docker)

            # End branching docker
            end_branching_docker = CC.calculate_source_branching_end_docker_downwards(
                source_row_center_x=source_row_center_x,
                h_corridor_lane_center_y=source_horizontal_corridor_lane.lane_center_y.y,
            )

            association_docker.append(end_branching_docker)
            source_horizontal_corridor_lane.add_used_docker(end_branching_docker)

        else:
            # Right angle branching docker
            angled_branching_docker = Coordinates(
                x=source_row_center_x, y=source_horizontal_corridor_lane.lane_center_y.y
            )

            association_docker.append(angled_branching_docker)
            source_horizontal_corridor_lane.add_used_docker(angled_branching_docker)

        # From source row to target vertical lane cross section
        source_cross_section_v_lane_docker = Coordinates(
            x=target_vertical_corridor_lane.lane_center_x.x, y=source_horizontal_corridor_lane.lane_center_y.y
        )

        association_docker.append(source_cross_section_v_lane_docker)
        source_horizontal_corridor_lane.add_used_docker(source_cross_section_v_lane_docker)
        target_vertical_corridor_lane.add_used_docker(source_cross_section_v_lane_docker)

        if multiple_incoming_connections or FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
            # Start merging docker
            start_merging_docker = CC.calculate_target_merging_start_docker(
                v_corridor_lane_center_x=target_vertical_corridor_lane.lane_center_x.x,
                source_row_center_y=source_row_center_y,
                target_row_center_y=target_row_center_y,
            )

            association_docker.append(start_merging_docker)
            target_vertical_corridor_lane.add_used_docker(start_merging_docker)

            # End merging docker
            end_merging_docker = Coordinates(
                x=target_vertical_corridor_lane.lane_right_docker_anchor.x, y=target_row_center_y
            )

            association_docker.append(end_merging_docker)
            target_vertical_corridor_lane.add_used_docker(end_merging_docker)

        else:
            # Right angle merging docker
            angled_merging_docker = Coordinates(x=target_vertical_corridor_lane.lane_center_x.x, y=target_row_center_y)

            association_docker.append(angled_merging_docker)
            target_vertical_corridor_lane.add_used_docker(angled_merging_docker)

    def __layout_special_port_connection_dockers(self, con: PortConnection):
        source_row = self.global_grid_lookup.get_occupied_row_for_inc_collapsed_pool_con_or_con_between_pools(
            source=con.source,
            target=con.target,
            both_pools=True if con.relative_position_to_source == CD.SOURCE_AND_TARGET_COLLAPSED_POOLS else False,
        )

        target_row: int = self.global_grid_lookup.get_row(resource_id=con.target)
        target_col: int = self.global_grid_lookup.get_col(resource_id=con.target)

        source_col = target_col - 1

        forge_logger.debug(f"Calculating dockers for SPECIAL connection: {con}")

        vertical_corridor: VerticalCorridor = self.flow_corridor_manager.vertical_corridors_by_col[source_col]

        vertical_corridor_lane = vertical_corridor.get_available_vertical_corridor_lane(
            busy_source_row=source_row,
            busy_target_row=target_row,
            original_source_row=source_row,
            original_target_row=target_row,
            perspective=BUSY_SECTION_PERSPECTIVE.TARGET,
            add_where=VerticalCorridor.ADD_WHERE.FIRST_LEFT,
        )

        con.append_used_lanes(used_lanes=vertical_corridor_lane)

        # Skip docker generation since only shape dockers are required, save x coordinate for alignment
        if con.relative_position_to_source == CD.SOURCE_AND_TARGET_COLLAPSED_POOLS:
            con.association.dockers = [
                Coordinates(x=vertical_corridor_lane.lane_center_x.x, y=0),
            ]
            return

        self.__generate_dockers_for_special_port_connection(
            con=con,
            v_corridor_lane=vertical_corridor_lane,
        )

    def __generate_dockers_for_special_port_connection(
        self,
        con: PortConnection,
        v_corridor_lane: VerticalCorridorLane,
    ):
        """
        Generates dockers for special port connections.

        Args:
            con: PortConnection being processed
            vertical_corridor_lane: Vertical corridor lane used for this connection
        """
        association_docker: list[Coordinates] = con.association.dockers

        source_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.source].global_center_y
        target_row_center_y = self.coordinates_handler.shape_coords_record_by_resource_id[con.target].global_center_y

        if FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS:
            # Start of merging docker
            target_merging_start_docker = CC.calculate_target_merging_start_docker(
                v_corridor_lane_center_x=v_corridor_lane.lane_center_x.x,
                source_row_center_y=source_row_center_y,
                target_row_center_y=target_row_center_y,
            )

            association_docker.append(target_merging_start_docker)
            v_corridor_lane.add_used_docker(target_merging_start_docker)

            # End of merging docker
            target_merging_end_docker = Coordinates(x=v_corridor_lane.lane_right_docker_anchor.x, y=target_row_center_y)
            association_docker.append(target_merging_end_docker)
            v_corridor_lane.add_used_docker(target_merging_end_docker)

        else:
            # Right angle merging docker
            angled_merging_docker = Coordinates(x=v_corridor_lane.lane_center_x.x, y=target_row_center_y)

            association_docker.append(angled_merging_docker)
            v_corridor_lane.add_used_docker(angled_merging_docker)
