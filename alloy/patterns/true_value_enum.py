from enum import Enum


class TrueValueEnum(Enum):
    def __get__(self, *args, **kwargs):
        return self.value
