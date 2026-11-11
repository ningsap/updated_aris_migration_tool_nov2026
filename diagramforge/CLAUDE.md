# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DiagramForge is a Python package that optimizes BPMN diagram layouts. It ingests Signavio BPMN JSON, applies intelligent positioning algorithms, and outputs SPM-compatible JSON with improved readability.

## Development Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests -v

# Lint and format
pre-commit run --all-files
# Or manually:
uv run ruff check . --fix && uv run ruff format .

# Run local test script (configurable)
uv run python __RUN_LOCAL_TESTS.py
```

## Architecture

The main entry point is the `DiagramForge` class in `diagramforge/diagramforge.py`:

```python
from diagramforge.diagramforge import DiagramForge
diagram_forge = DiagramForge(json_or_model)
optimized_json = diagram_forge.to_spm_json()
```

**Processing Pipeline:**
1. **ModelConverter** (`conversion/`) - Validates JSON and converts to Pydantic models
2. **PreparationTool** (`transformation/preparation_tool.py`) - Builds NetworkX graph and mappings
3. **ColumnPositioner** (`transformation/column_positioner.py`) - BFS-based x-axis positioning with RuleBook heuristics
4. **ContainerLayoutManager** (`transformation/container_layout_manager.py`) - Pool/lane ordering using spectral layout
5. **RowPositioner** (`transformation/row_positioner.py`) - Y-axis positioning with crossing minimization
6. **JsonBuilder** (`rendering/json_builder.py`) - Final coordinate calculation and connection routing
   - **Sub-components:**
     - `NodePositioningManager` - Places nodes in lanes using grid coordinates
     - `ContainerPositioningManager` - Sizes pools/lanes based on contained nodes
     - `CoordinatesHandler` - Manages global ↔ local coordinate transforms
     - `GlobalGridLookup` (`flows/`) - Unified grid system merging lane grids
     - `SequenceFlowManager` (`flows/`) - Orchestrates connection routing
     - `FlowCorridorManager` (`flows/`) - Creates vertical/horizontal routing corridors
     - `PortAdapter`/`PortConnection` (`flows/`) - Sorts connections by direction (N/E/S/W)
     - `LabelPlacer` (`flows/`) - Places labels on sequence flows and gateways
   - **Processing flow:**
     1. Cleanup existing dockers/bounds
     2. Position nodes in lanes (NodePositioningManager)
     3. Position containers around nodes (ContainerPositioningManager)
     4. Create global coordinate system (GlobalGridLookup + CoordinatesHandler)
     5. Route connections through corridors (SequenceFlowManager)
     6. Place labels (LabelPlacer)
     7. Revert global → local coordinates
     8. Add shape dockers and wrap text

**Key Modules:**
- `schema/` - Pydantic models for BPMN shapes (Diagram, Pool, Lane, Task, Event, Gateway, etc.)
- `transformation/` - Graph algorithms for layout positioning
- `rendering/` - Coordinate calculation and sequence flow routing
- `helpers/STATICS.py` - Layout spacing constants
- `CONFIG.py` - Global configuration singleton (ConfigStore)

## Code Style

- Python 3.10-3.11 required
- Line length: 120 characters
- Ruff for linting/formatting
- PEP8 compliance
- Avoid shortcuts/workarounds - maintain clean, maintainable code

## Testing

Tests run via pytest. After running tests, transformed diagrams are output to `TESTS_UPLOAD_TO_SPM/` directory for **manual validation in SPM** (no automated visual validation exists).

Add new test diagrams by placing JSON files in `tests/data/`.

## Branch Strategy

- `main` - Protected, accepts PRs only from `dev`
- `dev` - Default development branch
- Fork the repository for client/project-specific changes instead of creating feature branches
