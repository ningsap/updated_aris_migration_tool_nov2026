import os
import sys
import inspect
from loguru import logger
from loguru._simple_sinks import StreamSink
from typing import Optional


logger.level("INFO", icon="\U0001F4AC")  # Fixes width issue with standard icon
logger.level("WARNING", icon="\U0001F4E3")  # Fixes width issue with standard icon
logger.level("CRITICAL", icon="\U0001F525")  # Fixes width issue with standard icon


default_format = "{level.icon} <green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
short_format = "{level.icon} <green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>"

LOG_TRACEBACK = True
EXIT_ON_ERROR_LOG = False


spm_logger = logger.bind(name="SPM")

stream_sink_set = False

for handler in spm_logger._core.handlers.values():
    if isinstance(handler._sink, StreamSink) and not stream_sink_set:
        spm_logger.remove(handler_id=handler._id)
        spm_logger.add(sys.stderr, format=default_format)
        stream_sink_set = True
    elif isinstance(handler._sink, StreamSink) and stream_sink_set:
        spm_logger.remove(handler_id=handler._id)


spm_logger.add(
    sink=os.path.join("logs", "SPM.log"),
    rotation=f"3000 KB",
    format=default_format,
    filter=lambda record: "SPM" == record["extra"].get("name")
)


def log_error(message: str, force_depth: Optional[int] = None, overruling_exit: Optional[bool] = None):
    """
    Logs an error message with optional traceback and exits the application under certain conditions.

    This function dynamically adjusts the logging depth to improve the accuracy of the source location in the logs,
    based on whether a specific depth is forced or if the caller is within an exception class. It supports logging
    full tracebacks for exceptions and can conditionally exit the application after logging, based on configuration
    or an explicit override parameter.

    Args:
        message (str): The error message to log.
        force_depth (int or None, optional): If specified, forces the logging system to use this value as the call stack depth,
                                enhancing the accuracy of the logged source location. Useful in complex logging scenarios. Defaults to None.
        overruling_exit (bool or None, optional): If provided, determines whether the function should exit the application
                                          after logging the error. True causes an exit; False does nothing. When None,
                                          the behavior defaults to the configuration specified in LOGGER_CONFIG. Defaults to None.
    """

    caller_class = inspect.stack()[1].frame.f_locals.get(
        "self", None).__class__

    depth = 2 if (force_depth is not None or issubclass(
        caller_class, Exception)) else 1

    logger_opt = logger.bind().opt(depth=depth)

    if LOG_TRACEBACK:
        logger_opt.exception(message)
    else:
        logger_opt.error(message)

    if overruling_exit != None:
        if overruling_exit:
            sys.exit()
    elif EXIT_ON_ERROR_LOG:
        sys.exit()


spm_logger.log_error = log_error
