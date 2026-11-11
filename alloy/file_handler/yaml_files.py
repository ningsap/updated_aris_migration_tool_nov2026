import os
from datetime import datetime
from pathlib import Path

import yaml

from ARIS_Migration_Tool_SCB_Nov2026.alloy.configs.module_config import FILES, STANDARDS
from ARIS_Migration_Tool_SCB_Nov2026.alloy.general.helpers import root
from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger


def write_yaml_file(
    yaml_data: dict, file_name: str = FILES.DEFAULT_OUTPUT_YAML_FILE, path: str = "", file_name_is_path: bool = False
) -> bool:
    """
    Writes a dictionary to a YAML file.
    This function takes a dictionary (`yaml_data`) and writes it to a YAML file. The file name and path can be specified.
    If no file name is provided, a default name with the current timestamp is used. If no path is specified, a default
    directory is used. The function creates the necessary directories if they don't exist.

    Args:
        yaml_data (dict): The data to be written to the YAML file.
        file_name (str, optional): The name of the file to write to. Defaults to "default_output.yaml".
        path (str, optional): The directory path to save the file. Defaults to an empty string, which uses a default path.
        file_name_is_path (bool, optional): Flag to indicate if the file_name is a full path.
    Returns:
        bool: True if the file was successfully written, False otherwise.
    """

    if not file_name_is_path:

        if file_name == FILES.DEFAULT_OUTPUT_YAML_FILE:
            file_name = datetime.now().strftime(STANDARDS.DATE_LONG_FORMAT) + "_" + file_name

        file_name += ".yaml" if ".yaml" not in file_name else ""

        if not path:
            path = os.path.join(root(), FILES.TEMP_DIR)

    try:
        if not file_name_is_path:
            output_file = Path(os.path.join(path, file_name))
            output_file.parent.mkdir(parents=True, exist_ok=True)

        else:
            output_file = file_name

        with open(output_file, "w", encoding="utf-8") as outfile:
            yaml.dump(yaml_data, outfile, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"File creation failed: {e}")
        return False

    return True


def read_yaml_file(file_name: str, path: str = "", file_name_is_path: bool = False) -> dict:
    """
    Reads a YAML file and returns its contents as a dictionary.
    This function reads a YAML file specified by the `file_name` and `path`. If the path is not specified, a default
    directory is used. The function handles file not found, YAML decode errors, and other exceptions by
    logging the error and returning None.

    Args:
        file_name (str): The name of the YAML file to read.
        path (str, optional): The directory path of the YAML file. Defaults to an empty string, which uses a default path.
        file_name_is_path (bool, optional): Flag to indicate if the file_name is a full path
    Returns:
        dict: The contents of the YAML file as a dictionary, or None if an error occurs.
    """

    if not file_name_is_path:
        if not path:
            path = os.path.join(root(), FILES.TEMP_DIR)

        file_name += ".yaml" if ".yaml" not in file_name and ".yml" not in file_name else ""

        file_path = os.path.join(path, file_name)

    else:
        file_path = file_name

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logger.error(f"The file {file_path} was not found.")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error decoding YAML from the file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
