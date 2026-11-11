from typing import Annotated, Optional, Union

import rich.pretty
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator
from pydantic.alias_generators import to_camel

from diagramforge.schema.stencils import (
    ArtifactStencil,
    AssociationStencil,
    ContainerStencil,
    EventStencil,
    GatewayStencil,
    TaskStencil,
)


class SignavioBaseModel(BaseModel):
    """
    Base class for all API data models.

    Adds automatic pretty printing to them.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def __repr__(self):
        """Returns a pretty-printed representation of the model."""
        return rich.pretty.pretty_repr(self)

    def validate_structure(self):
        """
        Placeholder method to be overridden by subclasses.

        This method can be implemented by subclasses to validate model structure.
        """
        pass


def parse_model(T, data):
    """
    Parses data into a Pydantic model.

    Args:
        T: The model type to parse the data into.
        data: The data to parse.

    Returns:
        The validated model of type T.
    """
    return TypeAdapter(T).validate_python(data)


def dump_model(T, data, **kwargs):
    """
    Dumps a Pydantic model to a dictionary with optional configuration.

    Args:
        T: The model type to dump.
        data: The model instance or dictionary data to dump.
        **kwargs: Additional key-value arguments passed to the TypeAdapter dump_python method.

    Returns:
        A dictionary representation of the model with aliases applied.
    """
    return TypeAdapter(T).dump_python(data, by_alias=True, **kwargs)


class Stencil(SignavioBaseModel):
    """
    Represents a BPMN stencil.

    Attributes:
        id (Union[ContainerStencil, TaskStencil, EventStencil, GatewayStencil, AssociationStencil]):
            The ID of the stencil, which determines the type of BPMN element.
    """

    id: Annotated[
        Union[ContainerStencil, TaskStencil, EventStencil, GatewayStencil, AssociationStencil, ArtifactStencil],
        Field(description="ID of the stencil"),
    ]


class Coordinates(SignavioBaseModel):
    """
    Represents x and y coordinates.

    Attributes:
        x (float): The x-coordinate value.
        y (float): The y-coordinate value.
    """

    x: float = 0
    y: float = 0

    @field_validator("x", "y", mode="before")
    def set_default_for_null(cls, v):
        """
        Sets the default value to 0 if x or y is null.

        Args:
            v: The value to validate.

        Returns:
            The original value or 0 if the original value is null.
        """
        if v is None or v == "null":
            return 0
        return v


class Bounds(SignavioBaseModel):
    """
    Encapsulates the upper-left and lower-right bounds of a shape.

    Attributes:
        upperLeft (Coordinates): Coordinates of the shape's upper-left corner.
        lowerRight (Coordinates): Coordinates of the shape's lower-right corner.
    """

    upperLeft: Coordinates = Field(default=Coordinates())
    lowerRight: Coordinates = Field(default=Coordinates())

    def __str__(self) -> str:
        """Returns a descriptive string containing the upper-left and lower-right coordinates."""
        return (
            f"UL (X;Y): ({self.upperLeft.x};{self.upperLeft.y}) | LR (X;Y): ({self.lowerRight.x};{self.lowerRight.y})"
        )


class Target(SignavioBaseModel):
    """
    Represents a target shape by resource ID.

    Attributes:
        resource_id (str): The ID referencing the target shape.
    """

    resource_id: str


class Properties(SignavioBaseModel):
    """
    Represents a collection of properties for a shape.

    Attributes:
        name (str): The display name of the shape.
        documentation (str): Additional documentation or description for the shape.
    """

    model_config = ConfigDict(
        alias_generator=None,
        extra="allow",
        validate_assignment=True,
    )

    name: str = ""
    documentation: str = ""

    def __getitem__(self, key):
        """
        Enables bracket-access for properties.

        Args:
            key (str): The property name.

        Returns:
            The value of the specified property, or None if it doesn't exist.
        """
        if key in self.model_fields:
            return getattr(self, key)
        else:
            return self.model_extra.get(key)

    def __setitem__(self, key, value):
        """
        Allows setting properties using bracket notation.

        Args:
            key (str): The property name.
            value: The value to set for the property.
        """
        if key in self.model_fields:
            setattr(self, key, value)
        else:
            self.model_extra[key] = value

    def get_all_names(self):
        """
        Retrieves all name-related properties.

        Returns:
            A dictionary containing the primary name and any localized names.
        """
        names = {}

        if self.name:
            names["name"] = self.name

        for key, value in self.model_extra.items():
            if key.startswith("name_"):
                names[key] = value
        return names


class AssociationLabel(SignavioBaseModel):
    """
    Represents label data for an association relationship.

    Attributes:
        ref (Optional[str]): Reference to the label property.
        orientation (Optional[str]): Orientation of the label. Accepts 'll' or 'lr'.
        distance (Optional[int]): Distance from the association line.
        x (Optional[float]): X coordinate position.
        y (Optional[float]): Y coordinate position.
        from_ (Optional[int]): Alias for 'from' coordinate.
        to (Optional[int]): 'To' coordinate.
        valign (Optional[str]): Vertical alignment of the label. Defaults to 'bottom'.
        align (Optional[str]): Horizontal alignment. Accepts 'left' or 'right'.
    """

    ref: Optional[str] = "text_name"
    orientation: Optional[str] = Field(default="ll", pattern="^(ul|ur|lr|ll)$")
    distance: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    from_: Optional[int] = Field(None, alias="from")
    to: Optional[int] = None
    valign: Optional[str] = "bottom"
    align: Optional[str] = Field(default="left", pattern="^(left|right)$")


class GatewayLabel(SignavioBaseModel):
    """
    Represents label data for a Gateway shape.

    Attributes:
        ref (str): The reference property for the gateway label.
        top (bool): Whether the label is displayed above the gateway.
        x (float): The x offset for the label.
        y (float): The y offset for the label.
        valign (str): The vertical alignment of the label.
        align (str): The horizontal alignment of the label.
    """

    ref: str = "text_name"
    top: bool = True
    x: float = 20
    y: float = -8
    valign: str = "bottom"
    align: str = "center"


class ShapeBase(SignavioBaseModel):
    """
    Base model for a BPMN shape.

    Attributes:
        resource_id (str): The unique identifier of the shape.
        outgoing (Optional[list[Target]]): A list of target shapes to which this shape is connected.
        formats (Optional[dict]): Custom format attributes for the shape.
        bounds (Optional[Bounds]): The coordinates bounding this shape.
        stencil (Stencil): The BPMN stencil describing the shape type.
        properties (Properties): The properties associated with this shape.
        target (Optional[Target]): Target shape reference for edges.
        dockers (Optional[list]): Docker points if this shape is an edge.
        layers (Optional[list]): Layers used by the shape.
        glossary_links (Optional[dict]): Links to glossary items.
        label_dirty_states (Optional[dict]): Indicates whether labels need refreshing.
        child_shapes (list[ShapeBase]): Child shapes nested under this shape.
    """

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    resource_id: str
    outgoing: Optional[list[Target]] = []
    formats: Optional[dict] = None
    bounds: Optional[Bounds] = Bounds()
    stencil: Stencil
    properties: Properties = Properties()
    target: Optional[Target] = None
    dockers: Optional[list] = []
    layers: Optional[list] = []
    glossary_links: Optional[dict] = {}
    label_dirty_states: Optional[dict] = {}
    labels: Optional[list] = []
    child_shapes: list["ShapeBase"] = []


ShapeBase.model_rebuild()
