"""Local testing: run DiagramForge → write rendered diagram → upload to Signavio.

Usage (run as a module from repo root):
    Process all files in local_testing/testfiles_active/:
        .venv/bin/python -m local_testing.run

    Process specific files (paths or names from testfiles_active/):
        .venv/bin/python -m local_testing.run file1.json file2.json
        .venv/bin/python -m local_testing.run path/to/file.json

    Process files matching a glob pattern in testfiles_active/:
        .venv/bin/python -m local_testing.run "TEST_*"

Upload toggle:
    Edit the DIAGRAMFORGE_UPLOAD constant below (works when running from
    VS Code), or set the DIAGRAMFORGE_UPLOAD environment variable to
    override it (1/true/yes/on vs 0/false/no/off). When disabled, Process
    Manager authentication is skipped entirely.
"""

import json
import os
import random
import string
import sys
import time
from pathlib import Path

# Allow direct execution (e.g. VS Code's "Run File"): when invoked as
# `python local_testing/run.py` rather than `python -m local_testing.run`,
# only this script's directory lands on sys.path, so `from local_testing...`
# imports fail. Insert the repo root so the package resolves either way.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Upload toggle
#
# Flip this to False to skip uploading rendered diagrams to Signavio Process
# Manager. When False, no Process Manager authentication happens either, so
# this works without Signavio credentials.
#
# The DIAGRAMFORGE_UPLOAD environment variable, when set, overrides this
# constant.
# ---------------------------------------------------------------------------
DIAGRAMFORGE_UPLOAD: bool = True

from diagramforge.CONFIG import FORGE_CONFIG
from diagramforge.diagramforge import DiagramForge
from diagramforge.SETUP import forge_logger as log

FORGE_CONFIG.LOG_DEBUG = True
FORGE_CONFIG.COLUMN_POSITIONING_MAX_ITERATIONS = 100
FORGE_CONFIG.ALWAYS_USE_DIAGONALS_IN_SEQUENCE_FLOWS = False

ANONYMIZE_DIAGRAM_DATA = False
ANONYMIZE_ASSOCIATION_TITLES = False

FLOW_STENCILS = {"SequenceFlow", "MessageFlow"}


def _upload_enabled() -> bool:
    """Return whether to upload to Signavio.

    Env var DIAGRAMFORGE_UPLOAD overrides the module-level
    DIAGRAMFORGE_UPLOAD constant.
    """
    raw = os.getenv("DIAGRAMFORGE_UPLOAD")
    if raw is None:
        return DIAGRAMFORGE_UPLOAD
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def anonymize_diagram(diagram_json: dict, names_on_flows: bool = False) -> dict:
    """Replace all resource IDs and names with random 5-char strings.

    Flows (SequenceFlow, MessageFlow) also receive the generated ID as their
    resource ID. Their name is cleared unless names_on_flows=True.
    """
    resource_id_mapping: dict[str, str] = {}

    def _generate_id() -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=5))

    def _iter_child_shapes(child_shapes: list[dict]) -> None:
        for shape in child_shapes:
            new_id = _generate_id()
            resource_id_mapping[shape["resourceId"]] = new_id
            shape["resourceId"] = new_id

            props = shape.get("properties", {})
            stencil_id = shape.get("stencil", {}).get("id", "")

            if stencil_id in FLOW_STENCILS:
                if not names_on_flows:
                    props["name"] = ""
                else:
                    props["name"] = new_id
            else:
                props["name"] = new_id

            props["documentation"] = ""
            for key in [k for k in props if k.startswith("documentation_")]:
                del props[key]

            props["description"] = ""
            for key in [k for k in props if k.startswith("description_")]:
                del props[key]

            for key in [k for k in props if k.startswith("meta-")]:
                del props[key]

            if "childShapes" in shape:
                _iter_child_shapes(shape["childShapes"])

    _iter_child_shapes(diagram_json["childShapes"])

    def _update_edges(child_shapes: list[dict]) -> None:
        for shape in child_shapes:
            if "outgoing" in shape:
                for edge in shape["outgoing"]:
                    edge["resourceId"] = resource_id_mapping[edge["resourceId"]]
            if "target" in shape:
                shape["target"]["resourceId"] = resource_id_mapping[shape["target"]["resourceId"]]
            if "childShapes" in shape:
                _update_edges(shape["childShapes"])

    _update_edges(diagram_json["childShapes"])
    return diagram_json


