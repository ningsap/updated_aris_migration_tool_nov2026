from collections import defaultdict
from typing import Dict, List, Literal

from diagramforge.rendering.coords_calculator import CoordsCalculator as CoordsCalc
from diagramforge.rendering.render_helpers import get_width_height_by_stencil
from diagramforge.schema.base import Bounds, ShapeBase
from diagramforge.SETUP import forge_logger


class NodePositioningManager:
    """
    This class is responsible for placing nodes in their designated lanes. It receives the BPMN-adjusted grid and
    resource ID to node mapping as input and return all lanes with their nodes placed at the correct positions
    as well as stores the node positions as a list for easy access in the future.
    """

    def __init__(
        self,
        bpmn_adjusted_grid: Dict[str, Dict[str, Dict[Literal["col", "row"], int]]],
        resource_id_to_shape_mapping: Dict[str, ShapeBase],
        node_resource_id_to_parent_mapping: Dict[str, Dict[str, ShapeBase]],
    ) -> None:
        self.bpmn_adjusted_grid = bpmn_adjusted_grid
        self.resource_id_to_shape_mapping = resource_id_to_shape_mapping
        self.node_resource_id_to_parent_mapping = node_resource_id_to_parent_mapping

    def position_nodes_into_lanes(self) -> Dict[str, List[ShapeBase]]:
        """
        Positions BPMN nodes into their respective lanes by calculating and updating the
        bounds of each node according to a grid layout.
        This method reads lane-to-node position mappings from the instance attribute
        bpmn_adjusted_grid, determines the center coordinates for each node based on
        its row and column indices, adjusts the bounding box of each shape accordingly,
        and groups the positioned shapes by lane.

        Returns:
            Dict[str, List[ShapeBase]]
                A dictionary keyed by lane identifiers, where each value is a list of
                shape objects whose bounds have been updated based on their computed
                row and column positions.
        """

        positioned_nodes_by_lane = defaultdict(list)

        for lane_id, node_positions in self.bpmn_adjusted_grid.items():
            forge_logger.debug(f"Calculating node positions in lane {lane_id}")

            for node_id, node_position in node_positions.items():
                node_shape: ShapeBase = self.resource_id_to_shape_mapping[node_id]
                shape_bounds: Bounds = node_shape.bounds

                shape_width, shape_height = get_width_height_by_stencil(node_shape.stencil)
                node_col, node_row = node_position["col"], node_position["row"]

                forge_logger.debug(f"Calculating node position for node {node_id} at col {node_col} and row {node_row}")

                shape_center_x = CoordsCalc.calculate_col_mid_x(node_col)
                shape_center_y = CoordsCalc.calculate_row_mid_y(node_row)

                shape_bounds.upperLeft.x = shape_center_x - shape_width / 2
                shape_bounds.upperLeft.y = shape_center_y - shape_height / 2
                shape_bounds.lowerRight.x = shape_center_x + shape_width / 2
                shape_bounds.lowerRight.y = shape_center_y + shape_height / 2

                forge_logger.debug(
                    f"Node {node_id} positioned at X {shape_center_x} Y {shape_center_y} | Bounds: {shape_bounds}"
                )

                positioned_nodes_by_lane[lane_id].append(node_shape)

        return positioned_nodes_by_lane
