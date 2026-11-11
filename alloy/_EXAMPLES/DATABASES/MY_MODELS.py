from sqlalchemy.orm import Mapped, mapped_column

from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.models import Base


class MyCustomDBTable(Base):  # This should be located in a separate file - here just for demonstration purposes
    __tablename__ = "my_custom_model"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"<MyCustomDBTable(name={self.name}, last_name={self.last_name})>"
