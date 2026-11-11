import json
import os

from ARIS_Migration_Tool_SCB_Nov2026.alloy._EXAMPLES.TASK_WATCH._aux import _create_json_files
from ARIS_Migration_Tool_SCB_Nov2026.alloy._EXAMPLES.TASK_WATCH._models import DBWatchTable, FileWatchTable
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_factory import DatabaseUtilityFactory
from ARIS_Migration_Tool_SCB_Nov2026.alloy.general.helpers import root
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger
from ARIS_Migration_Tool_SCB_Nov2026.alloy.task_watch.task_watch import TaskWatch


def EXAMPLE_WATCH():

    # TaskWatch requires the DatabaseUtility to be initialized!
    dbu = DatabaseUtilityFactory.get_database_utility(db_engine="sqlite", db_name="MySQLiteDB")

    # Some preparations - create a directory with some mock JSON files
    _create_json_files(num_files=500, destination='./.TEMP', complexity=1000)

    # Read out the files - simulates the data retrieval
    temp_dir = os.path.join(root(), ".TEMP")
    test_list_files = os.listdir(temp_dir)

    def yield_files():
        nonlocal test_list_files

        for index, file in enumerate(test_list_files):

            file_id = file.split("_")[1][:-5]
            file_data = None

            with open(os.path.join(temp_dir, file), "r") as f:
                file_data = json.load(f)
            yield index, file_id, file_data

    # Choose between FileWatchTable and DBWatchTable

    # ====================== Using files as data storage ======================
    # FileWatchTable is a subclass of Base and FileWatchMixin and tracks data into TASK_WATCH_ARTIFACTS using JSON files (both default)

    file_watch = TaskWatch(
        watch_table=FileWatchTable,
        write_data_to_files_instead_db=True
    )

    # Use mock data from JSON files
    for index, file_id, file_data in yield_files():

        # Check if task is done
        # The ID can be a composite key as here or just a string, see the database watch example below

        # The keys must be named like the columns in the respective watch table!
        my_composite_id = {
            "task_id": file_id,
            "file_id": index
        }

        is_done, data = file_watch.is_task_done(id=my_composite_id)

        if is_done:
            logger.success(f"Task {file_id} is done - skip processing.")
        else:
            # ... do what is needed to retrieve the data, for instance SPM requests or heavy calculations...

            # After you are done retrieve the data, save it.
            is_save_successful = file_watch.save_task_results(id=my_composite_id, data=file_data)

            is_save_successful and logger.success(f"Task with ID {file_id} has been saved to the database with an associated file.")

        # ... continue with the data without repeating the task...

    # ====================== Using the database as data storage ======================
    # DBWatchTable is a subclass of Base and DBWatchMixin and tracks data into a database in JSON format (default)

    db_watch = TaskWatch(
        watch_table=DBWatchTable,
    )

   # Use mock data from JSON files
    for _, file_id, file_data in yield_files():

        # Check if task is done
        # Just using the file_id as id
        is_done, data = db_watch.is_task_done(id=file_id)

        if is_done:
            logger.success(f"Task {file_id} is done - skip processing.")
        else:
            # ... do what is needed to retrieve the data, for instance SPM requests or heavy calculations...

            # After you are done retrieve the data, save it.
            is_save_successful = db_watch.save_task_results(id=file_id, data=file_data)

            is_save_successful and logger.success(f"Task with ID {file_id} and its data has been saved to the database.")

        # ... continue with the data without repeating the task...


EXAMPLE_WATCH()
