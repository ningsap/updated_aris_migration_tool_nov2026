import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from ARIS_Migration_Tool_SCB_Nov2026.alloy.configs.module_config import FILES
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_factory import DatabaseUtilityFactory
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.models import Base
from ARIS_Migration_Tool_SCB_Nov2026.alloy.file_handler.json_files import read_json_file, write_json_file
from ARIS_Migration_Tool_SCB_Nov2026.alloy.general.helpers import root
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger
from ARIS_Migration_Tool_SCB_Nov2026.alloy.task_watch.definitions.watch_exceptions import FaultyWatchTable
from ARIS_Migration_Tool_SCB_Nov2026.alloy.task_watch.definitions.watch_mixins import DBWatchMixin, FileWatchMixin, WatchTableType


class TaskWatch:

    def __init__(
        self,
        watch_table: WatchTableType,
        write_data_to_files_instead_db: bool = False,
        track_file_prefix: str = None,
        track_file_path: str = None,
        serialization_method: Callable[[Any], str] = json.dumps,
        deserialization_method: Callable[[str], Any] = json.loads,
        file_read_method: Callable[[Any], Any] = read_json_file,
        file_write_method: Callable[[Any], bool] = write_json_file,
        file_extension: str = ".json"
    ) -> None:
        """
        Initializes the TaskWatch instance with the given configuration.
        Args:
            watch_table (Type[Base]): A subclass of Base and either DBWatchMixin or FileWatchMixin that represents the tracking table.
            write_data_to_files_instead_db (bool, optional): Flag to determine if data should be written to files instead of the database.
                If True, watch_table must be a subclass of FileWatchMixin. Defaults to False.
            track_file_prefix (str, optional): Prefix for tracking file names. If not provided, it defaults to the name of the watch_table.
            track_file_path (str, optional): Directory path where tracking files will be stored. If not provided, a default path is computed.
            serialization_method (Callable[[Any], str], optional): Function to serialize data. Defaults to json.dumps.
            deserialization_method (Callable[[str], Any], optional): Function to deserialize data. Defaults to json.loads.
            file_read_method (Callable[[Any], Any], optional): Function to read files. Defaults to read_json_file.
            file_write_method (Callable[[Any], bool], optional): Function to write files. Defaults to write_json_file.
            file_extension (str, optional): Extension for tracking files. Defaults to ".json".
        Raises:
            FaultyWatchTable: If watch_table is not a subclass of Base, or if it does not inherit from either DBWatchMixin or FileWatchMixin.
            FaultyWatchTable: If there is a mismatch between the type of watch_table and the write_data_to_files_instead_db flag.
        """

        self.dbu = DatabaseUtilityFactory.get_existing_instance()
        self.write_data_to_files_instead_db = write_data_to_files_instead_db

        # Check if given tracking table is a subclass of Base and either DBTrackerMixin or FileTrackerMixin
        if not issubclass(watch_table, Base):
            raise FaultyWatchTable(f"Tracking table must be a subclass of alloy.databases.models.Base. Given: {watch_table}")
        else:
            if not issubclass(watch_table, DBWatchMixin) and not issubclass(watch_table, FileWatchMixin):
                raise FaultyWatchTable(f"Tracking table must be a subclass of either DBTrackerMixin or FileTrackerMixin from alloy.task_watch.definitions.watch_mixins. Given: {watch_table}")

        if issubclass(watch_table, DBWatchMixin) and write_data_to_files_instead_db:
            raise FaultyWatchTable(f"Tracking table is a subclass of alloy.task_watch.definitions.watch_mixins.DBTrackerMixin, but write_data_to_files_instead_db is set to True. Given: {watch_table}")

        if issubclass(watch_table, FileWatchMixin) and not write_data_to_files_instead_db:
            raise FaultyWatchTable(
                f"Tracking table is a subclass of alloy.task_watch.definitions.watch_mixins.FileTrackerMixin, but write_data_to_files_instead_db is set to False. Given: {watch_table}")

        self.watch_table = watch_table

        # Check whether serialization methods are default
        if serialization_method == json.dumps:
            logger.info(f"Using default stringify method: json.dumps")

        self.serialization_method = serialization_method

        if deserialization_method == json.loads:
            logger.info(f"Using default parse method: json.loads")

        self.deserialization_method = deserialization_method

        # Check whether file extension is given
        if file_extension == ".json":
            logger.info(f"Using default file extension: .json")

        self.file_extension = file_extension

        # Check whether tracking to files or database
        if write_data_to_files_instead_db:
            logger.info(f"Tracking to files instead of database.")

            if not track_file_path:
                self.track_file_path = os.path.join(root(), FILES.TASK_WATCH_ARTIFACTS_DIR)
                logger.info(f"No file path given, using default path: {self.track_file_path}")

            else:
                self.track_file_path = track_file_path
                logger.info(f"Using given file path: {self.track_file_path}")

            if not track_file_prefix:
                self.track_file_prefix = watch_table.__name__
                logger.info(f"No file prefix given, using default prefix (table name): {self.track_file_prefix}")

            else:
                self.track_file_prefix = track_file_prefix
                logger.info(f"Using given file prefix: {self.track_file_prefix}")

        # Check whether file read and write methods are default
        if write_data_to_files_instead_db and file_read_method == read_json_file:
            logger.info(f"Using default file read method: read_json_file")
        self.read_file = file_read_method

        if write_data_to_files_instead_db and file_write_method == write_json_file:
            logger.info(f"Using default file write method: write_json_file")
        self.write_file = file_write_method

    def is_task_done(self, id: str | Dict) -> Tuple[DBWatchMixin | FileWatchMixin | bool, Any]:
        """
        Check if a task is complete and retrieve its associated data.
        This method determines whether a task is done by first retrieving the task entry from the database
        and then retrieving the respective data either from the database record or file storage, depending on 
        the value of the `write_data_to_files_instead_db` flag.

        If the task is identified using a string, it is converted into a dictionary format internally.
        The dictionary keys must match the columns of the tracking table.

        In case the task entry is not found, the method returns False along with None for the data.

        Parameters:
            id (str | dict): The identifier of the task. This can be either a string or a dictionary 
                              containing the task id.
        Returns:
            tuple[DBWatchMixin | FileWatchMixin | bool, Any]:
                A tuple where:
                  - The first element is either a database or file watch model instance when the task exists,
                    or False if the task is not found.
                  - The second element is the task data fetched either from a file (if configured)
                    or by deserializing the data from the task entry. If no data is available, it returns None.
        """

        if isinstance(id, str):
            id = {'id': id}

        __use_id = self.__id(id)

        task_db_entry: DBWatchMixin | FileWatchMixin = self.dbu.read(model_class=self.watch_table, filters=id)

        if not task_db_entry:
            return False, None

        # Read out file
        if self.write_data_to_files_instead_db:
            artifact_file = self.__file_path(__use_id)

            data = self.read_file(file_name=artifact_file, file_name_is_path=True)

            return task_db_entry, data

        # Read out database
        else:

            if not task_db_entry.data:
                return task_db_entry, None

            return task_db_entry, self.deserialization_method(task_db_entry.data)

    def save_task_results(self, data: Any, id: str | Dict, try_update: bool = False) -> bool:
        """
        Saves task results to a database or file based on the current configuration.
        This method first determines whether a task with the specified identifier exists. If the identifier 
        is provided as a string, it is converted into a dictionary. The method then checks for an existing 
        database record using the identifier. If a record is found and try_update is False (and writing to 
        files is not enabled), a warning is logged and the method returns False. If writing to files is enabled, 
        the method writes the data to the specified file path and creates or updates the corresponding database 
        record with the relative file path. Otherwise, the data is serialized and stored directly in the database.

        Args:
            data (Any): The task result data to be saved.
            id (str | Dict): An identifier for the task. If provided as a string, it is converted into a dictionary.
            try_update (bool): Whether to update an existing task result. Defaults to False.
        Returns:
            bool: True if the task results were successfully saved or updated, False otherwise.
        """

        if isinstance(id, str):
            id = {'id': id}

        __use_id = self.__id(id)

        if existing_db_record := self.dbu.read(model_class=self.watch_table, filters=id):

            if existing_db_record and not try_update and not self.write_data_to_files_instead_db:
                logger.warning(f"Task with id {__use_id} already exists in database, but try_update is set to False.")
                return False

            task_db_entry = existing_db_record

        else:

            task_db_entry = self.watch_table(**id)

        # Write to file
        if self.write_data_to_files_instead_db:

            artifact_file = self.__file_path(__use_id)

            if os.path.exists(artifact_file) and not try_update:
                logger.warning(f"Task with id {__use_id} already exists in file, but try_update is set to False.")
                return False

            write_confirmation = self.write_file(data=data, file_name=artifact_file, file_name_is_path=True)

            if not write_confirmation:
                logger.error(f"Writing to file failed: {artifact_file}")
                return False

            task_db_entry.relative_file_path = os.path.join(self.track_file_prefix, f"{self.__id(__use_id)}{self.file_extension}")

            self.dbu.create(model_object=task_db_entry, try_update=try_update)

            return True

        # Write to database
        else:

            task_db_entry.data = self.serialization_method(data)

            self.dbu.create(model_object=task_db_entry, try_update=try_update)

            return True

    def yield_filtered_records(self, filters: Optional[dict] = {}):
        """
        Yields filtered records along with their corresponding data.

        Args:
            filters (Optional[dict]): A dictionary containing filters to apply on the records. Defaults to an empty dictionary.

        Yields:
            Tuple: A tuple containing the record ID and its corresponding data.

        Returns:
            None
        """

        filtered_records: List[DBWatchMixin | FileWatchMixin] = self.dbu.read(model_class=self.watch_table, filters=filters, multiple=True)

        if not filtered_records:
            logger.error("No records available for mapping.")
            return

        for record in filtered_records:

            if self.write_data_to_files_instead_db:
                data = self.read_file(os.path.join(self.track_file_path, record.relative_file_path), file_name_is_path=True)
            else:
                data = self.deserialization_method(record.data)

            yield record, data

    def __id(self, id: str | Dict) -> str:

        if isinstance(id, dict):
            return f"{'_'.join([str(v) for v in id.values()])}"
        else:
            return str(id)

    def __file_path(self, used_id: str) -> str:
        return os.path.join(self.track_file_path, self.track_file_prefix, f"{self.__id(used_id)}{self.file_extension}")
