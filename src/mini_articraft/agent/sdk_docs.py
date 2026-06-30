from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mini_articraft import package_dir

SDK_DOCS_ROOT = package_dir / "sdk" / "docs"
WORKSPACE_SDK_DOCS_ROOT = Path("docs") / "sdk"
QUICKSTART_RELATIVE_PATH = Path("common") / "00_quickstart.md"


@dataclass(frozen=True)
class SDKDoc:
    name: str
    description: str
    short_description: str | None
    relative_path: Path
    path: Path
    body: str

    @property
    def workspace_path(self) -> Path:
        return WORKSPACE_SDK_DOCS_ROOT / self.relative_path


def load_sdk_docs() -> list[SDKDoc]:
    docs: list[SDKDoc] = []
    for path in sorted(SDK_DOCS_ROOT.rglob("*.md"), key=_doc_sort_key):
        metadata, body = split_frontmatter(path.read_text(encoding="utf-8"), path=path)
        relative_path = path.relative_to(SDK_DOCS_ROOT)
        docs.append(
            SDKDoc(
                name=_required_str(metadata, "name", path),
                description=_required_str(metadata, "description", path),
                short_description=_short_description(metadata, path),
                relative_path=relative_path,
                path=path,
                body=body,
            )
        )
    _validate_docs(docs)
    return docs


def _doc_sort_key(path: Path) -> tuple[int, str]:
    relative = path.relative_to(SDK_DOCS_ROOT)
    if relative == QUICKSTART_RELATIVE_PATH:
        return (0, relative.as_posix())
    if relative.parts and relative.parts[0] == "common":
        return (1, relative.as_posix())
    return (2, relative.as_posix())


def render_sdk_quickstart_context() -> str:
    docs = load_sdk_docs()
    quickstart = _quickstart_doc(docs)
    inventory = _render_reference_inventory(docs)
    return _replace_reference_inventory(quickstart.body, inventory).strip()


def split_frontmatter(text: str, *, path: Path) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path} must start with YAML frontmatter")

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            raw_frontmatter = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :]).lstrip("\n")
            parsed = yaml.safe_load(raw_frontmatter)
            if not isinstance(parsed, dict):
                raise ValueError(f"{path} frontmatter must be a YAML mapping")
            return parsed, body

    raise ValueError(f"{path} frontmatter must end with ---")


def _required_str(metadata: dict[str, Any], field: str, path: Path) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} frontmatter field {field!r} must be a non-empty string")
    return " ".join(value.split())


def _short_description(metadata: dict[str, Any], path: Path) -> str | None:
    nested = metadata.get("metadata", {})
    if nested is None:
        return None
    if not isinstance(nested, dict):
        raise ValueError(f"{path} frontmatter field 'metadata' must be a mapping")
    value = nested.get("short-description")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{path} frontmatter field 'metadata.short-description' must be a non-empty string"
        )
    return " ".join(value.split())


def _validate_docs(docs: list[SDKDoc]) -> None:
    if not docs:
        raise ValueError(f"no SDK docs found under {SDK_DOCS_ROOT}")

    names: dict[str, Path] = {}
    for doc in docs:
        existing = names.get(doc.name)
        if existing is not None:
            raise ValueError(f"duplicate SDK doc name {doc.name!r}: {existing} and {doc.path}")
        names[doc.name] = doc.path


def _quickstart_doc(docs: list[SDKDoc]) -> SDKDoc:
    for doc in docs:
        if doc.relative_path == QUICKSTART_RELATIVE_PATH:
            return doc
    raise ValueError(f"missing SDK quickstart doc: {QUICKSTART_RELATIVE_PATH}")


def _render_reference_inventory(docs: list[SDKDoc]) -> str:
    lines = [
        "## Reference Inventory",
        "",
        "These docs are available in the run workspace. Use `read` to open a page when it is relevant.",
        "",
    ]
    for doc in docs:
        lines.append(f"- `{doc.workspace_path.as_posix()}`: {doc.description}")
    lines.extend(
        [
            "",
            "Read the exact document you need before using a helper or pattern from it.",
            "Do not load unrelated pages just because they are listed here.",
        ]
    )
    return "\n".join(lines)


def _replace_reference_inventory(body: str, inventory: str) -> str:
    marker = "## Reference Inventory"
    next_marker = "\n## Recommended Imports"
    start = body.find(marker)
    end = body.find(next_marker)
    if start == -1 or end == -1 or end <= start:
        raise ValueError("quickstart doc must contain Reference Inventory before Recommended Imports")
    return body[:start] + inventory + body[end:]
