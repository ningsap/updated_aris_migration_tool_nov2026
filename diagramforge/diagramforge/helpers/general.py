import json
import re
from enum import Enum


class TrueValueEnum(Enum):
    def __get__(self, *args, **kwargs):
        return self.value


def all_elements_in(a, b):
    """
    Checks if all elements of list 'a' are in list 'b'.

    This function is useful for verifying if one collection is a subset of another.

    Args:
        a (Iterable): The first collection of elements.
        b (Iterable): The second collection of elements.

    Returns:
        bool: True if all elements of 'a' are in 'b', False otherwise.
    """

    set_b = set(b)
    return all(elem in set_b for elem in a)


def any_element_in(a, b):
    """Checks if any element of list 'a' is in list 'b'.

    This function is useful for checking the intersection of two collections.

    Args:
        a (Iterable): The first collection of elements.
        b (Iterable): The second collection of elements.

    Returns:
        bool: True if any element of 'a' is in 'b', False otherwise.
    """

    set_b = set(b)
    return any(elem in set_b for elem in a)


def defaultdict_to_json(d):
    """
    Converts a defaultdict to a JSON-serializable dictionary.

    Args:
        d (defaultdict): The defaultdict to convert.

    Returns:
        dict: A JSON-serializable dictionary.
    """

    return json.loads(json.dumps(d))


def wrap_text(text: str, max_width_px: int = 150, char_width: int = 6) -> str:
    """
    Wraps text to fit within max_width_px, breaking only at spaces or after hyphens/slashes.
    """
    max_chars = max_width_px // char_width
    lines = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        line = ""
        for word in para.split(" "):
            segments = [word] if len(word) <= max_chars else re.split(r"([-/])", word)
            for seg in segments:
                if not seg:
                    continue
                if line:
                    if seg in "-/":
                        sep, avail = "", max_chars - len(line)
                    else:
                        sep, avail = " ", max_chars - len(line) - 1
                else:
                    sep, avail = "", max_chars

                if len(seg) <= avail:
                    line += sep + seg
                else:
                    if line:
                        lines.append(line)
                    line = seg
        if line:
            lines.append(line)
    return "\n".join(lines)
