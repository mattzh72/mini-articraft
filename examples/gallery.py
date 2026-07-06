"""Assemble overnight results: stack each object's opening montage + write a
summary of which produced valid USD rigs."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pxr import Usd, UsdPhysics

RUNS = Path("data/agent_runs")


def usd_summary(usd_path: Path) -> str:
    try:
        stage = Usd.Stage.Open(str(usd_path))
        bodies = [p.GetName() for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
        joints = [(p.GetName(), p.GetTypeName().split(":")[-1])
                  for p in stage.Traverse()
                  if p.IsA(UsdPhysics.RevoluteJoint) or p.IsA(UsdPhysics.PrismaticJoint)]
        return f"{len(bodies)} bodies {bodies}, joints {joints}"
    except Exception as exc:
        return f"(unreadable: {exc})"


def main() -> None:
    rows = []
    lines = ["# Overnight agent-articulation results\n"]
    for d in sorted(RUNS.iterdir()):
        if not d.is_dir():
            continue
        open_png = d / "open.png"
        usd = d / "object.usda"
        summ = usd_summary(usd) if usd.exists() else "NO USD"
        lines.append(f"- **{d.name}**: {summ}")
        if open_png.exists():
            img = np.asarray(Image.open(open_png).convert("RGB"))
            pim = Image.fromarray(img)
            ImageDraw.Draw(pim).text((4, 4), d.name, fill=(150, 0, 0))
            rows.append(np.asarray(pim))
    if rows:
        w = max(r.shape[1] for r in rows)
        rows = [np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows]
        Image.fromarray(np.concatenate(rows, axis=0)).save(RUNS / "GALLERY.png")
        lines.append(f"\nGallery: `{RUNS / 'GALLERY.png'}`")
    (RUNS / "RESULTS.md").write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nwrote {RUNS/'GALLERY.png'} + {RUNS/'RESULTS.md'}")


if __name__ == "__main__":
    main()
