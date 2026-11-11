from typing import Dict, List, Literal

from networkx import MultiDiGraph

from diagramforge.helpers.general import wrap_text
from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.container_positioning_manager import ContainerPositioningManager
from diagramforge.rendering.coordinates_handler import CoordinatesHandler
from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup
from diagramforge.rendering.flows.label_placer import LabelPlacer
from diagramforge.rendering.flows.sequence_flow_manager import SequenceFlowManager
from diagramforge.rendering.node_positioning_manager import NodePositioningManager
from diagramforge.schema.base import Bounds, Coordinates, ShapeBase
from diagramforge.schema.shapes import Association, CollapsedPool, Diagram, Event, Gateway, Pool, Task
from diagramforge.SETUP import forge_logger


class JsonBuilder:
    """Builds and manages the JSON representation of a BPMN diagram.

    Attributes:
        source_graph (MultiDiGraph): The source graph containing the BPMN elements.
        diagram (Diagram): The Diagram object to be modified.
        bpmn_adjusted_grid (Dict[str, Dict[str, Dict[Literal["col", "row"], int]]]): Adjusted grid data for BPMN rendering.
        resource_id_to_shape_mapping (Dict[str, ShapeBase]): Maps resource IDs to shape objects.
        lane_positions_by_pool (Dict[str, List[str]]): Lane positions grouped by pool.
        lane_positions_by_lane (Dict[str, List[str]]): Lane positions grouped by lane.
        node_resource_id_to_parent_mapping (Dict[str, Dict[str, ShapeBase]]): Mapping of node resource IDs to their parents.
        positioned_nodes_by_lane (dict or None): Nodes positioned by lane.
        global_grid_lookup (GlobalGridLookup or None): Grid lookup utility.
        coordinates_handler (CoordinatesHandler or None): Coordinates handler for reverting global coords.
    """

    def __init__(
        self,
        source_graph: MultiDiGraph,
        diagram: Diagram,
        bpmn_adjusted_grid: Dict[str, Dict[str, Dict[Literal["col", "row"], int]]],
        resource_id_to_shape_mapping: Dict[str, ShapeBase],
        pool_order: Dict[int, str],
        lane_positions_by_pool: Dict[str, List[str]],
        lane_positions_by_lane: Dict[str, List[str]],
        node_resource_id_to_parent_mapping: Dict[str, Dict[str, ShapeBase]],
    ) -> None:
        """Initializes the JsonBuilder with all required mapping data.

        Args:
            source_graph (MultiDiGraph): The source BPMN graph.
            diagram (Diagram): The diagram object to be updated.
            bpmn_adjusted_grid (Dict[str, Dict[str, Dict[Literal["col", "row"], int]]]): Adjusted grid data for node positioning.
            resource_id_to_shape_mapping (Dict[str, ShapeBase]): Maps resource IDs to shape instances.
            lane_positions_by_pool (Dict[str, List[str]]): Lane positioning information by pool.
            lane_positions_by_lane (Dict[str, List[str]]): Lane positioning information by lane.
            node_resource_id_to_parent_mapping (Dict[str, Dict[str, ShapeBase]]): Parent-child relationships of node resource IDs.
        """

        self.source_graph = source_graph
        self.diagram = diagram
        self.bpmn_adjusted_grid: dict = bpmn_adjusted_grid
        self.pool_order: dict = pool_order
        self.resource_id_to_shape_mapping: dict = resource_id_to_shape_mapping
        self.lane_positions_by_pool: dict = lane_positions_by_pool
        self.lane_positions_by_lane: dict = lane_positions_by_lane
        self.node_resource_id_to_parent_mapping: dict = node_resource_id_to_parent_mapping

        # Cross-methodical class instance variables in order of usage
        self.positioned_nodes_by_lane = None
        self.global_grid_lookup: GlobalGridLookup = None
        self.coordinates_handler: CoordinatesHandler = None

    def build_json(self):
        """Builds the JSON representation of the diagram by removing dockers, placing nodes, managing flows, and restoring local coords.

        Returns:
            Diagram: The updated diagram with properly placed shapes and flows.
        """

        self.__cleanup_dockers_and_bounds(self.diagram.child_shapes)
        self.__place_nodes_in_lanes()
        self.__place_containers()
        self.__create_global_coords()
        self.__manage_sequence_flows()
        self.coordinates_handler.revert_global_to_local_coords()
        self.__add_shape_docker()
        self.__wrap_in_diagram_displayed_texts()
        return self.diagram

    def __place_nodes_in_lanes(self):
        """Places nodes within their respective lanes using NodePositioningManager."""

        node_positioning_manager = NodePositioningManager(
            bpmn_adjusted_grid=self.bpmn_adjusted_grid,
            resource_id_to_shape_mapping=self.resource_id_to_shape_mapping,
            node_resource_id_to_parent_mapping=self.node_resource_id_to_parent_mapping,
        )
        self.positioned_nodes_by_lane = node_positioning_manager.position_nodes_into_lanes()

    def __place_containers(self):
        """Positions container elements (lanes, pools) on the diagram using ContainerPositioningManager."""

        container_positioning_manager = ContainerPositioningManager(
            diagram=self.diagram,
            resource_id_to_shape_mapping=self.resource_id_to_shape_mapping,
            pool_order_dict=self.pool_order,
            node_resource_id_to_parent_mapping=self.node_resource_id_to_parent_mapping,
            lane_positions_by_pool=self.lane_positions_by_pool,
            lane_positions_by_lane=self.lane_positions_by_lane,
            positioned_nodes_by_lane=self.positioned_nodes_by_lane,
        )
        container_positioning_manager.position_containers()

    def __cleanup_dockers_and_bounds(self, children: list[ShapeBase]):
        """Removes dockers and bounds from the given list of shapes recursively.

        Args:
            children (list[ShapeBase]): List of child shapes to clean up.
        """

        for s in children:
            s.dockers = []
            if s.child_shapes:
                self.__cleanup_dockers_and_bounds(s.child_shapes)

    def __add_shape_docker(self):
        """
        Adds shape dockers to source and target shapes for each edge in the source graph.
        Each shape must contain dockers as part of its bounds list at the start and end (index 0 and -1) that
        correspond to the center of the shape. In other words, the shape height/2 and width/2 as x and y coordinates.
        """

        processed_association_ids = set()

        for source_node_id, target_node_id in self.source_graph.edges():
            source_shape: ShapeBase = self.resource_id_to_shape_mapping[source_node_id]
            target_shape: ShapeBase = self.resource_id_to_shape_mapping[target_node_id]

            respective_association = None
            for association_target in source_shape.outgoing:
                if association_target.resource_id not in self.resource_id_to_shape_mapping.keys():
                    continue

                respective_association: Association = self.resource_id_to_shape_mapping[association_target.resource_id]
                if respective_association.target.resource_id != target_node_id:
                    continue

                source_shape_width = source_shape.bounds.lowerRight.x - source_shape.bounds.upperLeft.x
                source_shape_height = source_shape.bounds.lowerRight.y - source_shape.bounds.upperLeft.y
                target_shape_width = target_shape.bounds.lowerRight.x - target_shape.bounds.upperLeft.x
                target_shape_height = target_shape.bounds.lowerRight.y - target_shape.bounds.upperLeft.y

                if respective_association.resource_id in processed_association_ids:
                    forge_logger.warning(f"Association {respective_association.resource_id} already done.")
                    continue

                # FIX: Skip adding dockers for collapsed pools to collapsed pools
                if isinstance(source_shape, (CollapsedPool, Pool)) and isinstance(target_shape, (CollapsedPool, Pool)):
                    first_docker = respective_association.dockers[0]

                    source_docker = Coordinates(
                        x=first_docker.x - SC.POOL_LEFT_CANVAS_SPACER,
                        y=SC.COLLAPSED_POOL_HEIGHT / 2,
                    )

                    target_docker = Coordinates(
                        x=first_docker.x - SC.POOL_LEFT_CANVAS_SPACER,
                        y=SC.COLLAPSED_POOL_HEIGHT / 2,
                    )

                    respective_association.dockers = [source_docker, target_docker]

                    forge_logger.debug(
                        f"Assigned special shape dockers to association {respective_association.resource_id} "
                        f"from outgoings of {source_shape.resource_id} to target {target_shape.resource_id} "
                        f"as both are CollapsedPools."
                    )
                    continue

                if isinstance(source_shape, (CollapsedPool, Pool)):
                    first_docker = respective_association.dockers[0]
                    source_docker = Coordinates(
                        x=first_docker.x - SC.POOL_LEFT_CANVAS_SPACER,
                        y=SC.COLLAPSED_POOL_HEIGHT / 2,
                    )
                    respective_association.dockers.insert(0, source_docker)
                else:
                    source_docker = Coordinates(x=source_shape_width / 2, y=source_shape_height / 2)
                    respective_association.dockers.insert(0, source_docker)

                if isinstance(target_shape, (CollapsedPool, Pool)):
                    last_docker = respective_association.dockers[-1]
                    target_docker = Coordinates(
                        x=last_docker.x - SC.POOL_LEFT_CANVAS_SPACER,
                        y=SC.COLLAPSED_POOL_HEIGHT / 2,
                    )
                    respective_association.dockers.append(target_docker)
                else:
                    target_docker = Coordinates(x=target_shape_width / 2, y=target_shape_height / 2)
                    respective_association.dockers.append(target_docker)

                processed_association_ids.add(respective_association.resource_id)
                forge_logger.debug(
                    f"Added shape dockers to association {respective_association.resource_id} "
                    f"from outgoings of {source_shape.resource_id}"
                )

    def __create_global_coords(self):
        """Creates global coordinates for shapes using GlobalGridLookup and initializes CoordinatesHandler."""

        self.global_grid_lookup = GlobalGridLookup(
            bpmn_adjusted_grid=self.bpmn_adjusted_grid,
            pool_order=self.pool_order,
            lane_positions_by_pool=self.lane_positions_by_pool,
            lane_positions_by_lane=self.lane_positions_by_lane,
            resource_id_to_shape_mapping=self.resource_id_to_shape_mapping,
            node_resource_id_to_parent_mapping=self.node_resource_id_to_parent_mapping,
        )
        self.coordinates_handler = CoordinatesHandler(
            diagram=self.diagram,
            resource_id_to_shape_mapping=self.resource_id_to_shape_mapping,
        )

    def __manage_sequence_flows(self):
        """Manages sequence flows, calculates dockers, and places labels using SequenceFlowManager and LabelPlacer."""

        sequence_flow_manager = SequenceFlowManager(
            source_graph=self.source_graph,
            diagram=self.diagram,
            resource_id_to_shape_mapping=self.resource_id_to_shape_mapping,
            global_grid_lookup=self.global_grid_lookup,
            coordinates_handler=self.coordinates_handler,
            node_resource_id_to_parent_mapping=self.node_resource_id_to_parent_mapping,
        )
        sequence_flow_manager.build_port_adapter_mapping()
        sequence_flow_manager.build_flow_corridors()
        sequence_flow_manager.calculate_dockers()

        label_placer = LabelPlacer(
            coordinates_handler=self.coordinates_handler,
            association_resource_id_to_port_connection_mapping=sequence_flow_manager.association_resource_id_to_port_connection_mapping,
            flow_corridor_manager=sequence_flow_manager.flow_corridor_manager,
            shape_resource_id_to_port_adapter_mapping=sequence_flow_manager.shape_resource_id_to_port_adapter_mapping,
            global_grid_lookup=self.global_grid_lookup,
            resource_id_to_shape_mapping=self.resource_id_to_shape_mapping,
        )
        label_placer.place_sequence_flow_labels()
        label_placer.place_gateway_labels()

        # Append association bounds after label placement to ensure correct positioning
        sequence_flow_manager.append_bounds()

    def __wrap_in_diagram_displayed_texts(self):
        """Wraps relevant texts in the diagram to fit within specified width."""

        for shape in self.resource_id_to_shape_mapping.values():
            if not isinstance(shape, (Association, Event, Task, Gateway)):
                continue

            for prop_name, prop_value in shape.properties:
                if prop_name.startswith("name") and prop_value:
                    wrapped_text = wrap_text(prop_value, max_width_px=150)

                    if not wrapped_text:
                        wrapped_text = prop_value
                        forge_logger.warning(f"Text wrapping failed for {shape.resource_id}: {prop_value}")

                    shape.properties[prop_name] = wrapped_text
                    shape.properties[prop_name] = wrapped_text
