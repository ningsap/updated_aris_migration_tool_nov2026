# Logger Factory ([module link](../alloy/logging/logger_factory.py))

The logger factory is a new implementation of the previous logger utility and provides a simple approach to using the [loguru package](https://github.com/Delgan/loguru) logger object. The loguru package is a more user-friendly and powerful logging package than the built-in logging module. Its main benefit is that loguru abstracts a lot of the headaches that one would have with the standard implementation.


> Please see the the [usage example](../alloy/_EXAMPLES/LOGGER.py) for a quick start guide on how to use the logger.

Mainly, you can choose between one of two ways to use the logger:

### 1. Use the standard instance `logger`

If you don't have any special requirements for the logger, you can simply import the `logger` instance from the `LoggerWrapper` class returned by `LoggerFactory.get_logger()` and use it as you would with the standard logging module.

```python
from alloy.logging.logger_factory import logger
```

This is an instance created by the `LoggerFactory` class with the default settings. It logs to the console and to a file in the `logs/shared_default.log` directory. Other logger instances that are not customized will also log to this file.

### 2. Create a custom logger instance

If you need to customize the logger, you can create a custom logger instance using the `LoggerFactory` class. 
```python
from alloy.logging.logger_factory import LoggerFactory
my_logger = LoggerFactory.get_logger(name="My amazing logger!", log_file="logs/my_logger.log")
```

The name that is passed to the `LoggerFactory` class is the name of the logger which will be displayed in the log messages.

With a custom logger instance, you can specify another log file.

Either way, the logger supports the following log levels:
- `debug`
- `info`
- `warning`
- `error`
- `critical`
- `success`

An added functionality is that you can enable and disable certain log levels on the fly using the `LoggerWrapper.enable_level()` and `LoggerWrapper.disable_level()` methods respectively. You have to pass the log level as a string to these methods:

```python
my_logger.enable_level("debug")
my_logger.disable_level("info")
```

By default, all log levels are enabled.