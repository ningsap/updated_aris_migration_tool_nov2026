import traceback
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text

from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_base import DatabaseUtilityBase
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_exceptions import DatabaseUnsupportedInitParam, DatabaseUtilityRuntimeError
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.models import Base
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger


class MySQLUtilityEngine(DatabaseUtilityBase):
    def __init__(
        self,
        db_name: str,
        username: str = "root",
        password: str = "",
        host: str = "localhost",
        port: int = 3306,
        append_from_base: bool = False,
        recreate_on_schema_change: bool = False,
        recreate_on_rerun: bool = False,
        *args,
        **kwargs,
    ):
        self.db_name = db_name
        self.username = username
        self.password = password
        self.host = host
        self.port = port

        if recreate_on_schema_change:
            raise DatabaseUnsupportedInitParam("Recreate on schema change is not supported for MySQL databases.")

        if recreate_on_rerun:
            raise DatabaseUnsupportedInitParam("Recreate on rerun is not supported for MySQL databases.")

        try:
            self.sync_engine = self._create_engine()
            logger.success(f"Engine created and connection established to {self.sync_engine.url}")
        except Exception as e:
            logger.error(f"Database creation/connection failed. Error: {e} | Traceback: {traceback.format_exc()}")

        inspector = inspect(self.sync_engine)
        # Use the existence of the metadata table as an indicator the schema is present.

        if not inspector.has_table("database_metadata"):
            self.setup_database_schema_if_not_exists()

        elif not self.schema_is_current():
            logger.warning("Database schema is outdated.")
            if append_from_base:
                self.append_missing_from_base()
                if not self.schema_is_current():
                    raise DatabaseUtilityRuntimeError("Database schema append failed.")

            else:
                raise DatabaseUtilityRuntimeError("Database schema is outdated.")

    def _create_engine(self):
        connection_url = f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        return create_engine(connection_url)

    def append_missing_from_base(self):
        """
        Appends missing tables and missing columns to the current schema.
        """
        inspector = inspect(self.sync_engine)
        existing_tables = inspector.get_table_names()

        with self.sync_engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                if table_name not in existing_tables:
                    table.create(conn)
                    logger.info(f"Table {table_name} created")
                else:
                    existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                    table_columns = {column.name for column in table.columns}
                    missing_columns = table_columns - existing_columns

                    for column in missing_columns:
                        column_type = table.columns[column].type.compile(conn.dialect)
                        sql_command = text(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}")
                        conn.execute(sql_command)
                        logger.info(f"Column {column} added to table {table_name}")
