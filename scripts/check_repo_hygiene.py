from __future__ import annotations

import subprocess
import sys
from pathlib import PurePosixPath


def main() -> int:
    tracked_files = _tracked_files()
    violations = [path for path in tracked_files if _is_forbidden(path)]
    if not violations:
        return 0

    print("Tracked generated, local, or build files are not allowed:")
    for path in violations:
        print(f"  {path}")
    return 1


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
