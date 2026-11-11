from diagramforge.exceptions.general import LogException


class SourceToTargetRelativePositionException(LogException):
    def __init__(self, source_resource_id: str, target_resource_id: str) -> None:
        super().__init__(
            f"Relative position from source '{source_resource_id}' to target '{target_resource_id}' is could not be determined."
        )


class InvalidColumnDistance(LogException):
    def __init__(self, distance: int, source_resource_id: str, target_resource_id: str) -> None:
        super().__init__(
            f"Column distance <{distance}> from source '{source_resource_id}' to target '{target_resource_id}' is invalid."
        )


class RelativePositionCouldNotBeDetermined(LogException):
    def __init__(self, source_resource_id: str, target_resource_id: str) -> None:
        super().__init__(
            f"Relative position from source '{source_resource_id}' to target '{target_resource_id}' could not be determined."
        )
