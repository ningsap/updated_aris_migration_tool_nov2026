import csv
import os
from datetime import datetime
from pathlib import Path

from ARIS_Migration_Tool_SCB_Nov2026.alloy.configs.module_config import FILES, STANDARDS
from ARIS_Migration_Tool_SCB_Nov2026.alloy.general.helpers import root
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger


def write_csv_file(
    csv_data: list, file_name: str = FILES.DEFAULT_OUTPUT_CSV_FILE, path: str = "", file_name_is_path: bool = False
) -> bool:
    """
    Writes a list of dictionaries to a CSV file.

    Args:
        csv_data (list): A list of dictionaries where each dictionary represents a row.
        file_name (str, optional): The name of the CSV file. Defaults to "default_output.csv".
        path (str, optional): The directory path to save the file.
        file_name_is_path (bool, optional): Flag to indicate if the file_name is a full path.

    Returns:
        bool: True if the file was successfully written, False otherwise.
    """

    if not file_name_is_path:
        if file_name == FILES.DEFAULT_OUTPUT_CSV_FILE:
            file_name = datetime.now().strftime(STANDARDS.DATE_LONG_FORMAT) + "_" + file_name

        file_name += ".csv" if ".csv" not in file_name else ""

        if not path:
            path = os.path.join(root(), FILES.TEMP_DIR)

    try:

        if not file_name_is_path:
            output_file = Path(os.path.join(path, file_name))
            output_file.parent.mkdir(parents=True, exist_ok=True)

        else:
            output_file = file_name

        with open(output_file, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)

    except Exception as e:
        logger.error(f"File creation failed: {e}")
        return False

    return True


def read_csv_file(file_name: str, path: str = "", file_name_is_path: bool = False) -> list:
    """
    Reads a CSV file and returns its contents as a list of dictionaries.

    Args:
        file_name (str): The name of the CSV file.
        path (str, optional): The directory path of the CSV file.
        file_name_is_path (bool, optional): Flag to indicate if the file_name is a full path.

    Returns:
        list: A list of dictionaries where each dictionary represents a row.
    """
    if not file_name_is_path:
        if not path:
            path = os.path.join(root(), FILES.TEMP_DIR)

        file_path = os.path.join(path, file_name + ".csv" if ".csv" not in file_name else file_name)

    else:
        file_path = file_name

    try:
        with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            return list(reader)

    except FileNotFoundError:
        logger.error(f"The file {file_path} was not found.")
        return None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
