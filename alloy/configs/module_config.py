from ARIS_Migration_Tool_SCB_Nov2026.alloy.patterns.true_value_enum import TrueValueEnum


class DEBUG(TrueValueEnum):
    WORK_ON_PACKAGE: bool = False


class STANDARDS(TrueValueEnum):
    DATE_LONG_FORMAT: str = "%d.%m.%Y_%H:%M:%S"
    DATE_LONG_FORMAT_FILESAVE: str = "%d-%m-%Y_%H:%M:%S"


class FILES(TrueValueEnum):
    TEMP_DIR: str = ".TEMP"
    TASK_WATCH_ARTIFACTS_DIR: str = ".TASK_WATCH_ARTIFACTS"
    DEFAULT_OUTPUT_JSON_FILE: str = "json_output"
    DEFAULT_OUTPUT_YAML_FILE: str = "yaml_output"
    DEFAULT_OUTPUT_CSV_FILE: str = "csv_output"
