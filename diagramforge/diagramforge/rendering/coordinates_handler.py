from collections import defaultdict
from copy import deepcopy
from typing import Dict, List, Union

from diagramforge.rendering.render_helpers import AuxCoordX, AuxCoordY
from diagramforge.rendering.shape_coords_record import ShapeCoordsRecord
from diagramforge.schema.base import Bounds, Coordinates, ShapeBase
from diagramforge.schema.shapes import Artifact, Association, CollapsedPool, Diagram, Lane, Pool
from diagramforge.SETUP import forge_logger


class CoordinatesHandler:
    """CoordinatesHandler class.

    This class is responsible for managing all diagram coordinates. It can shift elements
    on the x or y axis by a certain amount beyond a threshold. All changes are made in place
    within the Diagram object.
    """

    def __init__(
        self,
        diagram: Diagram,
        resource_id_to_shape_mapping: Dict[str, ShapeBase],
    ) -> None:
        """Initializes the CoordinatesHandler with a diagram and mappings.

        Args:
            diagram (Diagram): The Diagram object to be manipulated.
            resource_id_to_shape_mapping (Dict[str, ShapeBase]): A dictionary mapping
                resource IDs to Shape objects.
        """
        self.diagram = diagram
        self.resource_id_to_shape_mapping = resource_id_to_shape_mapping

        # Cross-methodical class instance variables in order of usage
        self.id_to_parent_shapes_ids_list_mapping: Dict[str, List[ShapeBase]] = None
        self.shape_coords_record_by_resource_id: Dict[str, ShapeCoordsRecord] = None

        self.additional_coords_to_shift: list[Coordinates] = []
        self.additional_x_to_shift: list[AuxCoordX] = []
        self.additional_y_to_shift: list[AuxCoordY] = []

        # Preparing the global coords conversion
        self.__create_id_to_parent_shapes_list_mapping()

        # Create a list of all shapes in the diagram with references to their actual coordinates
        # as well as the newly calculated global coordinates
        self.__compute_global_shape_bounds()

    def __create_id_to_parent_shapes_list_mapping(self) -> None:
        """Creates a mapping of each shape's resource ID to a list of its parent shapes.

        This method populates the self.id_to_parent_shapes_list_mapping dictionary using a
        depth-first traversal of the diagram hierarchy.
        """
        forge_logger.debug("Creating ID to parent shapes list mapping")

        self.id_to_parent_shapes_ids_list_mapping: Dict[str, List[Bounds]] = defaultdict(list)

        def iter_children(parent_shapes: list, shape: ShapeBase) -> None:
            """Recursively collects parent shapes for each shape in the hierarchy.
            For performance reasons, this method is only collecting the bounds of the parent shapes.

            Args:
                parent_shapes (list): A list of parent shapes collected so far.
                shape (ShapeBase): The current shape being processed.
            """
            new_parent_shapes = []

            if shape is None:
                return

            elif isinstance(shape, Diagram):
                pass

            else:
                forge_logger.debug(f"Collecting parent shapes for shape {shape.resource_id}")

                self.id_to_parent_shapes_ids_list_mapping[shape.resource_id] = deepcopy(parent_shapes)

                new_parent_shapes = parent_shapes + [shape.resource_id]

            for child in shape.child_shapes:
                iter_children(new_parent_shapes, child)

        iter_children([], self.diagram)

    def __compute_global_shape_bounds(self) -> None:
        """Computes the global bounds for each shape based on the hierarchy of parent shapes.

        This method updates self.shape_coords_record_by_resource_id with ShapeCoordsRecord instances
        that store local and global bounds for each shape.
        """
        self.shape_coords_record_by_resource_id = {}

        for shape_id, parent_shape_ids in self.id_to_parent_shapes_ids_list_mapping.items():
            local_bounds = self.resource_id_to_shape_mapping[shape_id].bounds
            global_bounds = deepcopy(local_bounds)

            for parent_shape_id in parent_shape_ids:
                if isinstance(parent_shape_id, Diagram):
                    continue

                current_parent_shape = self.resource_id_to_shape_mapping[parent_shape_id]

                global_bounds.lowerRight.x += current_parent_shape.bounds.upperLeft.x
                global_bounds.lowerRight.y += current_parent_shape.bounds.upperLeft.y
                global_bounds.upperLeft.x += current_parent_shape.bounds.upperLeft.x
                global_bounds.upperLeft.y += current_parent_shape.bounds.upperLeft.y

            shape_coords_record: ShapeCoordsRecord = ShapeCoordsRecord(
                reference_shape=self.resource_id_to_shape_mapping[shape_id],
                global_bounds=global_bounds,
                parent_shapes=parent_shape_ids,
            )

            forge_logger.debug(f"Shape {shape_id} has global bounds {global_bounds} | local bounds {local_bounds}")

            if isinstance(self.resource_id_to_shape_mapping[shape_id], Association):
                shape_coords_record.dockers = self.resource_id_to_shape_mapping[shape_id].dockers

            self.shape_coords_record_by_resource_id[shape_id] = shape_coords_record

    def revert_global_to_local_coords(self) -> None:
        """Reverts the global coordinates back to local coordinates for each shape.

        All global coordinates stored in shape_coords_record_by_resource_id are recalculated
        to local coordinates using the hierarchy of parent shapes.
        """
        for shape_entry in self.shape_coords_record_by_resource_id.values():
            new_local_bounds = Bounds()
            subtract_x = 0
            subtract_y = 0

            if isinstance(shape_entry.reference_shape, Association):
                # Associations do not have local bounds, so we skip them
                continue

            for parent_shape_id in shape_entry.parent_shapes:
                if isinstance(parent_shape_id, Diagram):
                    continue

                if isinstance(parent_shape_id, Association):
                    continue

                subtract_x += self.shape_coords_record_by_resource_id[
                    parent_shape_id
                ].reference_shape.bounds.upperLeft.x
                subtract_y += self.shape_coords_record_by_resource_id[
                    parent_shape_id
                ].reference_shape.bounds.upperLeft.y

            new_local_bounds.upperLeft.x = shape_entry.global_bounds.upperLeft.x - subtract_x
            new_local_bounds.upperLeft.y = shape_entry.global_bounds.upperLeft.y - subtract_y
            new_local_bounds.lowerRight.x = shape_entry.global_bounds.lowerRight.x - subtract_x
            new_local_bounds.lowerRight.y = shape_entry.global_bounds.lowerRight.y - subtract_y

            shape_entry.reference_shape.bounds = new_local_bounds

            forge_logger.debug(
                f"Reverting shape {shape_entry.reference_shape.resource_id} to local bounds {new_local_bounds}"
            )
        pass

    def shift_elements(
        self, axis: str, threshold: Union[int, float], shift_amount: Union[int, float], include_threshold: bool = False
    ) -> None:
        """Shifts elements on the specified axis by a given amount if they exceed a threshold.

        Args:
            axis (str): The axis to shift the elements on. Can be either 'x' or 'y'.
            threshold (Union[int, float]): The threshold beyond which the elements will be shifted.
            shift_amount (Union[int, float]): The amount by which the elements will be shifted.
            include_threshold (bool, optional): Whether to include the threshold itself. Defaults to False.
        """
        forge_logger.debug(f"Shifting elements on axis {axis} beyond threshold {threshold} by {shift_amount}")

        if include_threshold:
            threshold -= 0.1

        # Enlarge canvas
        self.diagram.bounds.lowerRight.y += shift_amount
        self.diagram.bounds.lowerRight.x += shift_amount

        for shape_entry in self.shape_coords_record_by_resource_id.values():
            if axis == "x":
                if isinstance(shape_entry.reference_shape, (Pool, Lane, CollapsedPool)):
                    if shape_entry.global_bounds.upperLeft.x > threshold:
                        shape_entry.global_bounds.upperLeft.x += shift_amount
                    if shape_entry.global_bounds.lowerRight.x > threshold:
                        shape_entry.global_bounds.lowerRight.x += shift_amount
                elif not isinstance(shape_entry.reference_shape, Artifact):
                    if isinstance(shape_entry.reference_shape, Association):
                        for association_label in shape_entry.reference_shape.labels:
                            if association_label.x > threshold:
                                association_label.x += shift_amount
                        for docker in shape_entry.reference_shape.dockers:
                            if docker.x > threshold:
                                docker.x += shift_amount
                    else:
                        if (
                            shape_entry.global_bounds.upperLeft.x > threshold
                            and shape_entry.global_bounds.lowerRight.x > threshold
                        ):
                            shape_entry.global_bounds.upperLeft.x += shift_amount
                            shape_entry.global_bounds.lowerRight.x += shift_amount
            elif axis == "y":
                if isinstance(shape_entry.reference_shape, (Pool, Lane, CollapsedPool)):
                    if shape_entry.global_bounds.upperLeft.y > threshold:
                        shape_entry.global_bounds.upperLeft.y += shift_amount
                    if shape_entry.global_bounds.lowerRight.y > threshold:
                        shape_entry.global_bounds.lowerRight.y += shift_amount
                elif not isinstance(shape_entry.reference_shape, Artifact):
                    if isinstance(shape_entry.reference_shape, Association):
                        for association_label in shape_entry.reference_shape.labels:
                            if association_label.y > threshold:
                                association_label.y += shift_amount
                        for docker in shape_entry.reference_shape.dockers:
                            if docker.y > threshold:
                                docker.y += shift_amount
                                pass
                    else:
                        if (
                            shape_entry.global_bounds.upperLeft.y > threshold
                            and shape_entry.global_bounds.lowerRight.y > threshold
                        ):
                            shape_entry.global_bounds.upperLeft.y += shift_amount
                            shape_entry.global_bounds.lowerRight.y += shift_amount

        # Additional coords to shift
        if axis == "x":
            if self.additional_coords_to_shift:
                for coords in self.additional_coords_to_shift:
                    if coords.x > threshold:
                        coords.x += shift_amount
            if self.additional_x_to_shift:
                for aux in self.additional_x_to_shift:
                    if aux.x > threshold:
                        aux.x += shift_amount
        elif axis == "y":
            if self.additional_coords_to_shift:
                for coords in self.additional_coords_to_shift:
                    if coords.y > threshold:
                        coords.y += shift_amount
            if self.additional_y_to_shift:
                for aux in self.additional_y_to_shift:
                    if aux.y > threshold:
                        aux.y += shift_amount
        pass

    def add_additional_coords_to_shift(self, coords: Coordinates) -> None:
        """Adds Coordinates objects to the list of additional coordinates to shift.

        Args:
            coords (Coordinates): The coordinates to be shifted.
        """
        self.additional_coords_to_shift.append(coords)

    def add_additional_x_to_shift(self, x: float) -> None:
        """Adds an AuxCoordX or float value to the list of additional x coordinates to shift.

        Args:
            x (float): The x-coordinate value.
        """
        self.additional_x_to_shift.append(x)

    def add_additional_y_to_shift(self, y: float) -> None:
        """Adds an AuxCoordY or float value to the list of additional y coordinates to shift.

        Args:
            y (float): The y-coordinate value.
        """
        self.additional_y_to_shift.append(y)