def anonymize_testfiles(source_dir: Path, target_dir: Path) -> list[Path]:
    """Anonymize all JSON files from source_dir into target_dir.

    Skips files whose anonymized output already exists (by filename check).
    Returns the list of anonymized file paths to process.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    result_paths: list[Path] = []

    for src_file in sorted(source_dir.glob("*.json")):
        anon_path = target_dir / src_file.name

        if anon_path.exists():
            result_paths.append(anon_path)
            continue

        with open(src_file) as f:
            data = json.load(f)

        if "model" in data and "stencil" not in data:
            data = data["model"]

        anonymized = anonymize_diagram(data, names_on_flows=ANONYMIZE_ASSOCIATION_TITLES)

        with open(anon_path, "w") as f:
            json.dump(anonymized, f, indent=2)

        log.info(f"Anonymized: {src_file.name}")
        result_paths.append(anon_path)

    return result_paths


def process_diagram(filepath: Path, output_dir: Path) -> bool:
    """Run DiagramForge on a single diagram, write the result, and upload."""
    upload_enabled = _upload_enabled()
    if upload_enabled:
        from local_testing.signavio_upload import upload_diagram

    log.info(f"Processing: {filepath.name}")

    with open(filepath) as f:
        data = json.load(f)

    if "model" in data and "stencil" not in data:
        data = data["model"]

    if ANONYMIZE_DIAGRAM_DATA:
        log.info(f"Anonymizing diagram data for: {filepath.name}")
        data = anonymize_diagram(data, names_on_flows=ANONYMIZE_ASSOCIATION_TITLES)

    try:
        forge = DiagramForge(data)
        rendered = forge.to_spm_json()
    except Exception as e:
        log.error(f"DiagramForge FAILED for {filepath.name}: {e}")
        return False

    log.info("Serializing...")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filepath.name
        with open(output_path, "w") as out_f:
            json.dump(rendered, out_f, indent=2)
        log.info(f"Output: {output_path}")
    except Exception as e:
        log.error(f"Serialize FAILED: {e}")
        return False

    log.info("Uploading to Signavio...")
    if not upload_enabled:
        log.info("Upload skipped (DIAGRAMFORGE_UPLOAD is disabled)")
        return True

    try:
        name = f"DiagramForge - {filepath.stem}"
        model_id = upload_diagram(output_path, name=name)
        log.success(f"Signavio: {name} (model: {model_id})")
    except Exception as e:
        log.error(f"Upload FAILED: {e}")

    return True


def _resolve_paths(args: list[str], active_dir: Path) -> list[Path]:
    """Resolve CLI arguments to file paths.

    Each arg can be:
    - An absolute or relative path to a .json file
    - A filename (looked up in active_dir)
    - A glob pattern matched against active_dir
    """
    paths: list[Path] = []
    for arg in args:
        p = Path(arg)
        if p.is_file():
            paths.append(p)
        elif (active_dir / p.name).is_file():
            paths.append(active_dir / p.name)
        else:
            matched = sorted(active_dir.glob(arg))
            if matched:
                paths.extend(matched)
            else:
                log.warning(f"No match for '{arg}' in {active_dir}")
    return paths


def main():
    script_dir = Path(__file__).parent
    default_input = script_dir / "testfiles"
    default_anon = script_dir / "testfiles_anonymized"
    default_active = script_dir / "testfiles_active"
    default_output = script_dir / "output"

    log.info("Anonymizing test files...")
    anonymize_testfiles(default_input, default_anon)
    default_active.mkdir(parents=True, exist_ok=True)

    args = sys.argv[1:]

    if args:
        paths = _resolve_paths(args, default_active)
        if not paths:
            log.error(f"No files resolved from arguments: {args}")
            return
    else:
        paths = sorted(default_active.glob("*.json"))
        if not paths:
            log.warning(f"No JSON files in {default_active} — add files from testfiles_anonymized/")
            return

    success = 0
    failed_paths: list[Path] = []
    for path in paths:
        if process_diagram(path, default_output):
            success += 1
        else:
            failed_paths.append(path)

    log.info(f"Done: {success} succeeded, {len(failed_paths)} failed")
    if failed_paths:
        log.warning("Failed files:")
        for p in failed_paths:
            log.warning(f"  {p.name}")


if __name__ == "__main__":
    _start = time.perf_counter()
    try:
        main()
    finally:
        _elapsed = time.perf_counter() - _start
        log.info(f"Total execution time: {_elapsed:.2f}s")
