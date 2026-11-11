from diagramforge.SETUP import forge_logger


class LogException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        forge_logger.error(self.message)

    def __str__(self) -> str:
        return self.message
