import os
import traceback
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text

from ARIS_Migration_Tool_SCB_Nov2026.alloy.configs.module_config import STANDARDS
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_base import DatabaseUtilityBase
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_exceptions import DatabaseUtilityRuntimeError
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.models import Base
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger


class SQLiteUtilityEngine(DatabaseUtilityBase):

    def __init__(
        self,
        db_name: str,
        append_from_base: bool = False,
        recreate_on_schema_change: bool = False,
        recreate_on_rerun: bool = False,
        *args,
        **kwargs
    ):

        self.db_name = db_name

        try:

            self.sync_engine = self._create_engine()
            logger.success(f"Engine created and connection established to {self.sync_engine.url}")

        except Exception as e:
            logger.error(f"Database creation/connection failed. Error: {e} | Traceback: {traceback.format_exc()}")

        self.db_file_path = self.sync_engine.url.database

        if not os.path.exists(self.sync_engine.url.database):
            self.setup_database_schema_if_not_exists()

        elif recreate_on_rerun:
            self.archive_and_create_new_database()

        elif not self.schema_is_current():
            logger.warning("Database schema is outdated.")

            if recreate_on_schema_change:
                self.archive_and_create_new_database()
                logger.success("Database archived and recreated.")

            elif append_from_base:
                self.append_missing_from_base()

            else:
                raise DatabaseUtilityRuntimeError("Database schema is outdated.")

    def _create_engine(self):

        return create_engine(f"sqlite:///{self.db_name}.sqlite")

    def append_missing_from_base(self):
        """
        Appends missing tables and updates existing tables with missing columns to the database schema.
        """
        inspector = inspect(self.sync_engine)
        existing_tables = inspector.get_table_names()

        with self.sync_engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                if table_name not in existing_tables:
                    table.create(conn)
                    logger.info(f"Table {table_name} created")
                else:
                    existing_columns = set(col['name'] for col in inspector.get_columns(table_name))
                    table_columns = set(column.name for column in table.columns)
                    missing_columns = table_columns - existing_columns

                    for column in missing_columns:
                        column_type = table.columns[column].type.compile(conn.dialect)
                        sql_command = text(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}")
                        conn.execute(sql_command)
                        logger.info(f"Column {column} added to table {table_name}")

    def archive_and_create_new_database(self):

        try:

            timestamp = datetime.now(timezone.utc)
            self.set_archive_meta_data(optional_timestamp=timestamp)

            old_db_name = f"{self.db_file_path.split('.sqlite')[0]}_{timestamp.strftime(STANDARDS.DATE_LONG_FORMAT_FILESAVE)}.sqlite"
            os.rename(self.db_file_path, old_db_name)
            logger.warning(f"Old database renamed to {old_db_name}")
            self.sync_engine.dispose()

            self.sync_engine = self._create_engine()

            self.setup_database_schema_if_not_exists()

        except Exception as e:
            raise DatabaseUtilityRuntimeError("Database recreation on rerun failed.")
