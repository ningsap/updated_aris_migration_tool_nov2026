
from sqlalchemy.orm import Mapped, mapped_column

from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.models import Base
from ARIS_Migration_Tool_SCB_Nov2026.alloy.task_watch.definitions.watch_mixins import DBWatchMixin, FileWatchMixin


class FileWatchTable(Base, FileWatchMixin):
    add_a_column_if_you_want: Mapped[str] = mapped_column(nullable=True)
    task_id: Mapped[str] = mapped_column(nullable=False)
    file_id: Mapped[str] = mapped_column(nullable=False)


class DBWatchTable(Base, DBWatchMixin):
    ...  # or leave it blank
