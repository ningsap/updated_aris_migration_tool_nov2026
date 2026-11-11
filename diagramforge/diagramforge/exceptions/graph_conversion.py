from diagramforge.exceptions.general import LogException


class ResourceIdNotUnique(LogException):
    def __init__(self, resource_id: str) -> None:
        super().__init__(f"Resource ID '{resource_id}' is not unique.")


class NotConnectedSequenceFlowsRemain(LogException):
    def __init__(self, sequence_flow_ids: str) -> None:
        super().__init__(f"Sequence flows with IDs '{sequence_flow_ids}' are not connected to any node.")


class UnknownSequenceFlowTarget(LogException):
    def __init__(self, sequence_flow_id: str, target_id: str) -> None:
        super().__init__(f"Sequence flow with ID '{sequence_flow_id}' has an unknown target ID '{target_id}'.")


class ShapeNotInLane(LogException):
    def __init__(self, resource_id: str) -> None:
        super().__init__(f"Shape with resource ID '{resource_id}' is not in a lane.")


class LaneNotInPool(LogException):
    def __init__(self, resource_id: str) -> None:
        super().__init__(f"Lane with resource ID '{resource_id}' is not in a pool.")
