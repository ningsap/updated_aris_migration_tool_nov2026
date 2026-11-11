# Assigning Rows to Nodes

The final step before a diagram can be rendered into the SPM JSON format, is to assign each node to a row. Mainly responsible for this task is the [`RowPositioner`](../../diagramforge/transformation/row_positioner.py) class and as before, it is orchestrated within the [`Diagram Forge`](../../diagramforge/diagramforge.py#L107) class.

## Table of Contents <!-- omit in toc -->
- [Initialization](#initialization)
- [Positioning Rows](#positioning-rows)
- [Optimizing Flow Layout](#optimizing-flow-layout)
  - [Steps:](#steps)
- [Crossing Minimization Algorithm](#crossing-minimization-algorithm)
  - [Algorithm Steps](#algorithm-steps)
  - [1. Left-to-Right Sweep](#1-left-to-right-sweep)
  - [2. Right-to-Left Sweep](#2-right-to-left-sweep)
    - [Example:](#example)
- [Row Compaction](#row-compaction)
- [Usage Notes](#usage-notes)



## Initialization

The `RowPositioner` is initialized with:
- `graph (nx.MultiDiGraph)`: The BPMN diagram's graph structure.
- `bpmn_adjusted_columns (Dict[int, List[str]])`: Column assignments for nodes (from prior layout steps).
- `lane_positions_by_pool (Dict[str, List[str]])`: Ordered lanes per pool (from `ContainerLayoutManager`).
- `lane_positions_by_lane (Dict[str, List[str]])`: Ordered nested lanes per parent lane.
- `node_resource_id_to_parent_mapping (Dict[str, ShapeBase])`: Node-to-container relationships.

Key attributes initialized:
- `bpmn_adjusted_grid (Dict[str, Dict[str, Dict[Literal["col", "row"], int]]])`: Final node positions stored as `{lane_id: {node: {col: integer, row: integer}}}`.

---

## Positioning Rows

> Method: `position_rows`

#### Inputs <!-- omit in toc -->
- `lane_positions_by_pool` (from initialization).
- `lane_positions_by_lane` (from initialization).

#### Outputs <!-- omit in toc -->
- `bpmn_adjusted_grid`: Final grid mapping lanes to node positions.

---

Other than the previous components, the `Diagram Forge` class does not orchestrate this class. Instead, it calls the `position_rows` method, which is responsible for arranging nodes within lanes. The idea is to arrange the nodes per pool as follows:

1. Identifies the current pool (currently supports single-pool diagrams).
2. Calls `optimize_flow_layout` to arrange nodes within lanes.


## Optimizing Flow Layout

> Method: `optimize_flow_layout`

#### Inputs <!-- omit in toc -->
- `current_pool (str)`: Target pool for layout optimization.

#### Outputs <!-- omit in toc -->
- Updates `self.bpmn_adjusted_grid` with optimized node positions.

### Steps:

1. **Lane Order Resolution**:  
   - Combines top-level and nested lanes into a single ordered list (e.g., `["LaneA", "NestedLane1", "NestedLane2"]`).
2. **Column Mapping**:  
   - Maps nodes to globally compacted column indices (e.g., original columns `[2,5]` → `[0,1]`).
3. **Lane Subgraph Processing**:  
   - For each lane, creates a subgraph of its nodes and applies crossing minimization.
4. **Crossing Minimization**:  
   - Invokes `minimize_crossings` to align nodes based on predecessor/successor relationships.
5. **Row Compaction**:  
   - Removes empty rows via `compact_rows` to ensure consecutive numbering.

---

## Crossing Minimization Algorithm

> Method: `minimize_crossings`

#### Inputs <!-- omit in toc -->
- `lane_subgraph (nx.MultiDiGraph)`: Subgraph of nodes in the current lane.
- `node_positions (Dict[str, Dict[Literal["col", "row"], int]])`: Current `{node: {col, row}}` assignments.
- `columns (Dict[int, List[str]])`: Nodes grouped by column index.
- `iterations (int)`: Number of optimization sweeps (configurable via `FORGE_CONFIG`).

### Algorithm Steps

### 1. Left-to-Right Sweep
- **Objective**: Align nodes with predecessors.  
- **Process**:
  1. For each column (excluding the first):
     - Calculate "desired rows" for nodes based on predecessor positions:
       - If all predecessors are in another lane, place at top/bottom edge.
       - Use predecessor barycenter (average row) for multi-predecessor nodes.
     - Sort nodes by desired row.
     - Assign rows sequentially, avoiding conflicts.

### 2. Right-to-Left Sweep
- **Objective**: Align nodes with successors.  
- **Process**:
  1. For each column (reverse order, excluding last):
     - Calculate desired rows using successor positions (similar to L→R sweep).
     - Sort and assign rows while resolving conflicts.

#### Example:
- **Before Sweep**: Nodes `A→B` with `A` at row 2, `B` unplaced.  
- **After L→R**: `B` placed at row 2 (aligned with `A`).  
- **After R→L**: Adjustments made if `B`'s successors require alignment.

---

## Row Compaction

> Method: `compact_rows`

#### Inputs <!-- omit in toc -->
- `node_positions`: Node positions with potential row gaps.

#### Process <!-- omit in toc -->
1. Identifies used rows (e.g., `[0, 2, 3]` → gaps at row 1).
2. Re-maps rows to consecutive integers (e.g., `[0→0, 2→1, 3→2]`).


## Usage Notes

- **Edge Cases**:  
  - Nodes without predecessors/successors retain original positions.
  - Single-node lanes are skipped during optimization.