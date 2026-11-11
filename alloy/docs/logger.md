# ~~Logger Utility (module link)~~

# ⚠️ DEPRECATION NOTICE ⚠️
> This logger module is deprecated and will be removed in future versions. Please use the `alloy.logging.logger_factory` module instead (see [docs](../docs/logger_factory.md)).
<hr>

This logger utility provides a simple approach to using the [loguru package](https://github.com/Delgan/loguru) logger object. The loguru package is a more user-friendly and powerful logging package than the built-in logging module. Its main benefit is that loguru abstracts a lot of the headaches that one would have with the standard implementation.

> ~~Please see the the usage example for a quick start guide on how to use the logger.~~

Mainly, you can choose between one of two ways to use the logger:

### 1. Use the standard instance `logger`

If you don't have any special requirements for the logger, you can simply import the `logger` instance from the `LoggerFactory` class and use it as you would with the standard logging module.

```python
from alloy.logging.logger_utility import logger
```

This is an instance created by the `LoggerUtility` class with the default settings. It logs to the console and to a file in the `logs` directory. The log file is named `alloy.log`.

### 2. Create a custom logger instance

If you need to customize the logger, you can create a custom logger instance using the `LoggerUtility` class. 

```python
from alloy.logging.logger_factory import LoggerFactory
my_logger = LoggerFactory.get_logger("MyLogger", log_file="logs/my_logger.log")
```

The name that is passed to the `LoggerUtility` class is the name of the logger which will be displayed in the log messages.

With a custom logger instance, you can specify whether to add a file handler (`LoggerUtility.add_file_sink()`) along with parameters like file name, format, rotation, etc. Please see the in-code documentation for more information.

Either way, the logger supports the following log levels:
- `debug`
- `info`
- `warning`
- `error`
- `critical`
- `success`

An added functionality is that you can enable and disable certain log levels on the fly using the `LoggerUtility.enable_level()` and `LoggerUtility.disable_level()` methods respectively. You have to pass the log level as a string to these methods:

```python
my_logger.enable_level("debug")
my_logger.disable_level("info")
```

By default, all log levels are enabled.