# Task Watch ([module link](../alloy/task_watch/))

> A combined approach that was previously named `FileTaskTracker` and `TaskTracker`.

The `task_watch` module provides a way to monitor the progress of a task. It is useful for long-running tasks that you want to keep track of, such as heavy calculations, data processing or network requests. An example use case could be the upload of diagrams during a migration where could check whether a specific diagram has been uploaded or not.

## Usage

The `TaskWatch` class combines both approaches from the `FileTaskTracker` and `TaskTracker` classes. During initialization, you can specify where and how you want the data (results) of you tasks to be stored.

> **Note:** You need to initialize a database connection from the `alloy.databases.database_utility_factory.DatabaseUtilityFactory` before using the `TaskWatch` class.

See the [examples](../alloy/_EXAMPLES/WATCH/) for more information, but here is a quick rundown:

```python
from alloy.databases.models import Base
from alloy.task_watch.task_watch import TaskWatch


class MyDBWatchTable(Base, DBWatchMixin):
    ...

# or

class MyFileWatchTable(Base, FileWatchMixin):
    ...

# Basic initialization for a database tracking
db_task_watch = TaskWatch(
    watch_table=MyWatchTable
)

# or

file_task_watch = TaskWatch(
    watch_table=MyFileWatchTable,
    write_data_to_files_instead_db=True # Default is False, must be set to True to write to files
)

for task in my_tasks: # e.g. creating Dictionary entries or uploading diagrams to SPM etc.

    is_done, data = is_done, data = file_task_watch.is_task_done(id=task.id)

    if is_done:
        # ... do something with the data or just skip the processing ...
    
    else:
        # ... do the processing required to acquire the data you want to store ...

```


That's all there is to it. Ideally, you would have the model in a separate file and import it.

## File vs. database tracking

`TaskWatch` allows you to customize where and how you want to track the data. By default, the data is stored in a database in JSON (stringified) format by default. However, you can also store the data in files by setting the `write_data_to_files_instead_db` parameter to `True`. This will store data in files under the projects `root/.TASK_WATCH_ARTIFACTS/<watch table name>` directory.

You can specify the serialization and deserialization functions for storing the data, i.e. you can also choose to store different types of data other than JSON. Basically, anything that can be serialized and deserialized can be stored.

Similarly with file storage, you can specify the file extension as well as the functions for reading and writing the data. As default, it uses the `json` extension and the `json` file handling functions from `alloy.file_handler.json_files`. This means, that you can also store data in other formats, such as `yaml` or `csv`, but you need to make sure that you custom functions have the same signature as the default ones.

