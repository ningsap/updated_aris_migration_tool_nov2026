# Conversion to Global Coordinates

Before tending to the sequence flow positioning, it is necessary to create a global coordinate system. Since the coordinates of Associations are absolute positions and not relative to any sub-canvas, the positions of all elements must be converted to global coordinates. In addition to that, it is important to know the relative positioning of the elements to each other.


## Table of Contents <!-- omit in toc -->
- [Global relative positioning](#global-relative-positioning)
  - [Initialization](#initialization)
  - [Relation between nodes in cardinal directions](#relation-between-nodes-in-cardinal-directions)
  - [Distance calculating methods](#distance-calculating-methods)
- [Global coordinate system](#global-coordinate-system)
  - [Used components](#used-components)
  - [Prerequisites \& assumption](#prerequisites--assumption)
  - [Calculation method](#calculation-method)
    - [Example](#example)


## Global relative positioning

The [`GlobalGridLookup`](../../diagramforge/rendering/flows/global_grid_lookup.py) class is responsible for translating the local grid of columns and rows to a global grid system. In other words, the columns and rows that were assigned to each node within their respective parent container are now converted to global columns and rows based on the local positions plus the offset of the parent container. The offset is derived from the order of pools and lanes that were calculated in the previous steps.

### Initialization

The `GlobalGridLookup` is initialized with:
- `bpmn_adjusted_grid (Dict[str, Dict[str, Dict[Literal["col", "row"], int]]])`: Final node positions stored as `{lane_id: {node: {col: integer, row: integer}}}`.
- `lane_positions_by_pool (Dict[str, List[str]])`: Mapping of pool IDs to a list of lane IDs.
- `lane_positions_by_lane (Dict[str, List[str]])`: Mapping of lane IDs to a list of lane IDs.
- `resource_id_to_shape_mapping (Dict[str, ShapeBase])`: Mapping of node IDs to their respective shapes.

Using the input the class was initialized with, the `GlobalGridLookup` servers as a lookup for various steps in the further process. The most important here are:

### Relation between nodes in cardinal directions
> Method: `determine_relative_direction`

#### Inputs <!-- omit in toc -->
- `source (str)`: The ID of the source node.
- `target (str)`: The ID of the target node.

#### Outputs <!-- omit in toc -->
- `(CARDINAL_DIRECTIONS)`: The direction of the target node relative to the source node.

This method returns the [`CARDINAL_DIRECTIONS`](../../diagramforge/helpers/STATICS.py#L37) of the target node relative to the source node. The direction is determined by comparing the global positions of both nodes in the global columns and rows grid. Especially for the determination of the sequence flow positions, this information is crucial.

### Distance calculating methods
> Methods: `get_row_distance`, `get_col_distance`, `is_a_node_in_between_on_row`

There is a number of helper methods within this class that helps determining how sequence flows are laid out later on. All these methods are based on the global columns and rows grid and are used to calculate the distance between two nodes in rows or columns and to check if there is a node in between two nodes on a row.

## Global coordinate system

The [`CoordinatesHandler`](../../diagramforge/rendering/coordinates_handler.py) is responsible for calculating the global coordinates of all elements in the diagram. It is also self-initializing with the following inputs:

- `diagram (Diagram)`: The diagram object.
- `resource_id_to_shape_mapping (Dict[str, ShapeBase])`: Mapping of node IDs to their respective shapes.

### Used components

- [`ShapeCoordsRecord`](../../diagramforge/rendering/shape_coords_record.py): Class to store the coordinates of a shape. Used mainly to maintain the reference to the original shape while allowing the calculation of global coordinates.

### Prerequisites & assumption

Calculating the global coordinates is a rather straightforward process. The premises are the following:

- The diagram (main canvas) is a coordinate system starting at (0,0) developing positive numbers to the right (X) and downwards (Y, inverted).
- Of all possible container elements, only Pools are directly tied to the diagram.
- Lanes must be located inside Pools.
- Nodes must be located inside Lanes.
- It is possible that a Lane is inside another Lane where the parent lane is inside a Pool (≤1 level of nesting is allowed).
- All coordinates of Associations are absolute positions and not relative to any sub-canvas (except for the "shape docker" that are added at the very end).
- All container elements and nodes that are inside of a container element have their positions relative to the top-left corner of the container element.

### Calculation method

With this in mind, the global coordinates are calculated by adding the local position of each element to the sum of all the element's parent container's top-left corner coordinates. This is done recursively for all elements in the diagram. For lanes inside pools, the shift on the Y-axis is calculated by the sum of the heights of all lanes above the current lane.

#### Example

A Task element's top-left corner is located on (300, 300) in a lane that is the "third" lane in its pool. Therefore, the lane's top-left is at (30, 500) - 30 on the X for the pool's header and shifted down by 500 on the Y for the two lanes above. The pool in which the lane is located is at (100, 100) - just to look nicer and not be jammed in the top-left corner of the diagram. The global position of the Task element is:
- X: 100 (pool) + 30 (lane) + 300 (Task) = 430
- Y: 100 (pool) + 500 (lane) + 300 (Task) = 900

For all further calculations until the diagram is done and the global coordinates can be reverted back into local ones, that Task's top-left corner is at (430, 900) in the global coordinate system.

The method `revert_global_to_local_coords` functions in the same way but in reverse. It is used right before the final output.