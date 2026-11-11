from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Import this class to create you own models.
    """

    @declared_attr
    def __tablename__(cls):
        return cls.__name__


class DatabaseStatus(PyEnum):
    ACTIVE = "Active"
    ARCHIVED = "Archived"


class DatabaseMetadata(Base):
    __tablename__ = "database_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[DatabaseStatus] = mapped_column(SQLAlchemyEnum(DatabaseStatus), nullable=False)
    creation_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    archiving_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"DatabaseMetadata(id={self.id!r}, status={self.status!r}, "
            f"creation_timestamp={self.creation_timestamp!r}, archiving_timestamp={self.archiving_timestamp!r})"
        )
