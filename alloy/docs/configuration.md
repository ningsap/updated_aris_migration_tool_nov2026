# Configuration ([module link](../alloy/configs/module_config.py))

> ⚠️ Config approach will be changed in near future. 

This module gathers all the different configurations used throughout this package in one place. Nothing more to it. Here is a quick rundown on the current configs and what they mean:

#### DEBUG
- `WORK_ON_PACKAGE` - Set this to `True` if you are working on the package itself. This will make sure that the package is imported from the local directory instead of the installed package.

#### STANDARDS
- `DATE_LONG_FORMAT` - Defines the long format for dates as day, month, year, hour, minute, second.
- `DATE_LONG_FORMAT_FILESAVE` - Specifies the date format for saving files, using hyphens between day, month, and year.

#### FILES
- `TEMP_DIR` - Directory name for temporary storage.
- `WATCH_ARTIFACTS_DIR` - Directory name for storing watch artifacts.
- `DEFAULT_OUTPUT_JSON_FILE` - Default name for JSON output files.
- `DEFAULT_OUTPUT_CSV_FILE` - Default name for CSV output files.
- `DEFAULT_OUTPUT_YAML_FILE` - Default name for YAML output files.