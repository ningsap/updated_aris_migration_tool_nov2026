from alloy.databases.models import Base
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from alloy.task_watch.definitions.watch_mixins import FileWatchMixin, DBWatchMixin
from sqlalchemy import Column, Integer, String, Boolean


class DictionaryEntries(Base, FileWatchMixin):
    @declared_attr
    def __tablename__(cls):
        return f"{cls.__name__}"
    """signavio_id = Column(String, nullable=True)
    category_id = Column(String, nullable=True)
    category_name = Column(String, nullable=True)
    creation_status = Column(String, nullable=True)
    creation_failed = Column(Boolean, nullable=True)
    has_linked_items = Column(Boolean, nullable=True)
    has_attributes_to_dict = Column(Boolean, nullable=True)
    needs_update = Column(Boolean, nullable=True)
    attribute_val_to_filter = Column(String, nullable=True)"""


class dbModels(Base, FileWatchMixin):
    @declared_attr
    def __tablename__(cls):
        return f"{cls.__name__}"
    # signavio_id = Column(String, nullable=True)
    # revision = Column(String, nullable=True)
    # element_type = Column(String, nullable=True)
    # error = Column(String, nullable=True)
    # json = Column(String, nullable=True)
