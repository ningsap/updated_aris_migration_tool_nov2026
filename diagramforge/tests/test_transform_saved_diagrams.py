import json
import os
from pathlib import Path

import pytest

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.diagramforge import DiagramForge


def get_json_files():
    test_data_dir = os.path.join(os.path.dirname(__file__), "data")

    return [os.path.join(test_data_dir, f) for f in os.listdir(test_data_dir) if f.endswith(".json")]


@pytest.mark.parametrize("json_file", Path("tests/data").glob("*.json"))
def test_transform_saved_diagrams(json_file):
    FORGE_CONFIG.LOG_DEBUG = False

    input_data = None
    file_name = None

    with open(json_file, "r") as f:
        file_name = os.path.basename(json_file)
        input_data = json.load(f)

    assert input_data is not None
    assert isinstance(input_data, dict)
    assert input_data.get("stencil", {}).get("id") == "BPMNDiagram"

    diagram_forge = DiagramForge(input_data)
    optimized_diagram = diagram_forge.to_spm_json()

    assert optimized_diagram is not None

    upload_dir_name = "TESTS_UPLOAD_TO_SPM"
    upload_dir = Path(upload_dir_name)
    upload_dir.mkdir(parents=True, exist_ok=True)

    with open(f"{upload_dir_name}/{file_name}", "w") as f:
        json.dump(optimized_diagram, f, indent=4)
