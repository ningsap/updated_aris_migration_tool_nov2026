from diagramforge.exceptions.general import LogException


class DiagramInputInvalid(LogException):
    def __init__(self) -> None:
        super().__init__(
            "The input must be either a dictionary representation of the SPM JSON or a schema.shapes.Diagram model."
        )


class RootObjectNotDiagram(LogException):
    def __init__(self, root_object: str) -> None:
        super().__init__(
            f"The root object must be a of type Diagram from diagramforge.schema.shapes.Diagram. Instead got {type(root_object)}"
        )


class InvalidStencil(LogException):
    def __init__(self, stencil_id: str) -> None:
        super().__init__(f"Unsupported stencil ID: {stencil_id}")


class MissingStencil(LogException):
    def __init__(self) -> None:
        super().__init__("Stencil ID is missing in the data.")


class PydanticErrorOnCreatingShape(LogException):
    def __init__(self, shape_stencil: str, error: str) -> None:
        super().__init__(f"Error creating shape -  Stencil: {shape_stencil} | Error: {error}")
