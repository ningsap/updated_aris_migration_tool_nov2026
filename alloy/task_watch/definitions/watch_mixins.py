from enum import Enum
from typing import Type, Union
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.models import Base


class Status(Enum):
    CREATED = "CREATED"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class DBWatchMixin():
    @declared_attr
    def __tablename__(cls):
        return f"TRACKER_{cls.__name__}"

    id: Mapped[str] = mapped_column(primary_key=True, nullable=False)
    status: Mapped[Status] = mapped_column(default=Status.CREATED)
    error_info: Mapped[str] = mapped_column(nullable=True)
    data: Mapped[str] = mapped_column(nullable=True)


@event.listens_for(DBWatchMixin, "before_insert", propagate=True)
def generate_id(mapper, connection, target):
    if target.id is None:
        target.id = str(uuid4())


class FileWatchMixin():
    @declared_attr
    def __tablename__(cls):
        return f"TRACKER_{cls.__name__}"

    id: Mapped[str] = mapped_column(primary_key=True, nullable=False)
    status: Mapped[Status] = mapped_column(default=Status.CREATED)
    error_info: Mapped[str] = mapped_column(nullable=True)
    relative_file_path: Mapped[str] = mapped_column(nullable=False)


@event.listens_for(FileWatchMixin, "before_insert", propagate=True)
def generate_id(mapper, connection, target):
    if target.id is None:
        target.id = str(uuid4())


WatchTableType = Union[
    Type[Base and DBWatchMixin],
    Type[Base and FileWatchMixin],
]
