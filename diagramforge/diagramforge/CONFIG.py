class ConfigStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigStore, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        super().__init__()

    # --- SPM Frontend: Please adjust as needed beforehand ---

    SPM_FRONTEND_VERSION = "18.9.2"
    SPM_DIAGRAM_SSEXTENSIONS = [
        "http://oryx-editor.org/stencilsets/extensions/bpmn2.0basicsubset#",
        "http://signavio.com/stencilsets/extensions/his#",
    ]

    # --- DiagramForge Configs ---

    # Enable or disable debug logging messages
    LOG_DEBUG = False

    # Maximum number of iterations for column positioning algorithm. If the diagram should have more than 300 columns, increase this value.
    COLUMN_POSITIONING_MAX_ITERATIONS = 300

    # Maximum number of iterations for row positioning algorithm. If the connections between nodes are not too wild, 10 iterations should be enough.
    ROW_POSITIONING_CROSSING_MINIMIZATION_MAX_ITERATIONS = 10

    # Allow a random node to be the root node of the diagram if it does not have any. If set to False and there is no root node, an error will be raised.
    ALLOW_RANDOM_NODE_AS_ROOT = False

    # Vertical sequence flows usually share the same X coordinate when traveling up or down and not crossing each other. If this is set to True, all vertical sequence flows will use separate passages.
    VERTICAL_FLOWS_ONE_LANE_PER_FLOW = False

    # Horizontal sequence flows usually share the same Y coordinate when traveling left or right and not crossing each other. If this is set to True, all horizontal sequence flows will use separate passages.
    HORIZONTAL_FLOWS_ONE_LANE_PER_FLOW = False

    # Sequence flows will use diagonals to vislualize their flow. With this you can decide whether all angels should be diagonals (True) or only the ones with conflicts or overlaps (False).
    ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS = False

    # >>> DO NOT CHANGE <<< This keeps track of the sequence flow corridor above the first row of nodes in the diagram.
    TOP_HORIZONTAL_CORRIDOR_LANE_START_Y_SAVE: float = 0.0

    # >>> DO NOT CHANGE <<< This keeps track of the sequence flow corridor left of the first column of nodes in the diagram.
    LEFT_VERTICAL_CORRIDOR_LANE_START_X_SAVE: float = 0.0


FORGE_CONFIG = ConfigStore()
