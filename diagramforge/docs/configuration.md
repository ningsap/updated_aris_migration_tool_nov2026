# Configuration

The Diagram Forge can be configured by using the `FORGE_CONFIG` object that is instantiated in [CONFIG.py](../diagramforge/CONFIG.py). In case you want to use custom configs, import the `FORGE_CONFIG` object before running the Diagram Forge and modify it as needed.

### Example

```python
from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.diagramforge import DiagramForge

FORGE_CONFIG.LOG_DEBUG = True
```

## Required SPM frontend & workspace configurations:

> ⚠️ The following configurations are required for the SPM frontend to work properly. Please adjust them according to the version of the frontend and workspace you are using.

- `SPM_FRONTEND_VERSION`: The version of the current frontend, defaults to `18.9.2`. Please check the version of the frontend you are using and adjust this value accordingly.
- `SPM_DIAGRAM_SSEXTENSIONS`: Absolutely no idea what this is for, but it is required. Check a diagram in the target workspace for `ssextensions` at the top level of the diagram JSON. Defaults to 
```
["http://oryx-editor.org/stencilsets/extensions/bpmn2.0basicsubset#", "http://signavio.com/stencilsets/extensions/his#"]
```

## Available Diagram Forge configurations:

- `LOG_DEBUG`: Enable or disable debug logging messages. Default is `False`.
- `COLUMN_POSITIONING_MAX_ITERATIONS`: Maximum number of iterations for column positioning algorithm. Default is `300`.
- `ROW_POSITIONING_CROSSING_MINIMIZATION_MAX_ITERATIONS`: Maximum number of iterations for row positioning algorithm. Default is `10`.
- `ALLOW_RANDOM_NODE_AS_ROOT`: Allow a random node to be the root node of the diagram if it does not have any. Default is `False`.
- `VERTICAL_FLOWS_ONE_LANE_PER_FLOW`: If set to `True`, all vertical sequence flows will use separate passages. This ensures no overlaps of vertically aligned flows at the cost of a clean look. Default is `False`.
- `HORIZONTAL_FLOWS_ONE_LANE_PER_FLOW`: If set to `True`, all horizontal sequence flows will use separate passages. This ensures no overlaps of horizontally aligned flows at the cost of a clean look. Default is `False`.
- `ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS`: Decide whether all angles should be diagonals (`True`) or only the ones with conflicts or overlaps (`False`). Default is `False`.


> ⚠️ Please don't alter the `TOP_HORIZONTAL_CORRIDOR_LANE_START_Y_SAVE` variable. This keeps track of the row positioning algorithm starting above the first row of diagram element and should not be changed.