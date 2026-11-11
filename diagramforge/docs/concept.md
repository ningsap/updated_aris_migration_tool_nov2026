# Concept

This is a high-level overview of the data flow explaining the overarching concept behind the Diagram Forge package and how it works. It is meant to give you a general understanding of the package and its functionality. You will find links to more detailed information on various components throughout this page.

It is divided into two main stages: the logical placement of all elements and the rendering of the diagram for proper visualization in SPM. The former places all elements into a grid system, and the latter uses that to calculate the exact position of each element.

### Table of Contents <!-- omit in toc -->
- [Logical Placement](#logical-placement)
  - [1. Input Data \& Format](#1-input-data--format)
  - [2. Preparations](#2-preparations)
  - [3. Assigning Columns to Nodes](#3-assigning-columns-to-nodes)
  - [4. Container Layout](#4-container-layout)
  - [5. Assigning Rows to Nodes](#5-assigning-rows-to-nodes)
- [Rendering Diagram](#rendering-diagram)
  - [6. Preparations \& Cleanup](#6-preparations--cleanup)
  - [7. Assign \& Calculate Positions in Sub-canvases](#7-assign--calculate-positions-in-sub-canvases)
  - [8. Conversion to Global Coordinates](#8-conversion-to-global-coordinates)
  - [9. Sequence Flow Positioning](#9-sequence-flow-positioning)
  - [10. Finalizing \& Output](#10-finalizing--output)

## Logical Placement

The first stage of the optimization process is the logical placement of all elements in the diagram. This stage is responsible for assigning each element to a column and row based on its relationships with other elements.

### 1. Input Data & Format
Diagram Forge accepts either of two input formats: the proprietary SPM JSON or the Pydantic representation of the BPMN diagram built using the blocks provided in the [schema](/diagramforge/schema/shapes.py). The former is transformed into the latter and is thereby validated. More information on the input data can be found at the [Usage](./usage.md) page.

### [2. Preparations](/docs/concept/preparations.md)

Before the actual optimization process starts, the input data is prepared. This includes transforming the input data into a format that is easier to work with and extracting relevant information. This step mainly consists of:
- Transforming the BPMN diagram into a graph representation, which becomes the basis for the optimization process  
  - BPMN elements are represented as *nodes* and their relationships as *edges*
- Building a base for the column assignment using a BFS traversal
- Mapping out all elements by their respective IDs
- Collecting all parents for every element

### [3. Assigning Columns to Nodes](/docs/concept/column_positioner.md)

Generally, the canvas of a BPMN diagram can be seen as a grid system. The optimization process assigns each node to a column and row. This step initiates that process by assigning nodes to columns based on their relationships and a predefined set of rules. Each node is traversed one or more times and is either *set* (i.e., assigned a column number) or pushed back to a later iteration, depending on the rules.

These rules are intended to be mutually exclusive and collectively exhaustive. This means each node can only be assigned to one column, and at the end of the process, all nodes must be assigned to a column by a specific rule. These rules are applied in a specific order using simple if statements.

### [4. Container Layout](/docs/concept/container_layout.md)

Unlike columns, rows are significantly influenced by the order of Pools and Lanes (i.e., Containers). Hence, each pool and each lane within those pools must be assigned a specific position before nodes can be assigned to rows.

This step uses aspects of spectral graph theory to calculate the optimal position of each container. The algorithm is based on the Laplacian matrix of the weighted graph representation between each pool and lane. This representation uses the sum of all incoming and outgoing connections for each lane as vectors. The Laplacian matrix is then used to derive eigenvectors and eigenvalues, which in turn are used to determine the optimal position of each container.

### [5. Assigning Rows to Nodes](/docs/concept/row_positioner.md)

After columns and containers are assigned, the nodes are assigned to rows. This iterative process calculates the optimal position of each node based on its predecessors, successors, and the relative positions of parent containers compared to the containers of its predecessors and successors.

With this process concluded, the logical placement of all elements is finished.

## Rendering Diagram

The second stage of the optimization process is the rendering of the diagram. This stage uses the logical placement of elements to calculate the exact position of each element in the diagram.

Unlike the first stage, the orchestration is done in the [`JsonBuilder`](../diagramforge/rendering/json_builder.py) class by invoking the `build_json()` method of the initialized instance.

### 6. Preparations & Cleanup

To ensure proper visualization in SPM, a quick process removes any boundary or coordinate information from the input data. This is necessary to prevent conflicts with the new element positions and to avoid graphical glitches.

### [7. Assign & Calculate Positions in Sub-canvases](/docs/concept/sub_canvas_positioning.md)

Diagrams in SPM use sub-canvases for nested elements. In other words, the origin of coordinates for each element begins at the top-left corner of the parent element with the coordinates (0,0). This step assigns and calculates the position of each element in its respective sub-canvas.

### [8. Conversion to Global Coordinates](/docs/concept/global_coordinates.md)

After the local positions of all elements are calculated, they are converted to global coordinates. This is necessary because local positions alone do not allow recalculations of elements beyond their parent container. The global coordinates are calculated by adding the local position of each element to the position of its parent container.

To allow the “shifting” of elements and the correct calculation of Sequence Flows, this step creates various structures to track the global positions of elements as well as their relative positions to one another.

### [9. Sequence Flow Positioning](/docs/concept/sequence_flow_positioning.md)

It is highly recommended to read the linked page for a detailed and visual explanation placing Sequence Flows.

In short, there are vertical and horizontal “corridors” between each column and row where Sequence Flows can be placed. These corridors consist of corridor lanes. One lane can contain multiple Sequence Flows as long as they do not overlap.

Each node with connections to other nodes is assigned four ports: North, East, South, and West. The N, E, and S ports serve outgoing connections, whereas the W port serves incoming connections.

Based on specific rules, each port is assigned a number of connections that are placed sequentially in a specific order. Depending on the relative position of the source and target nodes, the Sequence Flows are then placed in predefined corridors.

After all Sequence Flows are placed, labels of Gateways and Sequence Flows are positioned relative to their respective elements following a set of rules.

### 10. Finalizing & Output

The finalization step does the following:
- Removes any temporary structures created during the optimization process
- Converts the global coordinates of each element into local coordinates
- Adds the "shape dockers" to each Association (first and last docker with the half of the width and height of the source and target node respectively - mandatory for SPM)
- Converts the Pydantic model into JSON format

This JSON is then returned as the output of the optimization process and can be directly uploaded to SPM.