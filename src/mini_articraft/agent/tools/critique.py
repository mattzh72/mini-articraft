from __future__ import annotations

import base64
import io
import json
import math
from typing import Any

import websockets

from mini_articraft.agent.tools._core import Tool, ToolContext, schema
from mini_articraft.agent.tools.inspect_view import _load_model, render_png
from mini_articraft.settings import get_settings

_RESPONSES_URL = "wss://api.openai.com/v1/responses"
# Default overview: four orbits so the critic sees every side, plus the front.
_GRID_ANGLES = ((40.0, 18.0), (130.0, 18.0), (220.0, 18.0), (310.0, 18.0))


def _grid(pngs: list[bytes], columns: int = 2) -> bytes:
    from PIL import Image

    tiles = [Image.open(io.BytesIO(p)).convert("RGB") for p in pngs]
    tile_w = max(t.width for t in tiles)
    tile_h = max(t.height for t in tiles)
    rows = math.ceil(len(tiles) / columns)
    sheet = Image.new("RGB", (tile_w * columns, tile_h * rows), (0, 0, 0))
    for index, tile in enumerate(tiles):
        row, col = divmod(index, columns)
        sheet.paste(tile, (col * tile_w, row * tile_h))
    buffer = io.BytesIO()
    sheet.save(buffer, format="png")
    return buffer.getvalue()


def _render_views(model: Any, args: dict[str, Any]) -> bytes:
    """A single focused frame if the maker framed one, else a 2x2 overview grid."""
    pose = args.get("pose")
    color_by_shape = bool(args.get("color_by_shape", True))
    focused = any(args.get(key) is not None for key in ("target", "only", "azimuth", "elevation"))
    if focused:
        return render_png(
            model,
            azimuth=float(args.get("azimuth", 45.0)),
            elevation=float(args.get("elevation", 20.0)),
            zoom=float(args.get("zoom", 1.0)),
            target=args.get("target"),
            only=args.get("only"),
            pose=pose,
            labels=False,
            color_by_shape=color_by_shape,
            width=640,
        )
    tiles = [
        render_png(
            model,
            azimuth=az,
            elevation=el,
            zoom=1.0,
            target=None,
            only=None,
            pose=pose,
            labels=False,
            color_by_shape=color_by_shape,
            width=480,
        )
        for az, el in _GRID_ANGLES
    ]
    return _grid(tiles)


def _prompt(goal: str, question: str | None, colored: bool) -> str:
    coloring = (
        " Each separate part is drawn in a distinct bright color, so a mechanism built from "
        "many small pieces shows up as many colors."
        if colored
        else ""
    )
    ask = f'\n\nThe builder specifically asks: "{question}"' if question else ""
    return (
        "You are a product-design reviewer. An AI built this 3D model from the request:\n"
        f'"{goal}"\n\n'
        "You are seeing it for the first time and know nothing about how it was built."
        f"{coloring} Judge it as a real manufactured product would look. Call out anything "
        "jarring: exposed brackets, knuckles, or hardware a molded product would hide; parts "
        "that float or do not touch; crude stand-in shapes; a mechanism that does not read as "
        "the real thing. Be specific and blunt, and do not pad praise for parts that look "
        f"fine.{ask}\n\nEnd with the 1-3 most important fixes, most important first."
    )


async def _ask_critic(prompt_text: str, image_png: bytes) -> tuple[str, dict[str, Any]]:
    settings = get_settings()
    data_url = "data:image/png;base64," + base64.b64encode(image_png).decode("ascii")
    request = {
        "type": "response.create",
        "model": settings.openai_model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ],
        "reasoning": {"effort": settings.openai_reasoning_effort},
        "max_output_tokens": 4000,
        "store": False,
    }
    async with websockets.connect(
        _RESPONSES_URL,
        additional_headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        max_size=None,
    ) as socket:
        await socket.send(json.dumps(request))
        while True:
            event = json.loads(await socket.recv())
            kind = event.get("type")
            if kind in {"response.completed", "response.incomplete"}:
                response = event["response"]
                parts = [
                    part["text"]
                    for item in response.get("output", [])
                    if item.get("type") == "message"
                    for part in item.get("content", [])
                    if part.get("type") == "output_text"
                ]
                return "".join(parts), response.get("usage") or {}
            if kind in {"error", "response.failed"}:
                raise RuntimeError(json.dumps(event)[:300])


async def run(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    model = _load_model(context.workspace)
    image = _render_views(model, args)
    goal = context.task_prompt or "an object matching its intended design"
    text, usage = await _ask_critic(
        _prompt(goal, args.get("question"), bool(args.get("color_by_shape", True))), image
    )
    return {"critique": text, "usage": usage}


TOOL = Tool(
    "critique",
    schema(
        "critique",
        (
            "Get a second opinion from a fresh reviewer that has never seen your build. It "
            "renders the object and judges it cold as a real product, catching jarring, "
            "over-built, or floating geometry you may be too close to notice. Call it after a "
            "successful compile. By default it shows a four-angle overview; pass `target`, "
            "`only`, `azimuth`/`elevation`, or `pose` to point the reviewer at a specific part "
            "or an actuated pose, and `question` to ask about a specific worry. Returns a blunt "
            "defect list; fix what it flags and compile again."
        ),
        {
            "question": {
                "type": "string",
                "description": "An optional specific worry to ask the reviewer about.",
            },
            "target": {
                "type": ["string", "array"],
                "description": "A part or shape name (or [x,y,z]) to frame for a focused review.",
            },
            "only": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Render only these part or shape names.",
            },
            "azimuth": {"type": "number", "description": "Orbit angle for a focused view."},
            "elevation": {"type": "number", "description": "Up/down angle for a focused view."},
            "zoom": {"type": "number", "description": "1.0 fits the target; <1 zooms in."},
            "pose": {
                "type": "object",
                "description": "Joint name -> value, to actuate articulation before review.",
            },
            "color_by_shape": {
                "type": "boolean",
                "description": "Color each shape a distinct hue so separate pieces stand out (default true).",
            },
        },
        [],
    ),
    run,
)
