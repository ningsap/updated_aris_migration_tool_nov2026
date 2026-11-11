from typing import Dict, List, Literal, Union

from networkx import MultiDiGraph

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.conversion.model_converter import ModelConverter
from diagramforge.rendering.json_builder import JsonBuilder
from diagramforge.schema.shapes import Diagram, ShapeBase
from diagramforge.SETUP import forge_logger
from diagramforge.transformation.column_positioner import ColumnPositioner
from diagramforge.transformation.container_layout_manager import ContainerLayoutManager
from diagramforge.transformation.preparation_tool import PreparationTool
from diagramforge.transformation.row_positioner import RowPositioner


class DiagramForge:
    """
    A class for converting Signavio JSON diagrams or Diagram models into a fully
    positioned diagram and exporting it as SPM-compatible JSON.

    Attributes:
        model_converter (ModelConverter): Converts JSON or model to a Diagram object.
        diagram (Diagram): Validated diagram model.
        source_graph (MultiDiGraph): Internal graph representation of the diagram.
        resource_id_to_shape_mapping (Dict[str, ShapeBase]): Maps resource IDs to shape objects.
        node_resource_id_to_parent_mapping (Dict[str, Dict[str, ShapeBase]]): Maps node IDs to their parent.
        bpmn_adjusted_columns (Dict[int, List[str]]): Column positions assigned to nodes.
        lane_positions_by_pool (Dict[str, List[str]]): Container positioning data grouped by Pool.
        lane_positions_by_lane (Dict[str, List[str]]): Container positioning data grouped by Lane.
        pool_order ( Dict[int, str]): Priority data for ordering Pool placement.
    """

    def __init__(self, json_or_model: Union[dict, Diagram]) -> None:
        """
        Initializes the DiagramForge by converting and validating the input data.

        Args:
            json_or_model (Union[dict, Diagram]): Input data as JSON or Diagram model.
        """

        if not FORGE_CONFIG.LOG_DEBUG:
            forge_logger.disable_level("DEBUG")

        self.model_converter = ModelConverter()
        self.diagram = self.model_converter.convert_and_validate_json_or_model(json_or_model)

        # Cross-methodical class instance variables in order of usage
        self.source_graph: MultiDiGraph = None
        self.resource_id_to_shape_mapping: Dict[str, ShapeBase] = None
        self.node_resource_id_to_parent_mapping: Dict[str, Dict[str, ShapeBase]] = None
        self.bpmn_adjusted_columns: Dict[int, List[str]] = None
        self.lane_positions_by_pool: Dict[str, List[str]] = None
        self.lane_positions_by_lane: Dict[str, List[str]] = None
        self.pool_order: Dict[int, str] = None
        self.bpmn_adjusted_grid: Dict[str, Dict[str, Dict[Literal["col", "row"], int]]] = None

    def to_spm_json(self) -> dict:
        """
        Executes the entire forging process and returns the final SPM-compatible JSON.

        Returns:
            dict: The finalized diagram data in JSON format.
        """
        self.__prepare_data()
        self.__position_nodes_in_columns()
        self.__determine_container_priority()
        self.__position_nodes_in_rows()
        model = self.__render_diagram_json()
        return model

    def __prepare_data(self):
        """
        Builds the graph and creates resource mappings for the diagram.

        Returns:
            None
        """
        preparation_tool = PreparationTool(self.diagram)
        self.source_graph = preparation_tool.build_graph()
        self.resource_id_to_shape_mapping = preparation_tool.create_resource_id_to_shape_mapping()
        self.node_resource_id_to_parent_mapping = preparation_tool.create_node_resource_id_to_parent_mapping()
        forge_logger.success("Preparations complete.")

    def __position_nodes_in_columns(self):
        """
        Positions nodes into columns using a BFS-based approach.

        Returns:
            None
        """
        column_positioner = ColumnPositioner(graph=self.source_graph)
        self.bpmn_adjusted_columns = column_positioner.position_columns()
        forge_logger.success("Column positioning complete.")

    def __determine_container_priority(self):
        """
        Determines the order and arrangement of Pools and Lanes.

        Returns:
            None
        """
        container_positioner = ContainerLayoutManager(
            graph=self.source_graph,
            resource_id_to_shape_mapping=self.resource_id_to_shape_mapping,
            node_resource_id_to_parent_mapping=self.node_resource_id_to_parent_mapping,
        )
        self.container_positioner = container_positioner
        self.pool_order = container_positioner.determine_pool_order()
        self.lane_positions_by_pool = container_positioner.determine_lane_positions_by_pool()
        self.lane_positions_by_lane = container_positioner.determine_nested_lane_positions()
        forge_logger.success("Container positioning complete.")

    def __position_nodes_in_rows(self):
        """
        Assigns row positions to nodes, respecting container priorities.

        Returns:
            None
        """
        row_positioner = RowPositioner(
            graph=self.source_graph,
            bpmn_adjusted_columns=self.bpmn_adjusted_columns,
            pool_order_dict=self.pool_order,
            lane_positions_by_pool=self.lane_positions_by_pool,
            lane_positions_by_lane=self.lane_positions_by_lane,
            node_resource_id_to_parent_mapping=self.node_resource_id_to_parent_mapping,
        )
        self.bpmn_adjusted_grid = row_positioner.position_rows()

    def __render_diagram_json(self):
        """
        Builds the final SPM-compatible JSON for the diagram.

        Returns:
            dict: Converted diagram data in JSON format.
        """
        json_builder = JsonBuilder(
            source_graph=self.source_graph,
            diagram=self.diagram,
            bpmn_adjusted_grid=self.bpmn_adjusted_grid,
            pool_order=self.pool_order,
            resource_id_to_shape_mapping=self.resource_id_to_shape_mapping,
            lane_positions_by_pool=self.lane_positions_by_pool,
            lane_positions_by_lane=self.lane_positions_by_lane,
            node_resource_id_to_parent_mapping=self.node_resource_id_to_parent_mapping,
        )
        self.diagram_json = json_builder.build_json()
        forge_logger.success("Diagram JSON rendering complete.")

        model_converter = ModelConverter()
        return model_converter.convert_to_json(self.diagram_json)
