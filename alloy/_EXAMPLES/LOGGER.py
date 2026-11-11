from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import LoggerFactory, logger


def EXAMPLE_LOGGER():
    # Use the default logger instance
    logger.debug("This is a debug message")

    # Create a custom logger instance with custom file sink (file storage for logs)
    my_logger = LoggerFactory.get_logger("MyLogger", log_file="logs/my_logger.log")

    my_logger.debug("This is a debug message")
    my_logger.info("This is an info message")
    my_logger.success("This is a success message")
    my_logger.warning("This is a warning message")
    my_logger.critical("This is a critical message")
    my_logger.error("This is an error message")

    # Disabling and enabling logging
    my_logger.info("Disabling all logging")
    my_logger.disable()
    my_logger.debug(">>> This debug message should not appear")
    my_logger.success(">>> This success message should not appear")

    my_logger.enable()
    my_logger.info("Re-enabling logging")

    # Disabling specific log levels
    my_logger.debug("Disabling DEBUG level")
    my_logger.disable_level("DEBUG")
    my_logger.debug(">>> This debug message should not appear")
    my_logger.success("This success message should appear")

    my_logger.enable_level("DEBUG")
    my_logger.debug("Re-enabling DEBUG level")


EXAMPLE_LOGGER()
