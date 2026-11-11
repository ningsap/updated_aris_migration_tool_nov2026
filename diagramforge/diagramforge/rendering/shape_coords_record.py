from typing import List

from diagramforge.schema.base import Bounds, Coordinates, ShapeBase


class ShapeCoordsRecord:
    """
    Represents the coordinates and hierarchical relationships of a shape within the diagram.

    Attributes:
        shape_id (str): The unique identifier of the reference shape.
        local_bounds (Bounds): The local bounding box of the reference shape.
        reference_shape (ShapeBase): The reference shape object.
        global_bounds (Bounds): The global bounding box of the shape.
        parent_shapes (List[ShapeBase]): A list of parent shape objects.
        dockers (List[Coordinates]): A list of docking coordinates associated with the shape.
    """

    def __init__(self, reference_shape: ShapeBase, global_bounds: Bounds, parent_shapes: List[ShapeBase]) -> None:
        """
        Initializes a ShapeCoordsRecord instance.

        Args:
            reference_shape (ShapeBase): The reference shape object.
            global_bounds (Bounds): The global bounding box of the shape.
            parent_shapes (List[ShapeBase]): A list of parent shape objects.
        """

        self.shape_id = reference_shape.resource_id
        self.local_bounds = reference_shape.bounds

        self.reference_shape = reference_shape
        self.global_bounds = global_bounds
        self.parent_shapes = parent_shapes

        self.dockers: List[Coordinates] = []

    @property
    def global_center_x(self):
        """
        Calculates the global center x-coordinate of the shape.

        Returns:
            float: The x-coordinate of the global center.
        """

        return (self.global_bounds.lowerRight.x - self.global_bounds.upperLeft.x) / 2 + self.global_bounds.upperLeft.x

    @property
    def global_center_y(self):
        """
        Calculates the global center y-coordinate of the shape.

        Returns:
            float: The y-coordinate of the global center.
        """

        return (self.global_bounds.lowerRight.y - self.global_bounds.upperLeft.y) / 2 + self.global_bounds.upperLeft.y

    def __repr__(self):
        """
        Returns the official string representation of the ShapeCoordsRecord.

        Returns:
            str: A string representation including shape ID, type, global bounds, and parent shapes.
        """

        return f"ShapeCoordsRecord(shape_id={self.shape_id}, type={type(self.reference_shape).__class__.__name__} global_bounds={self.global_bounds}, parent_shapes={self.parent_shapes})"

    def __str__(self) -> str:
        """
        Returns the informal string representation of the ShapeCoordsRecord.

        Returns:
            str: A string representation including shape ID, global bounds, and parent shapes.
        """

        return f"ShapeCoordsRecord(shape_id={self.shape_id}, global_bounds={self.global_bounds}, parent_shapes={self.parent_shapes})"
