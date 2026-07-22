from __future__ import annotations

import base64
import hashlib
import io
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from mini_articraft.agent.tools._core import (
    Tool,
    ToolContext,
    ToolResult,
    display_path,
    readable_path,
    schema,
)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
PATCH_SIZE = 32


@dataclass(frozen=True)
class ImageLimits:
    max_dimension: int
    max_patches: int


LIMITS = {
    "high": ImageLimits(max_dimension=2_048, max_patches=2_500),
    "original": ImageLimits(max_dimension=6_000, max_patches=10_000),
}
FORMAT_MIME_TYPES = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "GIF": "image/gif",
    "WEBP": "image/webp",
}


async def run(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    detail = str(args.get("detail") or "high")
    if detail not in LIMITS:
        raise ValueError("detail must be high or original")

    requested_path = readable_path(context.workspace, str(args["path"]))
    raster_path = _raster_path(requested_path)
    source_bytes = raster_path.read_bytes()
    if len(source_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(f"image exceeds {MAX_IMAGE_BYTES} bytes")

    data, mime_type, width, height = _prepare_image(
        source_bytes,
        limits=LIMITS[detail],
    )
    requested_label = display_path(context.workspace, requested_path)
    raster_label = display_path(context.workspace, raster_path)
    result = {
        "path": requested_label,
        "mime_type": mime_type,
        "bytes": len(data),
        "width": width,
        "height": height,
        "detail": detail,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if raster_path != requested_path:
        result["raster_path"] = raster_label
    image_url = f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"
    return ToolResult(
        result,
        [
            {
                "type": "input_image",
                "image_url": image_url,
                "detail": detail,
            }
        ],
    )


def _raster_path(path: Path) -> Path:
    if path.suffix.lower() != ".svg":
        return path
    companion = path.with_suffix(".svg.webp")
    if not companion.is_file():
        raise ValueError(f"SVG preview is missing: {companion.name}")
    return companion


def _prepare_image(
    data: bytes,
    *,
    limits: ImageLimits,
) -> tuple[bytes, str, int, int]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                source_format = str(source.format or "").upper()
                source.load()
                orientation = source.getexif().get(274)
                image = ImageOps.exif_transpose(source).copy()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("image dimensions exceed the supported limit") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValueError("file is not a supported PNG, JPEG, GIF, or WebP image") from exc

    mime_type = FORMAT_MIME_TYPES.get(source_format)
    if mime_type is None:
        raise ValueError("view_image supports PNG, JPEG, GIF, and WebP images")

    width, height = _output_dimensions(image.width, image.height, limits)
    if (
        source_format in {"PNG", "JPEG", "WEBP"}
        and (width, height) == image.size
        and orientation in (None, 1)
    ):
        return data, mime_type, width, height

    if image.size != (width, height):
        image = image.resize((width, height), resample=Image.Resampling.BILINEAR)

    output_format = "PNG" if source_format == "GIF" else source_format
    output = io.BytesIO()
    if output_format == "JPEG":
        image.convert("RGB").save(
            output,
            format="JPEG",
            quality=85,
            optimize=False,
            progressive=False,
        )
    elif output_format == "WEBP":
        image.convert("RGBA").save(
            output,
            format="WEBP",
            lossless=True,
            quality=100,
            method=0,
        )
    else:
        image.convert("RGBA").save(
            output,
            format="PNG",
            compress_level=9,
            optimize=False,
        )
    encoded = output.getvalue()
    return encoded, FORMAT_MIME_TYPES[output_format], width, height


def _output_dimensions(width: int, height: int, limits: ImageLimits) -> tuple[int, int]:
    width = max(1, width)
    height = max(1, height)
    if _fits(width, height, limits):
        return width, height

    scale = min(limits.max_dimension / max(width, height), 1.0)
    width = max(1, round(width * scale))
    height = max(1, round(height * scale))
    if _fits(width, height, limits):
        return width, height

    scale = math.sqrt(PATCH_SIZE**2 * limits.max_patches / width / height)
    scaled_patches_wide = width * scale / PATCH_SIZE
    scaled_patches_high = height * scale / PATCH_SIZE
    scale *= min(
        math.floor(scaled_patches_wide) / scaled_patches_wide,
        math.floor(scaled_patches_high) / scaled_patches_high,
    )
    return max(1, math.floor(width * scale)), max(1, math.floor(height * scale))


def _fits(width: int, height: int, limits: ImageLimits) -> bool:
    patches = math.ceil(width / PATCH_SIZE) * math.ceil(height / PATCH_SIZE)
    return (
        width <= limits.max_dimension
        and height <= limits.max_dimension
        and patches <= limits.max_patches
    )


TOOL = Tool(
    "view_image",
    schema(
        "view_image",
        "View a local raster image or a vendored SDK SVG preview as image input. Defaults to bounded high detail; use original only when fine detail is required.",
        {
            "path": {
                "type": "string",
                "description": "Path inside the run workspace or read-only docs/sdk tree.",
            },
            "detail": {
                "type": "string",
                "enum": ["high", "original"],
                "description": "Image detail level. Defaults to high.",
            },
        },
        ["path"],
    ),
    run,
)
