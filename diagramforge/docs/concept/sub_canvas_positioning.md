# Assign & Calculate Positions in Sub-canvases

The purpose of these components is to assign and calculate all elements (container elements and non-container elements) in their respective sub-canvases. This process encompasses everything aside from Sequence Flows.

## Table of Contents <!-- omit in toc -->
- [Assigning \& calculating positions of non-container nodes in sub-canvases](#assigning--calculating-positions-of-non-container-nodes-in-sub-canvases)
  - [Used Components](#used-components)
  - [Initialization](#initialization)
  - [Assigning positions of non-container elements](#assigning-positions-of-non-container-elements)
- [Assigning \& calculating positions of container elements](#assigning--calculating-positions-of-container-elements)
  - [Used Components](#used-components-1)
  - [Initialization](#initialization-1)
  - [Assigning positions to container elements](#assigning-positions-to-container-elements)

## Assigning & calculating positions of non-container nodes in sub-canvases

The [`NodePositioningManager`](../../diagramforge/rendering/node_positioning_manager.py) is relatively straightforward. It puts all the non-container nodes in their respective parent lanes and assign their initial positions in that sub-canvas.

### Used Components
- [`CoordsCalculator`](../../diagramforge/rendering/coords_calculator.py): Class with static methods to calculate the coordinates. Mainly created for outsourcing the calculations and keep them in one place.
- [`get_width_height_by_stencil`](../../diagramforge/rendering/render_helpers.py): Helper function to get the width and height of an BPMN element by its stencil.


### Initialization
The `NodePositioningManager` is initialized with:
- `bpmn_adjusted_grid (Dict[str, Dict[str, Dict[Literal["col", "row"], int]]])`: Final node positions stored as `{lane_id: {node: {col: integer, row: integer}}}`.
- `resource_id_to_shape_mapping (Dict[str, ShapeBase])`: Mapping of node IDs to their respective shapes.
- `node_resource_id_to_parent_mapping (Dict[str, ShapeBase])`: Node-to-container relationships.

### Assigning positions of non-container elements
> Method: `position_nodes_into_lanes`

Since this is the only method of this class, inputs are not explicitly mentioned.

##### Outputs <!-- omit in toc -->

- `positioned_nodes_by_lane (Dict[str, List[ShapeBase]])`: Mapping of lane IDs to a list of shapes that are positioned in that lane.
  
---

This method positions all the non-container BPMN elements in their parent lanes starting from the coordinate origin (top-left corner of the lane at 0,0). First, it calculates the center position for each node. Using the center position, it calculates the `upperLeft` X and Y as well as the `lowerRight` X and Y required by SPM to be displayed correctly.

The positioned elements are stored in the `positioned_nodes_by_lane` dictionary and returned to the `JSONBuilder`.

## Assigning & calculating positions of container elements

This component is responsible for assigning and calculating the positions of container elements (Pools and Lanes) in their respective sub-canvases.

### Used Components

- [`CoordsCalculator`](../../diagramforge/rendering/coords_calculator.py): Class with static methods to calculate the coordinates. Mainly created for outsourcing the calculations and keep them in one place.

### Initialization

The [`ContainerPositioningManager`](../../diagramforge/rendering/container_positioning_manager.py) is initialized with:

- `diagram (Diagram)`: The diagram object.
- `resource_id_to_shape_mapping (Dict[str, ShapeBase])`: Mapping of node IDs to their respective shapes.
- `node_resource_id_to_parent_mapping (Dict[str, Dict[str, ShapeBase]])`: Node-to-container relationships.
- `lane_positions_by_pool (Dict[str, List[str]])`: Mapping of pool IDs to a list of lane IDs.
- `lane_positions_by_lane (Dict[str, List[str]])`: Mapping of lane IDs to a list of lane IDs.
- `positioned_nodes_by_lane (Dict[str, List[ShapeBase]])`: Mapping of lane IDs to a list of shapes that are positioned in that lane.

### Assigning positions to container elements
> Method: `position_containers`

Since this is the only method of this class, inputs are not explicitly mentioned.

##### Outputs <!-- omit in toc -->

- `self.diagram`: The diagram object with updated positions of container elements. Both of these components alter the positions of the elements in the respective diagram objects.
  
---

This process is very similar to the one above, but this time only with container elements. However, instead of calculating the center positions and the bounds based off of that, it calculates the bounds based on the parent container's content and the maximum width.

As for the height: For each pool as well as each lane that encompasses (nested) lanes, the height is calculated by summing up the heights of all the lanes. Each lane's height is derived from the largest Y coordinate of its child elements. The top-left corner is the result of keeping track of the current Y position and adding the height of the previous lane.

The width on the other hand, is derived from the largest X coordinate of the child elements for each lane and is updated at the end for all container elements so that each lane and pool has the same width.

With that, the calculation of local positions for all elements is concluded. Every change is applied directly in the `diagram` object that is referenced from the top most level.