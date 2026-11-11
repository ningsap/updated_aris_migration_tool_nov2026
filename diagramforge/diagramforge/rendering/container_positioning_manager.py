from copy import deepcopy
from typing import Dict, List

from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.rendering.coords_calculator import CoordsCalculator as CC
from diagramforge.schema.base import Bounds, Coordinates, ShapeBase
from diagramforge.schema.shapes import CollapsedPool, Diagram, Lane, Pool
from diagramforge.SETUP import forge_logger


class ContainerPositioningManager:
    """Manages the positioning of container shapes (Pools and Lanes) within a diagram."""

    def __init__(
        self,
        diagram: Diagram,
        resource_id_to_shape_mapping: Dict[str, ShapeBase],
        pool_order_dict: Dict[int, str],
        node_resource_id_to_parent_mapping: Dict[str, Dict[str, ShapeBase]],
        lane_positions_by_pool: Dict[str, List[str]],
        lane_positions_by_lane: Dict[str, List[str]],
        positioned_nodes_by_lane: Dict[str, List[ShapeBase]],
    ) -> None:
        """Initializes a ContainerPositioningManager.

        Args:
            diagram (Diagram): The diagram object to coordinate.
            resource_id_to_shape_mapping (Dict[str, ShapeBase]): Mapping of resource IDs to shapes.
            pool_order (Dict[int, str]): Priority order for Pools based on their index.
            node_resource_id_to_parent_mapping (Dict[str, Dict[str, ShapeBase]]): Mapping of node IDs to parent containers.
            lane_positions_by_pool (Dict[str, List[str]]): Ordered lane structure keyed by Pool IDs.
            lane_positions_by_lane (Dict[str, List[str]]): Ordered lane structure keyed by Lane IDs.
            positioned_nodes_by_lane (Dict[str, List[ShapeBase]]): Node shapes grouped by Lane ID.
        """

        self.diagram = diagram
        self.resource_id_to_shape_mapping = resource_id_to_shape_mapping
        self.pool_order_dict = pool_order_dict
        
        self.pool_order_list = sorted(pool_order_dict, key=pool_order_dict.get)

        self.node_resource_id_to_parent_mapping = node_resource_id_to_parent_mapping
        self.lane_positions_by_pool = lane_positions_by_pool
        self.lane_positions_by_lane = lane_positions_by_lane
        self.positioned_nodes_by_lane = positioned_nodes_by_lane

    def position_containers(self) -> Diagram:
        """Positions Pools and Lanes in the diagram based on previously placed nodes.

        All container shapes rely on the final calculated width for the largest lane so all are stretched to match.

        The lanes height is calculated based on the maximum height of the nodes within it as the positioned nodes
        will not be moved. For nested lanes, the height is calculated based on the maximum height of the nodes
        within the nested lanes.

        After positioning all lanes, pools are placed using the accumulated widths of their lanes.

        Returns:
            Diagram: The updated diagram with correctly positioned container shapes.
        """

        # Calculate lane placement and maximum width first
        pool_max_width: int = 0
        lane_lr_bounds: list[Coordinates] = []
        nested_lane_lr_bounds: list[Coordinates] = []

        for pool_id in self.pool_order_list:
            pool_shape: Pool = self.resource_id_to_shape_mapping[pool_id]

            accumulated_height: int = 0

            pool_bounds: Bounds = pool_shape.bounds
            seen_nested_lanes: set[str] = set()

            ordered_lanes: list[str] = self.lane_positions_by_pool.get(pool_id, [])

            for lane_id in ordered_lanes:
                if lane_id in self.lane_positions_by_lane:
                    nested_lane_accumulated_height: int = 0
                    container_lane_shape: Lane = self.resource_id_to_shape_mapping[lane_id]
                    container_lane_shape.child_shapes = []

                    container_lane_shape.bounds.upperLeft.x = SC.LANE_HEADER
                    container_lane_shape.bounds.upperLeft.y = deepcopy(accumulated_height)

                    for child_lane in self.lane_positions_by_lane[lane_id]:
                        child_lane_shape: Lane = self.resource_id_to_shape_mapping[child_lane]
                        child_lane_shapes: list[ShapeBase] = self.positioned_nodes_by_lane[child_lane]

                        child_lane_max_x = max([shape.bounds.lowerRight.x for shape in child_lane_shapes])
                        child_lane_max_y = max([shape.bounds.lowerRight.y for shape in child_lane_shapes])

                        child_lane_height = CC.calculate_lane_height(lane_max_y=child_lane_max_y)
                        child_lane_width = CC.calculate_lane_width(lane_max_x=child_lane_max_x)

                        pool_max_width = max(pool_max_width, child_lane_width)

                        child_lane_shape.bounds.upperLeft.x = SC.LANE_HEADER
                        child_lane_shape.bounds.upperLeft.y = deepcopy(nested_lane_accumulated_height)

                        nested_lane_accumulated_height += child_lane_height
                        child_lane_shape.bounds.lowerRight.y = deepcopy(nested_lane_accumulated_height)
                        nested_lane_lr_bounds.append(child_lane_shape.bounds.lowerRight)

                        child_lane_shape.child_shapes = child_lane_shapes
                        container_lane_shape.child_shapes.append(child_lane_shape)

                        seen_nested_lanes.add(child_lane)

                        forge_logger.debug(f"Positioned nested lane {child_lane} at {child_lane_shape.bounds}")

                    accumulated_height += nested_lane_accumulated_height
                    container_lane_shape.bounds.lowerRight.y = deepcopy(accumulated_height)
                    lane_lr_bounds.append(container_lane_shape.bounds.lowerRight)

                else:
                    if lane_id in seen_nested_lanes:
                        # Skip lanes that have already been processed as nested lanes
                        continue

                    lane_shape: Lane = self.resource_id_to_shape_mapping[lane_id]
                    lane_children_shapes: list[ShapeBase] = self.positioned_nodes_by_lane[lane_id]

                    lane_max_x = max([shape.bounds.lowerRight.x for shape in lane_children_shapes])
                    lane_max_y = max([shape.bounds.lowerRight.y for shape in lane_children_shapes])

                    lane_height = CC.calculate_lane_height(lane_max_y=lane_max_y)
                    lane_width = CC.calculate_lane_width(lane_max_x=lane_max_x)

                    pool_max_width = max(pool_max_width, lane_width)

                    lane_shape.bounds.upperLeft.x = SC.LANE_HEADER
                    lane_shape.bounds.upperLeft.y = deepcopy(accumulated_height)

                    accumulated_height += lane_height
                    lane_shape.bounds.lowerRight.y = deepcopy(accumulated_height)
                    lane_lr_bounds.append(lane_shape.bounds.lowerRight)

                    lane_shape.child_shapes = lane_children_shapes
                    forge_logger.debug(f"Positioned lane {lane_id} at {lane_shape.bounds}")

            if isinstance(pool_shape, CollapsedPool):
                accumulated_height += SC.COLLAPSED_POOL_HEIGHT

            pool_max_width += (SC.COL_WIDTH / 2) + SC.V_SHAPE_SPACER

            pool_bounds.lowerRight.x = pool_max_width + pool_bounds.upperLeft.x
            pool_bounds.lowerRight.y = accumulated_height + pool_bounds.upperLeft.y

        for lr_x in lane_lr_bounds:
            lr_x.x = deepcopy(pool_max_width)

        for lr_x in nested_lane_lr_bounds:
            lr_x.x = deepcopy(pool_max_width - SC.LANE_HEADER)

        # Position Pools based on lane widths

        accumulated_pools_height: int = 0 + SC.POOL_TOP_CANVAS_SPACER

        for pool_id in self.pool_order_list:
            pool_shape: Pool | CollapsedPool = self.resource_id_to_shape_mapping[pool_id]

            pool_height = pool_shape.bounds.lowerRight.y - pool_shape.bounds.upperLeft.y

            pool_shape.bounds.upperLeft.x = SC.POOL_LEFT_CANVAS_SPACER
            pool_shape.bounds.upperLeft.y = accumulated_pools_height

            pool_shape.bounds.lowerRight.x = pool_shape.bounds.upperLeft.x + pool_max_width
            pool_shape.bounds.lowerRight.y = pool_shape.bounds.upperLeft.y + pool_height

            accumulated_pools_height += pool_height + SC.SPACER_BETWEEN_POOLS

        return self.diagram
