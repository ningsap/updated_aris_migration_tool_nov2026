from collections import defaultdict
from typing import Dict, Union

import networkx as nx

from diagramforge.exceptions.graph_conversion import (
    LaneNotInPool,
    NotConnectedSequenceFlowsRemain,
    ResourceIdNotUnique,
    ShapeNotInLane,
    UnknownSequenceFlowTarget,
)
from diagramforge.schema.base import ShapeBase
from diagramforge.schema.shapes import Association, CollapsedPool, Diagram, Event, Gateway, Lane, Pool, Task
from diagramforge.schema.stencils import AssociationStencil
from diagramforge.SETUP import forge_logger


class PreparationTool:
    """A tool for preparing diagram data by building a graph, mapping resource IDs, and assigning nodes to pools and lanes."""

    def __init__(self, diagram: Diagram):
        """Initializes the PreparationTool.

        Args:
            diagram (Diagram): A Diagram object containing the BPMN diagram representation.
        """

        self.diagram = diagram
        self.faulty_edges_ids = []

    def build_graph(self) -> nx.DiGraph:
        """Builds a directed graph from the diagram's tasks, events, gateways, and sequence flows.

        Returns:
            nx.DiGraph: A directed graph representing the flow of the diagram.

        Raises:
            NotConnectedSequenceFlowsRemain: If sequence flows are not connected to nodes.
            UnknownSequenceFlowTarget: If a sequence flow has an unknown target.
        """

        G = nx.MultiDiGraph()

        # Add nodes first
        nodes: list[Union[Task, Event, Gateway, CollapsedPool]] = []
        associations: list[Association] = []

        def get_nodes_and_edges(shape: ShapeBase) -> None:
            """Recursively obtains node-like shapes and sequence flows from the diagram.

            Args:
                shape (ShapeBase): The shape to analyze.
            """
            if isinstance(shape, (Task, Event, Gateway, CollapsedPool)):
                nodes.append(shape)
            elif isinstance(shape, Association):
                if shape.stencil.id in (AssociationStencil.SEQUENCE_FLOW, AssociationStencil.MESSAGE_FLOW):
                    associations.append(shape)
            else:
                if not isinstance(shape, (Pool, Lane, Diagram)):
                    forge_logger.warning(f"Shape with ID {shape.resource_id} is not a node-like element.")

            if shape.child_shapes:
                for child_shape in shape.child_shapes:
                    get_nodes_and_edges(child_shape)

        get_nodes_and_edges(self.diagram)

        # Add nodes to the graph
        outgoing_list: list[str] = []
        for node in nodes:
            G.add_node(node.resource_id, shape=node)

            if node.outgoing:
                for outgoing in node.outgoing:
                    outgoing_list.append(outgoing.resource_id)

        # Add edges to the graph
        association_id_to_target = defaultdict(str)
        for association_flows in associations:
            if association_flows.resource_id in outgoing_list:
                association_id_to_target[association_flows.resource_id] = association_flows.target.resource_id
                outgoing_list.remove(association_flows.resource_id)

        if len(outgoing_list) > 0 and all([outgoing in association_id_to_target for outgoing in outgoing_list]):
            raise NotConnectedSequenceFlowsRemain(sequence_flow_ids=outgoing_list)

        for node in nodes:
            if node.outgoing:
                for outgoing in node.outgoing:
                    node_resource_id = node.resource_id
                    target_resource_id = association_id_to_target.get(outgoing.resource_id)

                    if outgoing.resource_id in self.faulty_edges_ids:
                        continue

                    if not target_resource_id:
                        raise UnknownSequenceFlowTarget(
                            sequence_flow_id=outgoing.resource_id, target_id=target_resource_id
                        )

                    if node_resource_id == target_resource_id:
                        forge_logger.warning(
                            f"Node {node_resource_id} is connected to itself via sequence flow {outgoing.resource_id}. Ignoring."
                        )
                        self.faulty_edges_ids.append(outgoing.resource_id)
                        continue

                    G.add_edge(node_resource_id, target_resource_id)

        if self.faulty_edges_ids:
            for canvas_level_shape in self.diagram.child_shapes:
                if (
                    isinstance(canvas_level_shape, Association)
                    and canvas_level_shape.resource_id in self.faulty_edges_ids
                ):
                    self.diagram.child_shapes.remove(canvas_level_shape)

        return G

    def create_resource_id_to_shape_mapping(self) -> Dict[str, ShapeBase]:
        """Creates a mapping of resource IDs to their respective ShapeBase objects in the diagram.

        Raises:
            ResourceIdNotUnique: If the resource ID is not unique in the diagram.

        Returns:
            dict: A dictionary mapping resource IDs to ShapeBase objects.
        """

        resource_id_to_shape_mapping = defaultdict(ShapeBase)

        def iterate_shapes(shape: ShapeBase) -> None:
            """Recursively adds shapes to the mapping, ensuring each resource ID is unique.

            Args:
                shape (ShapeBase): The shape to iterate through.
            """
            if shape.resource_id not in resource_id_to_shape_mapping:
                resource_id_to_shape_mapping[shape.resource_id] = shape
            else:
                raise ResourceIdNotUnique(resource_id=shape.resource_id)

            if shape.child_shapes:
                for child_shape in shape.child_shapes:
                    iterate_shapes(child_shape)

        iterate_shapes(self.diagram)
        return resource_id_to_shape_mapping

    def create_node_resource_id_to_parent_mapping(self) -> Dict[str, Dict[str, ShapeBase]]:
        """Creates a mapping of node resource IDs to their respective pool, lane, and nested lane.

        Raises:
            LaneNotInPool: If a lane does not belong to a pool.
            ShapeNotInLane: If a shape that must be in a lane is not.

        Returns:
            dict: A dictionary mapping node resource IDs to a dict detailing pool, lane, and nested lane.
        """

        node_resource_id_to_parent_mapping = defaultdict(dict)

        def iterate_shapes(shape: ShapeBase, pool_parent: str, lane_parent: str, nested_lane_parent: str) -> None:
            """Recursively determines the pool and lane hierarchy for diagram shapes.

            Args:
                shape (ShapeBase): The shape to analyze.
                pool_parent (str): The current pool resource ID.
                lane_parent (str): The current lane resource ID.
                nested_lane_parent (str): The current nested lane resource ID.
            """

            if isinstance(shape, Pool):
                pool_parent = shape.resource_id

            if isinstance(shape, Lane):
                if not pool_parent:
                    raise LaneNotInPool(resource_id=shape.resource_id)
                if lane_parent:
                    nested_lane_parent = shape.resource_id
                else:
                    lane_parent = shape.resource_id

            if isinstance(shape, (Task, Event, Gateway)):
                if pool_parent and lane_parent:
                    node_resource_id_to_parent_mapping[shape.resource_id] = {
                        "pool": pool_parent,
                        "lane": lane_parent,
                        "nested_lane": nested_lane_parent,
                    }
                elif not lane_parent:
                    raise ShapeNotInLane(resource_id=shape.resource_id)

            if shape.child_shapes:
                for child_shape in shape.child_shapes:
                    iterate_shapes(child_shape, pool_parent, lane_parent, nested_lane_parent)

        iterate_shapes(self.diagram, pool_parent=None, lane_parent=None, nested_lane_parent=None)
        return node_resource_id_to_parent_mapping
