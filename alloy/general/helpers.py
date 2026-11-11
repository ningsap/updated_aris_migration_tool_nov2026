import json
from functools import wraps
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from ARIS_Migration_Tool_SCB_Nov2026.alloy.configs.module_config import DEBUG
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger


def deprecated(message: str = None) -> Callable[..., Any]:
    """
    A decorator to mark functions, methods, or classes as deprecated.

    When a function, method, or class decorated with `@deprecated` is called or instantiated,
    a warning message will be logged using the `loguru` logger. The message will indicate that
    the function, method, or class is deprecated and suggest that it will be removed in a future version.

    Args:
        message (str, optional): An optional message to provide additional information
                                 or suggest an alternative function, method, or class.

    Returns:
        Callable: The original function, method, or class wrapped with a deprecation warning.
    """

    def decorator(obj: Callable[..., Any]) -> Callable[..., Any]:
        if isinstance(obj, type):
            orig_init = obj.__init__

            @wraps(orig_init)
            def wrapped_init(self, *args, **kwargs):
                full_message = f"[DEPRECATION NOTICE] The class {obj.__name__} is deprecated and will be removed in a future version."
                if message:
                    full_message += f" Details: {message}"

                logger.warning(full_message)
                orig_init(self, *args, **kwargs)

            obj.__init__ = wrapped_init
            return obj

        else:  # Assume it's a function or method

            @wraps(obj)
            def wrapper(*args, **kwargs) -> Any:
                full_message = (
                    f"[DEPRECATION NOTICE] {obj.__name__} is deprecated and will be removed in a future version."
                )
                if message:
                    full_message += f" Details: {message}"

                logger.warning(full_message)
                return obj(*args, **kwargs)

            return wrapper

    return decorator


def measure_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to measure the execution time of a function.

    This decorator logs the duration taken by the wrapped function to execute.
    It's useful for performance monitoring and debugging.

    Args:
        func (Callable[..., Any]): The function whose execution time is to be measured.

    Returns:
        Callable[..., Any]: A wrapper function that measures and logs the execution time of the given function.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = perf_counter()
        wrapper_return = func(*args, **kwargs)
        end_time = perf_counter()
        duration = end_time - start_time

        days = int(duration // 86400)
        hours = int((duration % 86400) // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = duration % 60

        duration_parts = []
        if days > 0:
            duration_parts.append(f"{days}d")
        if hours > 0 or days > 0:
            duration_parts.append(f"{hours}h")
        if minutes > 0 or hours > 0 or days > 0:
            duration_parts.append(f"{minutes}m")
        duration_parts.append(f"{seconds:.2f}s")

        formatted_duration = " ".join(duration_parts)
        logger.debug(f"Execution Time: {formatted_duration} of Function: {func.__name__}")

        return wrapper_return

    return wrapper


def print_json(data):
    """
    Prints a dictionary or list as a formatted JSON string.

    If the data is not a dictionary or a list, it prints the type of the data instead.

    Args:
        data (Union[dict, list]): The data to be printed in JSON format.
    """

    if isinstance(data, dict) or isinstance(data, list):
        print(json.dumps(data, indent=4))
    else:
        print(f"Data is no dict or list, it is {type(data)} instead")


def root() -> str:
    """
    Returns the root directory assuming that .venv is at the root of the project.

    Returns:
        Path: The root directory path.
    """

    # Check if the .venv directory exists
    if ".venv" in str(Path(__file__)):
        return str(Path(__file__)).split(".venv")[0]

    else:
        if DEBUG.WORK_ON_PACKAGE:
            return str(
                Path(__file__).parent.parent.parent
            )  # Makes only sense if the package is checked out and worked on directly

        raise FileNotFoundError(
            "The .venv directory was not found. Please ensure that the project is structured correctly."
        )


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
