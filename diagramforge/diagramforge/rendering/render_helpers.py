from copy import deepcopy
from typing import Tuple

from diagramforge.helpers.STATICS import SPACE_CONVENTIONS as SC
from diagramforge.schema.base import Stencil
from diagramforge.schema.stencils import GatewayStencil, TaskStencil


def get_width_height_by_stencil(stencil: Stencil) -> Tuple[int, int]:
    """Returns the width and height of a shape based on its stencil.

    Args:
        stencil (Stencil): The stencil of the shape.

    Returns:
        Tuple[int, int]: The width and height of the shape.
    """

    stencil_id = stencil.id
    stencil_name = stencil.id.lower()

    if isinstance(stencil_id, TaskStencil):
        return deepcopy(SC.TASK_SIZE_TUPLE)
    elif isinstance(stencil_id, GatewayStencil):
        return deepcopy(SC.GATEWAY_SIZE_TUPLE)
    elif stencil_name.startswith("start") or stencil_name.startswith("intermediate"):
        return deepcopy(SC.START_INTERMEDIATE_EVENT_SIZE_TUPLE)
    elif stencil_name.startswith("end"):
        return deepcopy(SC.END_EVENT_SIZE_TUPLE)
    else:
        return deepcopy(SC.TASK_SIZE_TUPLE)


class AuxCoordX:
    """Auxiliar class to store x coordinate."""

    def __init__(
        self,
        x: float,
    ) -> None:
        self.x: float = x

    def __repr__(self) -> str:
        return f"AuxCoordX: {self.x}"


class AuxCoordY:
    """Auxiliar class to store y coordinate."""

    def __init__(
        self,
        y: float,
    ) -> None:
        self.y: float = y

    def __repr__(self) -> str:
        return f"AuxCoordY: {self.y}"
