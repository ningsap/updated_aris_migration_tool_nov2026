from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_base import DatabaseUtilityBase
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_exceptions import DatabaseFactoryUnsupportedEngine, DatabaseUtilityNotInstantiated
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.engines.MySQLUtilityEngine import MySQLUtilityEngine
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.engines.SQLiteUtilityEngine import SQLiteUtilityEngine
from ARIS_Migration_Tool_SCB_Nov2026.alloy.patterns.singleton import Singleton


class DatabaseUtilityFactory:
    """
    A factory class to create instances of database utility classes based on the database engine type.
    """

    @staticmethod
    def get_database_utility(
        db_engine: str,
        db_name: str,
        username: str = "",
        password: str = "",
        host: str = "",
        port: int = 0,
        options: dict = None,
        append_from_base: bool = False,
        recreate_on_schema_change: bool = False,
        recreate_on_rerun: bool = False,
    ):
        """
        Creates and returns the appropriate database utility instance based on the provided engine type.

        Args:
            engine_type (str): The type of the database engine (e.g., 'sqlite', 'mysql').
            db_name (str): The name of the database.
            username (str, optional): Username for database authentication.
            password (str, optional): Password for database authentication.
            host (str, optional): Host address of the database server.
            port (int, optional): Port number of the database server.
            driver (str, optional): Database driver to be used for connection.
            options (dict, optional): Additional connection options.

        Returns:
            DatabaseUtilityInterface: An instance of a database utility class.
        """

        _SUPPORTED_ENGINES = {
            'sqlite': "SQLite",
            'mysql': "MySQL"
        }

        db_engine = db_engine.lower()

        if db_engine == _SUPPORTED_ENGINES['sqlite'].lower():

            return SQLiteUtilityEngine(
                db_name=db_name,
                append_from_base=append_from_base,
                recreate_on_schema_change=recreate_on_schema_change,
                recreate_on_rerun=recreate_on_rerun
            )

        elif db_engine == _SUPPORTED_ENGINES['mysql'].lower():

            return MySQLUtilityEngine(
                db_name=db_name,
                username=username,
                password=password,
                host=host,
                port=port,
                append_from_base=append_from_base,
                recreate_on_schema_change=recreate_on_schema_change,
                recreate_on_rerun=recreate_on_rerun
            )

        else:
            raise DatabaseFactoryUnsupportedEngine(f"Unsupported database engine type: {db_engine}. Supported engines: {', '.join(_SUPPORTED_ENGINES.values())}")

    @staticmethod
    def get_existing_instance():
        """
        Returns an existing instance of any class that inherits from DatabaseUtilityBase.

        Returns:
            DatabaseUtilityBase: The existing instance of any subclass of DatabaseUtilityBase, or None if no such instance exists.
        """
        for instance in Singleton._instances.values():
            if isinstance(instance, DatabaseUtilityBase):
                return instance

        raise DatabaseUtilityNotInstantiated("No instance of a database utility class found.")
