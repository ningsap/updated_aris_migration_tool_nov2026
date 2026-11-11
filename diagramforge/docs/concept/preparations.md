# PreparationTool

The [PreparationTool](../../diagramforge/transformation/preparation_tool.py) is a class that prepares the input data for the optimization process. This page explains the methods and attributes used in the preparation process.

### Table of Contents <!-- omit in toc -->
- [Initialization](#initialization)
- [Building the Graph](#building-the-graph)
- [Shapes to resource ID mapping](#shapes-to-resource-id-mapping)
- [Create a mapping between resource IDs and the respective shapes' parent elements](#create-a-mapping-between-resource-ids-and-the-respective-shapes-parent-elements)


## Initialization

The general concept is that the [DiagramForge Class](../../diagramforge/diagramforge.py#L66) is calling all required methods from the sub-components within itself in the intended sequence. The following are the separate methods along with their inputs and outputs.

This class is initialized with the following attributes:
- `diagram: (Diagram)` - The Pydantic model representing the BPMN diagram


## Building the Graph
> Method: `build_graph`

#### Inputs <!-- omit in toc -->
  - `self.diagram` - The diagram the class is initialized with

#### Outputs <!-- omit in toc -->
  - `graph: (nx.DiGraph)` - A directed graph representing the BPMN diagram

---

Quick and painless: This method creates a graph based on the diagram's elements and their relationships. The nodes are the elements themselves, and the edges are the relationships between them. The graph is then used as the basis for the optimization process.

The nested `get_nodes_and_edges` retrieves the nodes and edges, i.e. Tasks, Gateways, Events (nodes) as well as Sequence Flows (edges) from the diagram. Based on the results, the graph is built using the tools of the `networkx` library.

During this process, the method might raise the following exceptions:
- `NotConnectedSequenceFlowsRemain`: If sequence flows are not connected to nodes.
- `UnknownSequenceFlowTarget`: If a sequence flow has an unknown target.

## Shapes to resource ID mapping
> Method: `create_resource_id_to_shape_mapping`

#### Inputs <!-- omit in toc -->
  - `self.diagram` - The diagram the class is initialized with

#### Outputs <!-- omit in toc -->
  - `resource_id_to_shape_mapping: (Dict[str, Shape])` - A dictionary mapping resource IDs to their respective shapes
---

This method creates a mapping between the resource IDs and the shapes of the diagram. This mapping is used to quickly access the shape of a specific element based on its resource ID.

It can raise the following exceptions:
- `ResourceIdNotUnique`: If the resource ID is not unique in the diagram.

## Create a mapping between resource IDs and the respective shapes' parent elements
> Method: `create_node_resource_id_to_parent_mapping`

#### Inputs <!-- omit in toc -->
  - `self.diagram` - The diagram the class is initialized with

#### Outputs <!-- omit in toc -->
  -  `resource_id_to_parent_mapping: (Dict[str, Dict[str, ShapeBase]])` - A dictionary mapping resource IDs to their respective parent shapes
---

This method creates a mapping between the resource IDs of the nodes and their respective parent shapes. This mapping is used to quickly access the parent shape of a specific node based on its resource ID.

It accepts parents up to one level of nesting. The final dict looks like this:

```python
{
    "resource_id": {
        "pool": <Parent Pool Object>,
        "lane": <Parent Lane Object>,
        "nested_lane": <Parent Nested Lane Object>,
    }
}
```

It can raise the following exceptions:
- `LaneNotInPool`: If a lane does not belong to a pool.
- `ShapeNotInLane`: If a shape that must be in a lane is not.