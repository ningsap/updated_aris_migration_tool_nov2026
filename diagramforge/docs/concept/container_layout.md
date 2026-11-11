# Container Layout

After assigning columns to all nodes, the order of pools and lanes, i.e. containers, needs to be determined. This has to happen before rows can be assigned to the nodes, hence the position of lanes has direct influence on the rows yet not on the columns.

This step is mainly covered in the [`ContainerLayoutManager`](../../diagramforge/transformation/container_layout_manager.py) class. Again, the [`Diagram Forge`](../../diagramforge/diagramforge.py#L90) class orchestrates the calls of the respective methods in the correct order.

## Table of Contents <!-- omit in toc -->
- [Initialization](#initialization)
- [Determining the order of pools](#determining-the-order-of-pools)
- [Determining the order of lanes](#determining-the-order-of-lanes)
- [Determining the order of nested lanes](#determining-the-order-of-nested-lanes)
- [Helper method: `__determine_lane_positions`](#helper-method-__determine_lane_positions)
  - [Overview](#overview)
  - [Algorithm Steps](#algorithm-steps)
    - [1. Lane Collection \& Indexing](#1-lane-collection--indexing)
    - [2. Adjacency Matrix Construction](#2-adjacency-matrix-construction)
    - [3. Laplacian Matrix Computation](#3-laplacian-matrix-computation)
    - [4. Fiedler Vector Calculation](#4-fiedler-vector-calculation)
    - [5. Initial Lane Ordering](#5-initial-lane-ordering)
    - [6. Local Optimization (Greedy Swapping)](#6-local-optimization-greedy-swapping)
    - [7. Crossing Metrics Calculation](#7-crossing-metrics-calculation)
  - [Usage Notes](#usage-notes)


## Initialization

The `ContainerLayoutManager` is initialized with the following parameters:
- `graph (nx.MultiDiGraph)` - The directed graph representing the BPMN diagram
- `node_resource_id_to_parent_mapping (Dict[str, Dict[str, ShapeBase]])` - A dictionary mapping resource IDs to their respective parent shapes

In addition, the `__init__` method calls the `construct_auxiliary_mappings` method to populate the following attributes:

- `lane_to_pool_mapping (Dict[str, str])` - A dictionary mapping lanes to their respective pools
- `lane_list_by_pool (Dict[str, List[str]])` - A dictionary mapping a list of lanes to their respective pools
- `lane_list_by_lane (Dict[str, List[str]])` - A dictionary mapping a list of lanes to their respective lanes (nested lanes)
- `node_count_by_pool_sorted (Dict[str, int])` - A dictionary mapping pools to the number of nodes they contain, sorted by the number of nodes
- `node_count_per_lane_sorted (Dict[str, int])` - A dictionary mapping lanes to the number of nodes they contain, sorted by the number of nodes
- `lanes_outbound_connection_matrix_by_pool (Dict[str, Dict[str, Dict[str, int]]])` - A dictionary containing a lanes' outbound connections to other lanes by pool

All these mappings are used throughout the container layout process.

## Determining the order of pools

> Method: `determine_pool_order`

#### Inputs <!-- omit in toc -->
  - `self.node_count_by_pool_sorted (Dict[str, int])` - A dictionary mapping pools to the number of nodes they contain, sorted by the number of nodes

#### Outputs <!-- omit in toc -->
  - `self.pool_order (Dict[str, int])` - A dictionary mapping pools to their order
---

Straightforward: Assigns the pool order based on the number of nodes they contain so larger pools are displayed at the top of the diagram.

## Determining the order of lanes
> Method: `determine_lane_positions_by_pool`
>
#### Inputs <!-- omit in toc -->
  - `self.lanes_outbound_connection_matrix_by_pool (Dict[str, Dict[str, Dict[str, int]]])` - A dictionary containing a lanes' outbound connections to other lanes by pool

#### Outputs <!-- omit in toc -->
  - `self.lane_positions_by_pool (Dict[str, List[str]])` - A dictionary mapping pools to the order of lanes
---

This method determines the order of lanes within each pool. For that matter, the [`__determine_lane_positions`](#helper-method-__determine_lane_positions) is used which is described below.


## Determining the order of nested lanes
> Method: `determine_nested_lane_positions`
>
#### Inputs <!-- omit in toc -->
  - `lane_list_by_lane (Dict[str, List[str]])` - A dictionary mapping a list of lanes to their respective lanes (nested lanes)

#### Outputs <!-- omit in toc -->
  - `self.lane_positions_by_lane (Dict[str, List[str]])` - A dictionary mapping lanes to the order of nested lanes
---

This method determines the order of lanes within lanes if there are nested lanes. For that matter, the [`__determine_lane_positions`](#helper-method-__determine_lane_positions) is used.

## Helper method: `__determine_lane_positions`

### Overview

The `__determine_lane_positions` method is a core component of the `ContainerLayoutManager` class that calculates an optimal order for lanes within a pool or nested structure to minimize visual crossings between connected lanes. This method combines spectral graph theory with local optimization to achieve a balance between computational efficiency and layout quality.



#### Inputs <!-- omit in toc -->
- `connections (dict)` - A nested dictionary representing weighted connections between lanes. Format: {lane_id: {connected_lane_id: connection_weight, ...}, ...} Example: If lane A has 3 connections to lane B, the input would include `{"A": {"B": 3}, ...}`. Non-directional: Connections are treated as bidirectional (e.g., A→B and B→A are aggregated).

#### Outputs <!-- omit in toc -->
`tuple` Contains three elements:

- `lane_order (List[str])` - The optimized order of lanes (e.g., ["Lane2", "Lane1", "Lane3"]).
- `over_lane_crossings (int)` - The total number of connections that cross over intermediate lanes.
- `total_lanes_crossed (int)` - The weighted sum of lanes crossed by all connections (e.g., a connection spanning 2 lanes contributes 2 * weight).

### Algorithm Steps

#### 1. Lane Collection & Indexing
All unique lanes are extracted from the connections dictionary. Each lane is assigned a unique index (e.g., `{"LaneA": 0, "LaneB": 1}`).

#### 2. Adjacency Matrix Construction
A square matrix is created where the value at [i][j] represents the total connection weight between lane i and lane j. Symmetric: The matrix is mirrored across its diagonal to ensure bidirectionality.

#### 3. Laplacian Matrix Computation
The Laplacian matrix is derived from the adjacency matrix using scipy.sparse.csgraph.laplacian. This matrix encodes the structure of the graph and is critical for spectral analysis.

#### 4. Fiedler Vector Calculation
The Fiedler vector (eigenvector corresponding to the second-smallest eigenvalue of the Laplacian) is computed.This vector provides a 1D embedding of lanes where strongly connected lanes are positioned close to each other.

#### 5. Initial Lane Ordering
Lanes are sorted based on their corresponding values in the Fiedler vector.

Example: If the Fiedler vector is [0.2, -0.5, 0.3], lanes are ordered as [LaneB, LaneA, LaneC].

#### 6. Local Optimization (Greedy Swapping)
A greedy algorithm iteratively swaps adjacent lanes to reduce crossings: The current total lanes crossed is calculated. For each pair of adjacent lanes, their positions are swapped. If swapping reduces crossings, the new order is retained. The process repeats until no further improvements are possible.

#### 7. Crossing Metrics Calculation
After optimization, the final lane_order is analyzed to compute:

`over_lane_crossings`: Connections that skip one or more lanes.

`total_lanes_crossed`: Sum of (distance - 1) * weight for all connections.

### Usage Notes
Performance: Suitable for medium-sized graphs. Spectral decomposition (via eigsh) may become slow for very large lane sets (>1000 lanes).

Edge Cases:

If lanes have no connections, the initial order is based purely on the Fiedler vector (often arbitrary but deterministic).

For 1-2 lanes, no optimization is performed (handled by upstream methods).
