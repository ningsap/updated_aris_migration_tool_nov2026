import os
import sys
from threading import Lock
from types import MethodType
from typing import Any, Dict, Optional

from loguru import logger as default_logger

from ARIS_Migration_Tool_SCB_Nov2026.alloy.general.helpers import deprecated


@deprecated("Use LoggerFactory in alloy.logging.logger_factory instead.")
class LoggerUtility:
    """A configurable logging utility built on top of Loguru with enhanced features.

    This class provides multiple independent loggers with shared console output,
    individual file logging, enable/disable functionality, and per-level control.
    All instances share a single console sink while maintaining separate file sinks.

    Attributes:
        _registry (Dict[str, LoggerUtility]): Class-level registry of all logger instances
        _registry_lock (Lock): Thread lock for registry operations
        _console_sink_id (Optional[int]): Shared console sink ID for all instances

    Example:
        >>> db_logger = LoggerUtility("database")
        >>> db_logger.disable_level("DEBUG")
        >>> db_logger.debug("This won't be logged")  # No output
        >>> db_logger.info("Connection established")  # Logs normally
    """

    _registry: Dict[str, "LoggerUtility"] = {}
    _registry_lock = Lock()
    _console_sink_id: Optional[int] = None

    def __init__(self, name: str, console_format: Optional[str] = None, add_file_sink: bool = True):
        self.name = name
        self.enabled = True
        self.disabled_levels = set()  # Track disabled log levels
        self._file_sink_ids = []

        with LoggerUtility._registry_lock:
            if name in LoggerUtility._registry:
                raise ValueError(f"Logger with name '{name}' already exists")
            LoggerUtility._registry[name] = self

        self._setup_console_sink(console_format)

        if add_file_sink:
            self.add_file_sink(os.path.join("logs", f"{name}.log"))

    def _setup_console_sink(self, console_format: Optional[str]):
        """Initialize the shared console sink for all logger instances.

        Args:
            console_format: Format string for console output. If None, uses default format.

        Note:
            Removes Loguru's default sink (ID 0) to prevent duplicate log messages
            in the console. This is only executed by the first created instance.
        """
        with LoggerUtility._registry_lock:
            if LoggerUtility._console_sink_id is not None:
                return

            # Remove default Loguru sink to prevent duplication
            try:
                default_logger.remove(0)
            except ValueError:
                pass  # Already removed

            format_str = console_format or (
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<magenta>{extra[custom_logger_name]}</magenta> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}:{function}:{line}</cyan> | "
                "<level>{message}</level>"
            )

            LoggerUtility._console_sink_id = default_logger.add(
                sys.stdout,
                filter=self._console_filter,
                format=format_str,
                catch=True,
            )

    @classmethod
    def _console_filter(cls, record: Dict[str, Any]) -> bool:
        """Filter function for the shared console sink.

        Args:
            record: Loguru's log record dictionary

        Returns:
            bool: True if the log should be emitted, False otherwise

        Note:
            Filters records based on two conditions:
            1. The record must have a 'custom_logger_name' in its extra dict
            2. The corresponding logger instance must be enabled in the registry
        """
        with cls._registry_lock:
            logger_name = record["extra"].get("custom_logger_name")
            if logger_name is None:
                return False

            logger_instance = cls._registry.get(logger_name)
            if logger_instance is None:
                return False

            return logger_instance.enabled

    def add_file_sink(
        self,
        file_path: Optional[str] = "logs",
        format: Optional[str] = None,
        rotation: Optional[str] = "5 MB",
        level: str = "DEBUG",
        filter: Optional[MethodType] = None,
        **kwargs: Any,
    ) -> int:
        """Add a file sink with automatic 'logs' directory handling.

        Args:
            file_path: Path to the log file. Will be placed in 'logs' directory if not present
            format: Format string for file output. Uses default format if None
            rotation: Rotation condition (e.g., "100 MB", "1 day")
            level: Minimum logging level
            filter: Custom filter function. Uses instance-specific filter if None
            **kwargs: Additional arguments for Loguru's add() method

        Returns:
            int: The sink ID for later reference

        Note:
            The created sink will only receive messages from this logger instance.
        """
        default_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<magenta>{extra[custom_logger_name]}</magenta> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}:{function}:{line}</cyan> | "
            "<level>{message}</level>"
        )

        sink_id = default_logger.add(
            file_path,
            format=format or default_format,
            rotation=rotation,
            level=level,
            filter=self._create_file_filter() if filter is None else filter,
            **kwargs,
        )
        self._file_sink_ids.append(sink_id)
        return sink_id

    def _create_file_filter(self) -> MethodType:
        """Create an instance-specific filter for file sinks.

        Returns:
            MethodType: Filter function that checks both logger name and enabled state
        """

        def file_filter(record: Dict[str, Any]) -> bool:
            return record["extra"].get("custom_logger_name") == self.name and self.enabled

        return file_filter

    def log(self, level: str, message: str, **kwargs: Any) -> None:
        """Base logging method with enabled state and level check."""
        if not self.enabled:
            return
        level_upper = level.upper()
        if level_upper in self.disabled_levels:
            return
        default_logger.bind(custom_logger_name=self.name).opt(depth=2).log(level, message, **kwargs)

    def disable_level(self, level: str) -> None:
        """Disable logging for the specified level."""
        self.disabled_levels.add(level.upper())

    def enable_level(self, level: str) -> None:
        """Enable logging for the specified level."""
        self.disabled_levels.discard(level.upper())

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log DEBUG level message."""
        self.log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log INFO level message."""
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log WARNING level message."""
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log ERROR level message."""
        self.log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log CRITICAL level message."""
        self.log("CRITICAL", message, **kwargs)

    def success(self, message: str, **kwargs: Any) -> None:
        """Log SUCCESS level message."""
        self.log("SUCCESS", message, **kwargs)

    def disable(self) -> None:
        """Disable all logging output for this instance."""
        self.enabled = False

    def enable(self) -> None:
        """Enable logging output for this instance."""
        self.enabled = True

    def remove_file_sinks(self) -> None:
        """Remove all file sinks associated with this instance."""
        for sink_id in self._file_sink_ids:
            try:
                default_logger.remove(sink_id)
            except ValueError:
                pass
        self._file_sink_ids.clear()

    @classmethod
    def remove_console_sink(cls) -> None:
        """Remove the shared console sink from Loguru."""
        if cls._console_sink_id is not None:
            try:
                default_logger.remove(cls._console_sink_id)
                cls._console_sink_id = None
            except ValueError:
                pass

    def __del__(self):
        """Cleanup handler for instance destruction."""
        self.remove_file_sinks()
        with LoggerUtility._registry_lock:
            if self.name in LoggerUtility._registry:
                del LoggerUtility._registry[self.name]
