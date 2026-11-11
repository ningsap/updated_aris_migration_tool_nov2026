import sys
from threading import RLock
from typing import Dict, Optional, Set

from loguru import logger as _loguru_logger


class ChannelConfig:
    def __init__(self, name: str, use_console: bool, is_custom_file: bool):
        self.name = name
        self.enabled = True
        self.use_console = use_console
        self.is_custom_file = is_custom_file
        self.disabled_levels: Set[str] = set()


class LoggerFactory:
    _registry: Dict[str, ChannelConfig] = {}
    _registry_lock = RLock()
    _setup_done = False
    DEFAULT_CHANNEL_NAME = "System"

    @staticmethod
    def _patch_record(record):
        if "channel" not in record["extra"]:
            record["extra"]["channel"] = LoggerFactory.DEFAULT_CHANNEL_NAME

    @classmethod
    def _get_config(cls, channel_name: str) -> Optional[ChannelConfig]:
        return cls._registry.get(channel_name)

    @classmethod
    def _should_process(cls, record: Dict, config: ChannelConfig) -> bool:
        if not config.enabled:
            return False
        if record["level"].name in config.disabled_levels:
            return False
        return True

    # --- FILTERS ---

    @classmethod
    def _global_console_filter(cls, record):
        channel = record["extra"]["channel"]
        if channel == cls.DEFAULT_CHANNEL_NAME:
            return True
        config = cls._get_config(channel)
        if config is None:
            return True
        return config.use_console and cls._should_process(record, config)

    @classmethod
    def _shared_file_filter(cls, record):
        channel = record["extra"]["channel"]
        if channel == cls.DEFAULT_CHANNEL_NAME:
            return True
        config = cls._get_config(channel)
        if config is None:
            return True
        return (not config.is_custom_file) and cls._should_process(record, config)

    # --- SETUP ---

    @classmethod
    def setup(cls, default_log_file: str = "logs/shared_default.log"):
        if cls._setup_done:
            return

        _loguru_logger.remove()
        _loguru_logger.configure(patcher=cls._patch_record)

        console_fmt = (
            "<green>{time:HH:mm:ss}</green> | "
            "<magenta>{extra[channel]: <10}</magenta> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}:{function}:{line}</cyan> | "
            "<level>{message}</level>"
        )

        file_fmt = (
            "{time:YYYY-MM-DD HH:mm:ss} | {extra[channel]: <10} | {level: <8} | {name}:{function}:{line} | {message}"
        )

        # 1. Console Sink
        _loguru_logger.add(sys.stderr, format=console_fmt, filter=cls._global_console_filter, level="DEBUG")

        # 2. Shared File Sink
        _loguru_logger.add(
            default_log_file, format=file_fmt, filter=cls._shared_file_filter, rotation="10 MB", level="DEBUG"
        )

        cls._setup_done = True

    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None, console: bool = True):
        if not cls._setup_done:
            cls.setup()

        is_custom_file = log_file is not None

        with cls._registry_lock:
            if name not in cls._registry:
                cls._registry[name] = ChannelConfig(name, console, is_custom_file)
                if is_custom_file:
                    cls._add_custom_sink(name, log_file)
            else:
                cls._registry[name].use_console = console

        return LoggerWrapper(name)

    @classmethod
    def _add_custom_sink(cls, channel_name: str, file_path: str):
        def specific_filter(record):
            if record["extra"]["channel"] != channel_name:
                return False
            config = cls._get_config(channel_name)
            return cls._should_process(record, config)

        file_fmt = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"

        _loguru_logger.add(file_path, filter=specific_filter, format=file_fmt, rotation="10 MB")


class LoggerWrapper:
    """
    Wraps loguru logger to enforce context binding and depth correction.
    """

    def __init__(self, name: str):
        self.name = name
        # Bind the channel name
        self._proxy = _loguru_logger.bind(channel=name)

    # Configuration methods
    def enable(self):
        LoggerFactory._registry[self.name].enabled = True

    def disable(self):
        LoggerFactory._registry[self.name].enabled = False

    def disable_level(self, level: str):
        LoggerFactory._registry[self.name].disabled_levels.add(level.upper())

    def enable_level(self, level: str):
        LoggerFactory._registry[self.name].disabled_levels.discard(level.upper())

    # --- PROXY METHODS WITH DEPTH CORRECTION ---

    def info(self, message: str, *args, **kwargs):
        self._proxy.opt(depth=1).info(message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        self._proxy.opt(depth=1).debug(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._proxy.opt(depth=1).warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._proxy.opt(depth=1).error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._proxy.opt(depth=1).critical(message, *args, **kwargs)

    def success(self, message: str, *args, **kwargs):
        self._proxy.opt(depth=1).success(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        self._proxy.opt(depth=1).exception(message, *args, **kwargs)

    def log(self, level: str, message: str, *args, **kwargs):
        self._proxy.opt(depth=1).log(level, message, *args, **kwargs)


logger: LoggerWrapper = LoggerFactory.get_logger("Default")
