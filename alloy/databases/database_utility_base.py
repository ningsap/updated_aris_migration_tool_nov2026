import traceback
from datetime import datetime, timezone
from typing import List, Type, Union

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_exceptions import DatabaseUtilityRuntimeError
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.models import Base, DatabaseMetadata, DatabaseStatus
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger
from ARIS_Migration_Tool_SCB_Nov2026.alloy.patterns.singleton import Singleton


class DatabaseUtilityBase(metaclass=Singleton):
    def __init__(self, sync_engine: object):
        self.sync_engine = sync_engine

    # ====================================== DB MANAGEMENT METHODS ======================================

    def setup_database_schema_if_not_exists(self):
        """
        Ensures the database and its schema are created if they do not exist.
        This method checks for the existence of essential tables and creates them if necessary.
        """
        try:
            inspector = inspect(self.sync_engine)
            if not inspector.has_table(DatabaseMetadata.__tablename__):
                Base.metadata.create_all(self.sync_engine)
                self.set_creation_meta_data()

                logger.success(f"Database and schema created at {self.sync_engine.url.database}.")
                logger.info(f"Tables created: {self._current_tables_list()}")
            else:
                logger.info(f"Database already exists at {self.sync_engine.url.database}. No action needed.")

        except Exception as e:
            logger.error(f"Failed to create database or tables. Error: {e} | Traceback: {traceback.format_exc()}")

    def schema_is_current(self) -> bool:
        """
        Checks if the database schema is current.

        Returns:
            bool: True if the schema is up-to-date, False otherwise.
        """
        try:
            inspector = inspect(self.sync_engine)
            for table_name in Base.metadata.tables.keys():
                if not inspector.has_table(table_name):
                    return False
                model_columns = set(Base.metadata.tables[table_name].c.keys())
                db_columns = set([k["name"] for k in list(inspector.get_columns(table_name))])
                if model_columns != db_columns:
                    return False
            return True

        except Exception as e:
            logger.error(f"Error checking if schema is current. Error: {e} | Traceback: {traceback.format_exc()}")

    def _current_tables_list(self) -> list:
        """
        Retrieves the current list of tables in the database.

        Returns:
            list: A list of table names in the database.
        """

        try:
            inspector = inspect(self.sync_engine)
            return inspector.get_table_names()
        except Exception as e:
            logger.error(f"Retrieving database tables failed. Error: {e} | Traceback: {traceback.format_exc()}")
            return []

    def set_creation_meta_data(self, optional_timestamp: datetime = None):
        new_metadata_entry = DatabaseMetadata(
            status=DatabaseStatus.ACTIVE, creation_timestamp=datetime.now(optional_timestamp or timezone.utc)
        )

        with Session(self.sync_engine) as session:
            session.add(new_metadata_entry)
            session.commit()

    def set_archive_meta_data(self, optional_timestamp: datetime = None):
        """
        Sets the archiving timestamp and status of the database.
        """

        with Session(self.sync_engine) as session:
            metadata_entry = (
                session.query(DatabaseMetadata)
                .filter_by(status=DatabaseStatus.ACTIVE)
                .order_by(DatabaseMetadata.creation_timestamp.desc())
                .first()
            )
            if metadata_entry:
                metadata_entry.status = DatabaseStatus.ARCHIVED
                metadata_entry.archiving_timestamp = optional_timestamp or datetime.now(timezone.utc)
                session.commit()

    # ====================================== CRUD METHODS ======================================

    def create(self, model_object, try_update=False):
        """
        Inserts a new record into the database.

        This method attempts to add a new record to the database using the provided `model_object`. If the insertion
        fails (e.g., due to a primary key conflict or other integrity error), and if `try_update` is set to True,
        the method will attempt to update the existing record instead.

        Args:
            model_object (Base): An instance of the SQLAlchemy model class representing the record to be added to the database.
            try_update (bool, optional): If True, attempts to update the record if the insertion fails. Defaults to False.

        Returns:
            bool:
                - True if the record was successfully inserted or updated.
                - False if both the insertion and the update (if attempted) failed.

        Raises:
            None: This method logs errors and returns False if an exception occurs, rather than raising an exception.

        Example:
            # Create a new user
            new_user = User(id=1, name='John Doe', email='john.doe@example.com')
            success = create(new_user)

            # Attempt to create a new user, or update the existing user if a conflict occurs
            success = create(new_user, try_update=True)
        """

        try:
            with Session(self.sync_engine) as session:
                session.add(model_object)
                session.commit()
                return True
        except Exception as e:
            logger.error(
                f"Could not insert model instance {model_object}. Error: {e} | Traceback: {traceback.format_exc()}"
            )

            if try_update:
                return self.update(model_object)

            return False

    def read(
        self,
        model_class: Type[Base],
        multiple: bool = False,
        filters: dict = None,
        negative_filters: dict = None,
        limit: int = None,
    ) -> Union[Base, List[Base], None]:
        """
        Retrieves records from the database based on the specified filters.

        This method queries the database for records of the specified `model_class` that match the given `filters`.
        It can also exclude records that match the `negative_filters`. The method returns either the first matching
        record or all matching records based on the `multiple` flag.

        Args:
            model_class (Type[Base]): The SQLAlchemy model class representing the table to query.
            multiple (bool, optional): If True, returns all matching records. If False, returns the first matching record. Defaults to False.
            filters (dict, optional): A dictionary of filters to apply to the query. The keys are column names, and the values are the filter criteria.
                Example: {'status': 'active', 'age': [25, 30, 35]}.
            negative_filters (dict, optional): A dictionary of negative filters to exclude certain records from the query. The keys are column names,
                and the values are the exclusion criteria. Example: {'country': 'USA'}.
            limit (int, optional): The maximum number of records to retrieve. If None, no limit is applied. Defaults to None.

        Returns:
            Union[Base, List[Base], None]:
                - If `multiple` is False, returns the first matching record (an instance of `model_class`) or None if no match is found.
                - If `multiple` is True, returns a list of matching records (instances of `model_class`), or an empty list if no matches are found.
                - Returns None if an error occurs during the query execution.

        Raises:
            None: This method logs errors and returns None if an exception occurs, rather than raising an exception.

        Example:
            # Retrieve the first active user
            user = read(User, filters={'status': 'active'})

            # Retrieve all active users
            users = read(User, multiple=True, filters={'status': 'active'})

            # Retrieve all users except those from the USA
            users = read(User, multiple=True, negative_filters={'country': 'USA'})

            # Retrieve the first 10 active users
            users = read(User, multiple=True, filters={'status': 'active'}, limit=10)
        """

        try:
            with Session(self.sync_engine) as session:
                query = session.query(model_class)

                if filters:
                    for column_name, filter_value in filters.items():
                        column = getattr(model_class, column_name)

                        if isinstance(filter_value, list):
                            query = query.filter(column.in_(filter_value))
                        else:
                            query = query.filter(column == filter_value)

                if negative_filters:
                    for column_name, filter_value in negative_filters.items():
                        column = getattr(model_class, column_name)

                        if isinstance(filter_value, list):
                            query = query.filter(~column.in_(filter_value))
                        else:
                            query = query.filter(column != filter_value)

                if limit is not None:
                    query = query.limit(limit)

                if multiple:
                    results = query.all()
                else:
                    results = query.first()

                return results
        except Exception as e:
            logger.error(
                f"Could not retrieve records from table {model_class}. Error: {e} | Traceback: {traceback.format_exc()}"
            )
            return None

    def update(self, model_object: Base) -> bool:
        """
        Updates an existing record in the database.

        This method attempts to update an existing record in the database with the data provided in `model_object`.
        The `model_object` should represent an existing record in the database, identified by its primary key.
        If the update is successful, the method returns `True`. If an error occurs during the update process,
        the method logs the error and returns `False`.

        Args:
            model_object (Base): An instance of the SQLAlchemy model class representing the record to be updated.
                                This object should contain the primary key of the record to be updated.

        Returns:
            bool:
                - True if the record was successfully updated.
                - False if the update failed.

        Raises:
            None: This method logs errors and returns False if an exception occurs, rather than raising an exception.

        Example:
            # Update an existing user
            user_to_update = User(id=1, name='Jane Doe', email='jane.doe@example.com')
            success = update(user_to_update)

            if success:
                print("User updated successfully.")
            else:
                print("Failed to update the user.")
        """

        try:
            with Session(self.sync_engine) as session:
                session.merge(model_object)
                session.commit()
                return True

        except Exception as e:
            logger.error(
                f"Failed to update model instance {model_object}. Error: {e} | Traceback: {traceback.format_exc()}"
            )
            return False

    def delete(self, model_object: Base) -> bool:
        """
        Deletes an existing record from the database.

        This method attempts to delete a record from the database based on the provided `model_object`.
        The `model_object` should represent an existing record in the database, identified by its primary key.
        If the deletion is successful, the method returns `True`. If an error occurs during the deletion process,
        the method logs the error and returns `False`.

        Args:
            model_object (Base): An instance of the SQLAlchemy model class representing the record to be deleted.
                                This object should contain the primary key of the record to be deleted.

        Returns:
            bool:
                - True if the record was successfully deleted.
                - False if the deletion failed.

        Raises:
            None: This method logs errors and returns False if an exception occurs, rather than raising an exception.

        Example:
            # Delete an existing user
            user_to_delete = User(id=1)
            success = delete(user_to_delete)

            if success:
                print("User deleted successfully.")
            else:
                print("Failed to delete the user.")
        """

        try:
            with Session(self.sync_engine) as session:
                session.delete(model_object)
                session.commit()
                return True
        except Exception as e:
            logger.error(
                f"Failed to delete model instance {model_object}. Error: {e} | Traceback: {traceback.format_exc()}"
            )
            return False
