from diagramforge.exceptions.general import LogException


class RootNodesNotFound(LogException):
    def __init__(self) -> None:
        super().__init__("No root nodes found in the graph and config disallows picking random node.")


class MaxColumnPositionLimitExceeded(LogException):
    def __init__(self) -> None:
        super().__init__("Max level limit exceeded. Check for cyclic dependencies in the graph.")
