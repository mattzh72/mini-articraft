from __future__ import annotations

import base64
import mimetypes
from typing import Any

from mini_articraft.agent.tools._core import Tool, ToolContext, display_path, readable_path, schema

MAX_IMAGE_BYTES = 256_000


async def run(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    path = readable_path(context.workspace, str(args["path"]))
    data = path.read_bytes()
    path_label = display_path(context.workspace, path)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if mime_type.startswith("image/"):
        chunk = data[:MAX_IMAGE_BYTES]
        return {
            "path": path_label,
            "mime_type": mime_type,
            "bytes": len(data),
            "truncated": len(data) > len(chunk),
            "base64": base64.b64encode(chunk).decode("ascii"),
        }

    offset = int(args.get("offset") or 1)
    limit = args.get("limit")
    if offset < 1:
        raise ValueError("offset must be >= 1")
    if limit is not None and int(limit) < 1:
        raise ValueError("limit must be >= 1")

    lines = data.decode("utf-8", errors="replace").splitlines()
    selected = lines[offset - 1 :] if limit is None else lines[offset - 1 : offset - 1 + int(limit)]
    return {
        "path": path_label,
        "text": "\n".join(f"L{i}: {line}" for i, line in enumerate(selected, start=offset)),
    }


TOOL = Tool(
    "read",
    schema(
        "read",
        "Read a file from the run workspace or read-only SDK docs under docs/sdk. Text files return line-numbered text with optional offset and limit; images return MIME type, byte size, and capped base64.",
        {
            "path": {
                "type": "string",
                "description": "Path to the file inside the run workspace. Relative paths are resolved against the workspace.",
            },
            "offset": {
                "type": "integer",
                "description": "1-based line offset for text reads. Defaults to 1.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of text lines to return. Omit to read from offset to EOF.",
            },
        },
        ["path"],
    ),
    run,
    supports_parallel=True,
)
