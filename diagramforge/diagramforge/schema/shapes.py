from typing import Annotated, Optional, Union

from pydantic import ConfigDict, Field, model_validator

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.exceptions.model_validation import (
    CollapsedPoolNoChildShapesAllowed,
    DiagramDisallowedChildShape,
    PoolDisallowedChildShape,
)
from diagramforge.schema.base import AssociationLabel, Bounds, GatewayLabel, Properties, ShapeBase, Stencil
from diagramforge.schema.stencils import (
    ArtifactStencil,
    AssociationStencil,
    ContainerStencil,
    EventStencil,
    GatewayStencil,
    TaskStencil,
)


# Artifact shapes
class Artifact(ShapeBase):
    """Superclass for all artifacts in BPMN diagrams."""

    pass


class TextAnnotation(Artifact):
    """Represents a BPMN Text Annotation.

    Attributes:
        bounds (Bounds): The bounding box of the annotation (mandatory).
        properties (Properties): Properties specific to the text annotation.
        stencil (Stencil): Stencil object specifying that this is a TextAnnotation.
    """

    bounds: Bounds

    properties: Properties = Field(
        default_factory=lambda: {
            "textformat": "text/plain",
            "astahheight": 0,
            "bordercolor": "#000000",
            "astahwidth": 0,
            "alignment": "left",
        }
    )

    stencil: Annotated[Stencil, Field(description="Stencil must be TextAnnotation")] = Stencil(
        id=ArtifactStencil.TEXT_ANNOTATION
    )


# Diagram shapes


class Task(ShapeBase):
    """Represents a BPMN Task.

    Attributes:
        None
    """

    @model_validator(mode="after")
    def validate_stencil(self):
        if self.stencil.id not in [item.value for item in TaskStencil]:
            raise ValueError(f"Stencil ID must be one of TaskStencil values, got '{self.stencil.id}'")
        return self


class Event(ShapeBase):
    """Represents a BPMN Event.

    Attributes:
        None
    """

    @model_validator(mode="after")
    def validate_stencil(self):
        if self.stencil.id not in [item.value for item in EventStencil]:
            raise ValueError(f"Stencil ID must be one of EventStencil values, got '{self.stencil.id}'")
        return self


class Gateway(ShapeBase):
    """Represents a BPMN Gateway.

    Attributes:
        labels (list[GatewayLabel], optional): Optional gateway labels.
    """

    labels: Optional[list[GatewayLabel]] = []

    @model_validator(mode="after")
    def validate_stencil(self):
        if self.stencil.id not in [item.value for item in GatewayStencil]:
            raise ValueError(f"Stencil ID must be one of GatewayStencil values, got '{self.stencil.id}'")
        return self


class Association(ShapeBase):
    """Represents a BPMN Association.

    Attributes:
        labels (list[AssociationLabel], optional): Optional association labels.
    """

    labels: Optional[list[AssociationLabel]] = []

    @model_validator(mode="after")
    def validate_stencil(self):
        if self.stencil.id not in [item.value for item in AssociationStencil]:
            raise ValueError(f"Stencil ID must be one of AssociationStencil values, got '{self.stencil.id}'")
        return self


class Lane(ShapeBase):
    """Represents a BPMN Lane.

    Attributes:
        child_shapes (list[Union[Task, Event, Gateway, "Lane"]]): Allowed child shapes in a lane.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    stencil: Annotated[Stencil, Field(description="Stencil must be Lane")] = Stencil(id=ContainerStencil.Lane)

    child_shapes: list[Union[Task, Event, Gateway, "Lane", Artifact]] = []

    def validate_structure(self):
        for shape in self.child_shapes:
            if not isinstance(shape, (Task, Event, Gateway, Lane, Artifact)):
                raise ValueError("Lane child_shapes can only contain Task, Event, Gateway or Artifact", shape)
            shape.validate_structure()  # Recursively validate child shapes


Lane.model_rebuild()


class Pool(ShapeBase):
    """Represents a BPMN Pool.

    Attributes:
        child_shapes (list[Lane]): Lane shapes within this pool.
    """

    stencil: Annotated[Stencil, Field(description="Stencil must be Pool")] = Stencil(id=ContainerStencil.Pool)
    child_shapes: list[Lane] = []

    def validate_structure(self):
        for shape in self.child_shapes:
            if not isinstance(shape, Lane):
                raise PoolDisallowedChildShape(disallowed_child_shape=shape, parent_resource_id=self.resource_id)
            shape.validate_structure()  # Recursively validate child shapes


class CollapsedPool(ShapeBase):
    """Represents a BPMN Collapsed Pool.

    Attributes:
        child_shapes (list[Lane]): Lane shapes within this collapsed pool.
    """

    stencil: Annotated[Stencil, Field(description="Stencil must be CollapsedPool")] = Stencil(
        id=ContainerStencil.CollapsedPool
    )

    child_shapes: list = []

    def validate_structure(self):
        if self.child_shapes:
            raise CollapsedPoolNoChildShapesAllowed(resource_id=self.resource_id)
        # No further validation needed as no child shapes are allowed


class Diagram(ShapeBase):
    """
    Represents a BPMN diagram containing elements such as Pools and Associations.

    Attributes:
        resource_id (str):
            The resource identifier for the diagram. Defaults to "canvas".
        ssextensions (list):
            A list of Signavio stencil set extensions.
        stencilset (dict):
            Dictionary containing stencil set metadata (namespace, URL).
        stencil (Stencil):
            Stencil object specifying that this is a BPMNDiagram container.
        language (Optional[str]):
            Language code for localization, e.g., "de_de".
        properties (Properties):
            Properties specific to the diagram (e.g. targetnamespace, process type).
        child_shapes (List[Union[Pool, Association]]):
            A list of BPMN Pools or Associations that are part of this diagram.

        Validates that all shapes within the diagram are of supported types.

        Raises:
            DiagramDisallowedChildShape: If a child shape is not an instance of Pool or Association.
    """

    resource_id: str = "canvas"
    ssextensions: list = Field(default_factory=lambda: FORGE_CONFIG.SPM_DIAGRAM_SSEXTENSIONS)
    stencilset: dict = Field(
        default_factory=lambda: {
            "namespace": "http://b3mn.org/stencilset/bpmn2.0#",
            "url": f"/stencilsets/bpmn2.0/bpmn2.0.json?version={FORGE_CONFIG.SPM_FRONTEND_VERSION}",
        }
    )

    stencil: Annotated[Stencil, Field(description="Stencil must be BPMNDiagram")] = Stencil(
        id=ContainerStencil.BPMNDiagram
    )

    language: str = Field(description="Language code for localization, e.g., 'de_de'")

    properties: Properties
    # The BPMNDiagram root has no labels in Signavio's payload — set to None so
    # `model_dump(exclude_none=True)` drops the field. ShapeBase declares
    # `labels: Optional[list] = []` which would otherwise emit `"labels": []`.
    labels: Optional[list] = None
    child_shapes: list[Union[Pool, CollapsedPool, Association, Artifact]] = []

    def validate_structure(self):
        for shape in self.child_shapes:
            if not isinstance(shape, (Pool, CollapsedPool, Association, Artifact)):
                raise DiagramDisallowedChildShape(disallowed_child_shape=shape, parent_resource_id=self.resource_id)
            shape.validate_structure()
