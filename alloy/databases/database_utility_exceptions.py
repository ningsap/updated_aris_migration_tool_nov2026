from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger


class DatabaseUtilityConnectionError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class DatabaseUtilityRuntimeError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class DatabaseUnsupportedInitParam(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class DatabaseFactoryUnsupportedEngine(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class DatabaseUtilityNotInstantiated(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
