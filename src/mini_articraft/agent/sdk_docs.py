from __future__ import annotations

from pathlib import Path

from mini_articraft import package_dir

SDK_DOCS_ROOT = package_dir / "sdk" / "docs"
PRELOADED_DOCS = (
    Path("common") / "00_quickstart.md",
    Path("common") / "40_testing.md",
)


def render_sdk_context() -> str:
    parts: list[str] = []
    for relative_path in PRELOADED_DOCS:
        path = SDK_DOCS_ROOT / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"missing SDK doc: {relative_path.as_posix()}")
        parts.append(
            f"## docs/sdk/{relative_path.as_posix()}\n\n"
            f"{path.read_text(encoding='utf-8').strip()}"
        )
    return "\n\n".join(parts)
