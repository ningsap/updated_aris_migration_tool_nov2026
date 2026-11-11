import json
import os
from datetime import datetime
from pathlib import Path

from ARIS_Migration_Tool_SCB_Nov2026.alloy.configs.module_config import FILES, STANDARDS
from ARIS_Migration_Tool_SCB_Nov2026.alloy.general.helpers import root
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger


def write_json_file(
    data: dict, file_name: str = FILES.DEFAULT_OUTPUT_JSON_FILE, path: str = "", file_name_is_path: bool = False
) -> bool:
    """
    Writes a dictionary to a JSON file.

    This function takes a dictionary (`json_data`) and writes it to a JSON file. The file name and path can be specified.
    If no file name is provided, a default name with the current timestamp is used. If no path is specified, a default
    temporary directory is used. The function creates the necessary directories if they don't exist.

    Args:
        json_data (dict): The data to be written to the JSON file.
        file_name (str, optional): The name of the file to write to. Defaults to FILES.DEFAULT_OUTPUT_FILE.
        path (str, optional): The directory path to save the file. Defaults to an empty string, which uses a default path.
        file_name_is_path (bool, optional): Flag to indicate if the file_name is a full path.

    Returns:
        bool: True if the file was successfully written, False otherwise.
    """

    if not file_name_is_path:
        if file_name == FILES.DEFAULT_OUTPUT_JSON_FILE:
            file_name = datetime.now().strftime(STANDARDS.DATE_LONG_FORMAT) + "_" + file_name

        file_name += ".json" if ".json" not in file_name else ""

        if not path:
            path = os.path.join(root(), FILES.TEMP_DIR)

    if not file_name_is_path:
        output_file = Path(os.path.join(path, file_name))

    else:
        output_file = Path(file_name)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    json_object = json.dumps(data, indent=4)

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write(json_object)

    return True


def read_json_file(file_name: str, path: str = "", file_name_is_path: bool = False) -> dict:
    """
    Reads a JSON file and returns its contents as a dictionary.

    This function reads a JSON file specified by the `file_name` and `path`. If the path is not specified, a default
    temporary directory is used. The function handles file not found, JSON decode errors, and other exceptions by
    logging the error and returning None.

    Args:
        file_name (str): The name of the JSON file to read.
        path (str, optional): The directory path of the JSON file. Defaults to an empty string, which uses a default path.
        file_name_is_path (bool, optional): Flag to indicate if the file_name is a full path.

    Returns:
        dict: The contents of the JSON file as a dictionary, or None if an error occurs.
    """
    if not file_name_is_path:
        if not path:
            path = os.path.join(root(), FILES.TEMP_DIR)
        file_path = os.path.join(path, file_name + ".json" if ".json" not in file_name else file_name)

    else:
        file_path = file_name

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"The file {file_path} was not found.")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from the file {file_path}.")
        return None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
