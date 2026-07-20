from __future__ import annotations

import subprocess
import sys
from pathlib import Path, PurePosixPath

import yaml


class _UniqueKeyLoader(yaml.SafeLoader):
    """A SafeLoader that rejects duplicate mapping keys."""


def _reject_duplicate_keys(loader: yaml.Loader, node: yaml.MappingNode) -> dict:
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            raise yaml.YAMLError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _reject_duplicate_keys,
)


def main() -> int:
    workflow_errors = _check_workflows()
    for error in workflow_errors:
        print(error)

    tracked_files = _tracked_files()
    violations = [path for path in tracked_files if _is_forbidden(path)]
    if not violations and not workflow_errors:
        return 0

    for path in violations:
        print(f"  {path}")
    return 1


def _check_workflows() -> list[str]:
    errors: list[str] = []
    for path in sorted(Path(".github/workflows").glob("*.yml")):
        try:
            with path.open(encoding="utf-8") as file:
                yaml.load(file, Loader=_UniqueKeyLoader)
        except yaml.YAMLError as exc:
            errors.append(f"invalid workflow file {path}: {exc}")
    return errors


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _is_forbidden(path: str) -> bool:
    if path == "runs/.gitkeep":
        return False

    pure_path = PurePosixPath(path)
    parts = pure_path.parts
    name = pure_path.name

    if name == ".DS_Store":
        return True
    if name.endswith(".log"):
        return True
    if path.startswith("runs/"):
        return True
    if any(part in _FORBIDDEN_DIRECTORIES for part in parts):
        return True
    return any(part.endswith(".egg-info") for part in parts)


_FORBIDDEN_DIRECTORIES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
}


if __name__ == "__main__":
    sys.exit(main())
