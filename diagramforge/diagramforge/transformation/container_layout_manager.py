from collections import defaultdict
from copy import deepcopy
from typing import Dict, List

import networkx as nx
import numpy as np
from scipy.sparse import csgraph
from scipy.sparse.linalg import eigsh

from diagramforge.schema.base import ShapeBase
from diagramforge.schema.shapes import Association, CollapsedPool, Diagram, Event, Gateway, Lane, Pool, Task
from diagramforge.SETUP import forge_logger


class ContainerLayoutManager:
    """Handles positioning and ordering of pools, lanes, and nested lanes.

    This class constructs mappings for lane relationships, calculates pool and lane orders,
    and attempts to minimize lane crossings using a spectral layout approach combined with
    local optimizations.
    """

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        resource_id_to_shape_mapping: Dict[str, ShapeBase],
        node_resource_id_to_parent_mapping: Dict[str, Dict[str, ShapeBase]],
    ) -> None:
        """Initializes a ContainerPositioner.

        Args:
            graph (networkx.DiGraph): A graph containing diagram nodes and edges.
            node_resource_id_to_parent_mapping (dict): A mapping of node resource IDs
                to parent information, including pools, lanes, and nested lanes.
        """
        self.graph = graph
        self.resource_id_to_shape_mapping = resource_id_to_shape_mapping
        self.node_resource_id_to_parent_mapping = node_resource_id_to_parent_mapping

        # Cross-methodical class instance variables in order of usage
        self.lane_to_pool_mapping: Dict[str, str] = None
        self.lane_list_by_pool: Dict[str, List[str]] = None
        self.lane_list_by_lane: Dict[str, List[str]] = None
        self.node_count_by_pool_sorted: Dict[str, int] = None
        self.node_count_per_lane_sorted: Dict[str, int] = None
        self.lanes_outbound_connection_matrix_by_pool: Dict[str, Dict[str, Dict[str, int]]] = None
        self.pools_outbound_connection_matrix: Dict[str, Dict[str, int]] = None

        self.pool_order: dict = None
        self.lane_positions_by_pool: dict = None

        # Create auxiliary mappings
        self.__construct_auxiliary_mappings()

    def __construct_auxiliary_mappings(self):
        """Constructs auxiliary mappings for pool-lane relationships.

        This function identifies top-level lanes, nested lanes, and builds up counters for
        node distribution and inter-lane connections within each pool.
        """
        self.lane_to_pool_mapping = defaultdict(str)
        self.lane_list_by_pool = defaultdict(list)

        # Identify top-level lanes by pool, and build lane_to_pool (for top-level lanes).
        self.top_level_lane_to_pool_mapping = {}

        # Identify nested lanes by parent lane.
        self.lane_list_by_lane = defaultdict(list)
        self.lane_to_parent_lane = {}  # If a lane is nested, store lane->parent_lane

        # Each node also gets "top_level_lane" and "actual_lane".
        for node_id, parent_dict in self.node_resource_id_to_parent_mapping.items():
            pool_id = parent_dict["pool"]
            top_lane = parent_dict["lane"]  # The outer lane
            nested_lane = parent_dict["nested_lane"]

            # Always store the top-level lane.
            parent_dict["top_level_lane"] = top_lane

            # If there's a nested lane, that becomes the node's 'actual_lane'.
            if nested_lane:
                parent_dict["actual_lane"] = nested_lane

                if nested_lane not in self.lane_list_by_lane[top_lane]:
                    self.lane_list_by_lane[top_lane].append(nested_lane)
                self.lane_to_parent_lane[nested_lane] = top_lane
            else:
                parent_dict["actual_lane"] = top_lane

            # Track which pool each top-level lane belongs to.
            if top_lane not in self.lane_list_by_pool[pool_id]:
                self.lane_list_by_pool[pool_id].append(top_lane)
            self.top_level_lane_to_pool_mapping[top_lane] = pool_id

        # Create a mapping of the number of nodes per pool
        self.node_count_by_pool_sorted = defaultdict(int)
        for _, parent_dict in self.node_resource_id_to_parent_mapping.items():
            self.node_count_by_pool_sorted[parent_dict["pool"]] += 1
        self.node_count_by_pool_sorted = dict(
            sorted(self.node_count_by_pool_sorted.items(), key=lambda item: item[1], reverse=True)
        )

        # Create a mapping of the number of nodes per lane
        self.node_count_per_lane_sorted = defaultdict(int)
        for _, parent_dict in self.node_resource_id_to_parent_mapping.items():
            self.node_count_per_lane_sorted[parent_dict["actual_lane"]] += 1
        self.node_count_per_lane_sorted = dict(
            sorted(self.node_count_per_lane_sorted.items(), key=lambda item: item[1], reverse=True)
        )

        # Create a mapping of the number of outbound connections per pool (including collapsed pools)
        self.pools_outbound_connection_matrix = defaultdict(lambda: defaultdict(int))
        for source_node, target_node in self.graph.edges():
            if isinstance(self.resource_id_to_shape_mapping[source_node], (CollapsedPool, Pool)):
                source_pool = source_node
            else:
                source_pool = self.node_resource_id_to_parent_mapping[source_node]["pool"]
            if isinstance(self.resource_id_to_shape_mapping[target_node], (CollapsedPool, Pool)):
                target_pool = target_node
            else:
                target_pool = self.node_resource_id_to_parent_mapping[target_node]["pool"]

            if source_pool != target_pool:
                self.pools_outbound_connection_matrix[source_pool][target_pool] += 1
                self.pools_outbound_connection_matrix[target_pool][source_pool] += 1

        # Create a mapping of the number of outbound connections per lane (by pool)
        self.lanes_outbound_connection_matrix_by_pool = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        for pool in self.lane_list_by_pool.keys():
            for source_node, target_node in self.graph.edges():
                if isinstance(
                    self.resource_id_to_shape_mapping[source_node],
                    (
                        CollapsedPool,
                        Pool,
                    ),
                ) or isinstance(
                    self.resource_id_to_shape_mapping[target_node],
                    (
                        CollapsedPool,
                        Pool,
                    ),
                ):
                    # Skip connections between pools
                    continue

                source_pool = self.node_resource_id_to_parent_mapping[source_node]["pool"]
                target_pool = self.node_resource_id_to_parent_mapping[target_node]["pool"]
                if source_pool != pool or target_pool != pool:
                    continue

                source_lane = self.node_resource_id_to_parent_mapping[source_node]["top_level_lane"]
                target_lane = self.node_resource_id_to_parent_mapping[target_node]["top_level_lane"]

                if source_lane != target_lane:
                    # Add the connection from the source lane to the target lane
                    self.lanes_outbound_connection_matrix_by_pool[pool][source_lane][target_lane] += 1
                    self.lanes_outbound_connection_matrix_by_pool[pool][target_lane][source_lane] += 1

            not self.lanes_outbound_connection_matrix_by_pool and forge_logger.debug(
                "No outbound connections between lanes found."
            )

    def determine_pool_order(self) -> dict:
        """Determines the order of pools based on descending node counts first. If multiple pools are present, the order
        of pools is adjusted to minimize crossings of associations.

        Returns:
            dict: A mapping of pool IDs to their new indices.
        """
        self.pool_order = defaultdict(int)
        for i, pool in enumerate(self.node_count_by_pool_sorted.keys()):
            self.pool_order[pool] = i

        if not self.pools_outbound_connection_matrix:
            forge_logger.debug("No outbound connections between pools found. Using default pool order.")
            return self.pool_order

        # Safe pool order for cross-check
        pool_order_safe = deepcopy(self.pool_order)

        # Put the pools in order to minimize crossings of associations
        self.pool_order = self.__determine_pool_priority(
            pool_connections=self.pools_outbound_connection_matrix,
            start_pool=list(self.node_count_by_pool_sorted.keys())[0],
        )

        # Cross-check for any missing pools and add them back in the given order + 1
        for pool in pool_order_safe.keys():
            if pool not in self.pool_order:
                self.pool_order[pool] = len(self.pool_order)

        return self.pool_order

    def __determine_pool_priority(self, pool_connections: Dict[str, Dict[str, int]], start_pool: str) -> List[str]:
        """
        Sorts a dictionary of connected elements to minimize "crossings" in a linear layout.

        This function uses a greedy heuristic. It starts with a given node and iteratively
        adds the most strongly connected remaining node to the sorted list. This tends
        to group tightly connected elements together.

        Args:
            data: A dictionary where keys are node IDs and values are dictionaries
                of connected nodes and their connection weights (integers).
            start_node: The ID of the node to start the sorting from.

        Returns:
            A list of node IDs sorted to minimize crossings.

        Raises:
            ValueError: If the start_node is not found in the data keys.
        """

        if not pool_connections:
            return []

        if start_pool not in pool_connections:
            raise ValueError(f"The start_node '{start_pool}' was not found in the data.")

        all_node_ids = set(pool_connections.keys())

        # Initialize with the starting node
        sorted_list = [start_pool]
        placed_nodes = {start_pool}

        # The main loop continues until all nodes have been placed in the sorted_list
        while len(placed_nodes) < len(all_node_ids):
            unplaced_nodes = all_node_ids - placed_nodes

            best_next_node = None
            max_connectivity_score: int = -1

            # Find the unplaced node with the strongest connection to the already placed nodes
            for candidate_node in unplaced_nodes:
                current_score = 0
                # Calculate the sum of weights from the candidate to all placed nodes
                for node_in_list in placed_nodes:
                    # Check for a connection from the placed node to the candidate.
                    # The .get(candidate_node, 0) handles cases where there's no direct edge.
                    # connection_weight = pool_connections.get(node_in_list, {}).get(candidate_node, 0)
                    # current_score += connection_weight

                    current_score += (
                        pool_connections.get(node_in_list, {}).get(candidate_node, 0)
                        + pool_connections.get(candidate_node, {}).get(node_in_list, 0)  # count reverse edge
                    )

                if current_score > max_connectivity_score:
                    max_connectivity_score = current_score
                    best_next_node = candidate_node

            # If max_connectivity_score is still 0, it means the remaining nodes are a
            # disconnected component. We can pick any one to continue.
            if best_next_node is None:
                node_to_add = list(unplaced_nodes)[0]
            else:
                node_to_add = best_next_node

            # Add the chosen node to our results and update the sets
            sorted_list.append(node_to_add)
            placed_nodes.add(node_to_add)

        pool_order_dict = {node_id: index for index, node_id in enumerate(sorted_list)}

        return pool_order_dict

    def determine_lane_positions_by_pool(self) -> Dict[str, List[str]]:
        """Determines lane positions for each pool to minimize lane crossings.

        Returns:
            Dict[str, List[str]]
                A mapping of pool IDs to lists of lanes in the best order found.
        """
        self.lane_positions_by_pool = defaultdict(list)

        # If no order could be determined, use the default order
        if not self.lanes_outbound_connection_matrix_by_pool:
            self.lanes_outbound_connection_matrix_by_pool = deepcopy(self.lane_list_by_pool)

        for pool, lanes_connections_matrix in self.lanes_outbound_connection_matrix_by_pool.items():
            if isinstance(lanes_connections_matrix, list):
                # This means no connections were found between lanes in this pool
                self.lane_positions_by_pool[pool] = lanes_connections_matrix
                continue

            if len(lanes_connections_matrix) <= 2:
                if len(self.lane_list_by_pool[pool]) > len(list(lanes_connections_matrix)):
                    self.lane_positions_by_pool[pool] = list(self.lane_list_by_pool[pool])
                else:
                    self.lane_positions_by_pool[pool] = list(lanes_connections_matrix)
                continue

            lane_positions, over_lane_crossings, total = self.__determine_lane_positions(lanes_connections_matrix)

            forge_logger.debug(
                f"Optimized lane order to minimize over-lane crossings for pool '{pool}': "
                f"{lane_positions} with {over_lane_crossings} over-lane crossings. {total} total lanes crossed."
            )

            self.lane_positions_by_pool[pool] = lane_positions

        # Cross-check for any missing lanes
        for pool_id, lane_list in self.lane_list_by_pool.items():
            # Ensure all lanes in the pool are included in the positions
            for lane in lane_list:
                if pool_id not in self.lane_positions_by_pool:
                    self.lane_positions_by_pool[pool_id] = []

                if lane not in self.lane_positions_by_pool[pool_id]:
                    self.lane_positions_by_pool[pool_id].append(lane)

                # FIX: Check whether this is necessary here and not covered by code later on
                # if lane in self.lane_list_by_lane:
                #     for nested_lane in self.lane_list_by_lane[lane]:
                #         if nested_lane not in self.lane_positions_by_pool[pool_id]:
                #             self.lane_positions_by_pool[pool_id].append(nested_lane)

        return self.lane_positions_by_pool

    def determine_nested_lane_positions(self) -> Dict[str, List[str]]:
        """Determines positions for nested lanes within each top-level lane.

        Returns:
            dict: A mapping of each parent lane to a list of its nested lanes in the best order found.
        """
        self.lane_positions_by_lane = {}

        for parent_lane, child_lanes in self.lane_list_by_lane.items():
            if len(child_lanes) <= 1:
                self.lane_positions_by_lane[parent_lane] = child_lanes
                continue

            # Build adjacency among these child_lanes
            connections = defaultdict(lambda: defaultdict(int))
            for source_node, target_node in self.graph.edges():
                if (
                    source_node not in self.node_resource_id_to_parent_mapping
                    or target_node not in self.node_resource_id_to_parent_mapping
                ):
                    continue

                s_lane = self.node_resource_id_to_parent_mapping[source_node]["actual_lane"]
                t_lane = self.node_resource_id_to_parent_mapping[target_node]["actual_lane"]
                if s_lane in child_lanes and t_lane in child_lanes and s_lane != t_lane:
                    connections[s_lane][t_lane] += 1
                    connections[t_lane][s_lane] += 1

            # Then call the same crossing-minimization
            lane_order, over_lane_crossings, total = self.__determine_lane_positions(connections)
            self.lane_positions_by_lane[parent_lane] = lane_order

            # Cross-check for any missing nested lanes
            for lane in child_lanes:
                if lane not in self.lane_positions_by_lane[parent_lane]:
                    self.lane_positions_by_lane[parent_lane].append(lane)

        return self.lane_positions_by_lane

    def __determine_lane_positions(self, connections: dict) -> tuple:
        """Determines the optimal lane order to reduce over-lane crossings.

        Args:
            connections (dict): A mapping of lane IDs to other lanes and the
                weight of their connections.

        Returns:
            tuple: A tuple containing:
                - lane_order (list[str]): The optimal lane order.
                - over_lane_crossings (int): The number of connections crossing over intermediate lanes.
                - total_lanes_crossed (int): Total lanes crossed, weighted by connection counts.
        """
        lane_order = []
        over_lane_crossings = 0

        # Collect all lanes and assign indices
        lanes = set()
        for key, value in connections.items():
            lanes.add(key)
            lanes.update(value.keys())
        lanes = list(sorted(lanes))
        lane_index = {lane: idx for idx, lane in enumerate(lanes)}

        # Build adjacency matrix
        n = len(lanes)
        adjacency_matrix = np.zeros((n, n))
        for lane1 in connections:
            idx1 = lane_index[lane1]
            for lane2, weight in connections[lane1].items():
                idx2 = lane_index[lane2]
                adjacency_matrix[idx1][idx2] += weight
                adjacency_matrix[idx2][idx1] += weight

        # Compute Laplacian matrix
        laplacian = csgraph.laplacian(adjacency_matrix, normed=False)
        laplacian = (laplacian + laplacian.T) / 2

        # Compute the Fiedler vector
        eigenvalues, eigenvectors = eigsh(laplacian, k=2, which="SM")
        fiedler_vector = eigenvectors[:, 1]

        # Initial lane order based on the Fiedler vector
        sorted_indices = np.argsort(fiedler_vector)
        lane_order = [lanes[i] for i in sorted_indices]

        # Local optimization to minimize crossings
        def calculate_total_lanes_crossed(local_lane_order):
            positions = {lane: idx for idx, lane in enumerate(local_lane_order)}
            total_lanes_crossed = 0
            for l1 in connections:
                for l2, w in connections[l1].items():
                    pos_diff = abs(positions[l1] - positions[l2])
                    if pos_diff > 0:
                        lanes_crossed = (pos_diff - 1) * w
                        total_lanes_crossed += lanes_crossed
            return total_lanes_crossed

        min_total_lanes_crossed = calculate_total_lanes_crossed(lane_order)
        improved = True

        while improved:
            improved = False
            for i in range(len(lane_order) - 1):
                new_lane_order = lane_order.copy()
                new_lane_order[i], new_lane_order[i + 1] = new_lane_order[i + 1], new_lane_order[i]
                new_total_lanes_crossed = calculate_total_lanes_crossed(new_lane_order)
                if new_total_lanes_crossed < min_total_lanes_crossed:
                    lane_order = new_lane_order
                    min_total_lanes_crossed = new_total_lanes_crossed
                    improved = True
                    break

        # Calculate final crossing metrics
        positions = {lane: idx for idx, lane in enumerate(lane_order)}
        total_lanes_crossed = 0
        for lane1 in connections:
            for lane2, weight in connections[lane1].items():
                pos_diff = abs(positions[lane1] - positions[lane2])
                if pos_diff > 1:
                    over_lane_crossings += weight
                    lanes_crossed = (pos_diff - 1) * weight
                    total_lanes_crossed += lanes_crossed
                else:
                    lanes_crossed = 0

        forge_logger.debug(f"Lanes positioned | ordered lanes list: {lane_order}")
        return lane_order, over_lane_crossings, total_lanes_crossed
