# Import necessary modules
from typing import Any, Dict, Type, Union

from diagramforge.exceptions.model_conversion import (
    DiagramInputInvalid,
    InvalidStencil,
    MissingStencil,
    PydanticErrorOnCreatingShape,
    RootObjectNotDiagram,
)
from diagramforge.schema.base import ShapeBase, Stencil
from diagramforge.schema.shapes import (
    Association,
    CollapsedPool,
    Diagram,
    Event,
    Gateway,
    Lane,
    Pool,
    Task,
    TextAnnotation,
)
from diagramforge.schema.stencils import (
    ArtifactStencil,
    AssociationStencil,
    ContainerStencil,
    EventStencil,
    GatewayStencil,
    TaskStencil,
)


class ModelConverter:
    """
    Converts Signavio JSON diagrams into Pydantic Diagram models.

    This class provides methods to parse JSON data and build Diagram models,
    as well as convert Diagram models back into JSON.
    """

    STENCIL_ID_TO_MODEL: Dict[str, Type[ShapeBase]] = {
        ContainerStencil.BPMNDiagram.value: Diagram,
        ContainerStencil.Pool.value: Pool,
        ContainerStencil.Lane.value: Lane,
        ContainerStencil.CollapsedPool.value: CollapsedPool,
        # Task stencils
        **{e.value: Task for e in TaskStencil},
        # Event stencils
        **{e.value: Event for e in EventStencil},
        # Gateway stencils
        **{g.value: Gateway for g in GatewayStencil},
        # Association stencils
        **{a.value: Association for a in AssociationStencil},
        # Artifact stencils
        ArtifactStencil.TEXT_ANNOTATION.value: TextAnnotation,
    }

    def convert_to_json(self, diagram: Diagram) -> Dict[str, Any]:
        """
        Converts the Diagram model into Signavio JSON format.

        Args:
            diagram (Diagram): A Pydantic Diagram instance.

        Returns:
            Dict[str, Any]: The diagram serialized into Signavio-compatible JSON.
        """
        return diagram.model_dump(by_alias=True, exclude_none=True)

    def convert_to_model(self, data: Dict[str, Any]) -> Diagram:
        """
        Converts Signavio JSON data into a Diagram model.

        Args:
            data (Dict[str, Any]): Signavio JSON data.

        Returns:
            Diagram: The constructed Diagram model.

        Raises:
            RootObjectNotDiagram: If the top-level shape is not a Diagram instance.
        """
        shape = self._parse_shape(data)
        if not isinstance(shape, Diagram):
            raise RootObjectNotDiagram(shape)
        shape.validate_structure()
        return shape

    def convert_and_validate_json_or_model(self, json_or_model: Union[dict, Diagram]) -> Diagram:
        """
        Converts and validates JSON or a Diagram model into a Diagram instance.

        Args:
            json_or_model (Union[dict, Diagram]): Either a Signavio JSON dict or a Diagram.

        Returns:
            Diagram: A valid Diagram instance.

        Raises:
            DiagramInputInvalid: If the input is neither a dict nor a Diagram.
        """
        if isinstance(json_or_model, dict):
            return self.convert_to_model(json_or_model)
        elif isinstance(json_or_model, Diagram):
            _ = json_or_model.validate_structure()
            return json_or_model
        else:
            raise DiagramInputInvalid()

    def _parse_shape(self, data: Dict[str, Any]) -> ShapeBase:
        """
        Recursively parses JSON data to create and return a ShapeBase instance.

        Args:
            data (Dict[str, Any]): The JSON data representing a shape.

        Returns:
            ShapeBase: An instance of ShapeBase or its subclass.

        Raises:
            MissingStencil: If the stencil ID is missing in the data.
            InvalidStencil: If the stencil ID is not supported.
        """
        stencil_id = data.get("stencil", {}).get("id")
        if not stencil_id:
            raise MissingStencil()

        model_class = self._get_model_class(stencil_id)
        if not model_class:
            raise InvalidStencil(stencil_id)

        model_data = {
            "resource_id": data.get("resourceId"),
            "stencil": Stencil(id=stencil_id),
            "properties": data.get("properties", {}),
            "bounds": data.get("bounds"),
            "outgoing": data.get("outgoing"),
            "target": data.get("target"),
            "dockers": data.get("dockers"),
            "formats": data.get("formats"),
            "layers": data.get("layers", []),
            "glossary_links": data.get("glossaryLinks", {}),
            "label_dirty_states": data.get("labelDirtyStates", {}),
        }

        # Only forward `labels` when present in the source JSON; otherwise let
        # the model class supply its own default (e.g. Diagram defaults to None
        # so the field is dropped, while ShapeBase defaults to []).
        if "labels" in data:
            model_data["labels"] = data["labels"]

        if stencil_id == ContainerStencil.BPMNDiagram.value:
            model_data["language"] = data.get("language")
            model_data["ssextensions"] = data.get("ssextensions", None)
            model_data["stencilset"] = data.get("stencilset", None)

        child_shapes_data = data.get("childShapes", [])
        child_shapes = []
        for child_data in child_shapes_data:
            child_shape = self._parse_shape(child_data)
            child_shapes.append(child_shape)
        if child_shapes:
            model_data["child_shapes"] = child_shapes

        try:
            shape = model_class(**model_data)
        except Exception as e:
            raise PydanticErrorOnCreatingShape(stencil_id, str(e))

        return shape

    def _get_model_class(self, stencil_id: str) -> Type[ShapeBase]:
        """
        Returns the ShapeBase subclass for the given stencil ID.

        Args:
            stencil_id (str): The stencil identifier.

        Returns:
            Type[ShapeBase]: The corresponding ShapeBase subclass, if available.
        """
        return self.STENCIL_ID_TO_MODEL.get(stencil_id)
