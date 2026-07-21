"""Write a junction report: every attachment junction, measured for tangent contact.

An overall impression hides bad joints -- a partially attached handle, a floating
hinge block. After a successful compile this module lists every pair of touching (or
nearly touching) shapes with their shared overlap volume, and flags TANGENT CONTACT:
pieces that touch at a point, line, or bare surface (near-zero overlap volume)
instead of being embedded past the surface and welded. Touching is not fusion --
fused pieces share material, so their volumes must overlap.

Pairs that span an articulation's parent/child interface are listed but never
flagged: a hinge barrel in its sleeve needs running clearance -- tangency there is
the mechanism, not a defect.
"""

from __future__ import annotations

from pathlib import Path

from mini_articraft.sdk import ArticulatedObject
from mini_articraft.sdk._collision import (
    MeshCollisionKernel,
    _distance_entries,
    _mesh_intersection_volume,
)

JUNCTION_FILE = "junctions.md"
_JUNCTION_GAP_TOL = 0.002  # a pair this close is an attachment junction
_MAX_LISTED = 40
# Fused pieces share material: overlap below this volume is tangency, not fusion.
# 20 mm^3 is a ~2.7 mm cube -- far below any deliberate embed, far above the
# sliver overlaps that mesh tessellation produces at grazing contact.
_FUSION_VOLUME = 2.0e-8  # m^3


def write_junction_report(model: ArticulatedObject, workspace: Path) -> int:
    """Write ``junctions.md`` into the workspace; return the junction count."""
    kernel = MeshCollisionKernel(model, mesh_tolerance=0.0012)
    entries = kernel._all_entries({})
    junctions: list[tuple[float, str, str, str, bool]] = []
    for index, entry_a in enumerate(entries):
        for entry_b in entries[index + 1 :]:
            query = _distance_entries(entry_a, entry_b, max_contacts=4)
            if query.distance > _JUNCTION_GAP_TOL:
                continue
            name_a = f"{entry_a.part_name}/{entry_a.shape_name}"
            name_b = f"{entry_b.part_name}/{entry_b.shape_name}"
            overlap, tangent = _overlap(entry_a, entry_b)
            junctions.append((query.distance, name_a, name_b, overlap, tangent))

    junctions.sort(key=lambda item: item[0])
    # Pairs spanning an articulation are kinematic interfaces with intended clearance.
    kinematic_pairs = {
        frozenset((articulation.parent, articulation.child))
        for articulation in getattr(model, "articulations", [])
    }
    flags = [
        f"- TANGENT CONTACT: {name_a} <-> {name_b} ({overlap}) -- it touches at a point, "
        "line, or bare surface, which is touching, not fusion. Embed the piece past the "
        "surface so the volumes overlap, then weld; the bead fills the seam"
        for _, name_a, name_b, overlap, tangent in junctions
        if tangent
        and frozenset((name_a.split("/")[0], name_b.split("/")[0])) not in kinematic_pairs
    ]
    lines = [
        "# Junction report (rest pose)",
        "",
        f"{len(junctions)} junctions. A whole-object impression hides bad joints -- check",
        "each junction below, and fix or justify every flag, before you conclude the",
        "object is done:",
        "",
    ]
    if flags:
        lines += ["## Flags (fix or justify these)", "", *flags, ""]
    for distance, name_a, name_b, overlap, _ in junctions[:_MAX_LISTED]:
        contact = overlap if distance <= 0.0 else f"gap {distance * 1000:.1f}mm"
        lines.append(f"- {name_a} <-> {name_b} ({contact})")
    if len(junctions) > _MAX_LISTED:
        lines.append(f"- ... {len(junctions) - _MAX_LISTED} more omitted (closest listed first)")
    (workspace / JUNCTION_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(junctions)


def _overlap(entry_a, entry_b) -> tuple[str, bool]:
    """The pair's shared overlap volume, and whether it is tangency (no real overlap)."""
    volume = _mesh_intersection_volume(entry_a.world_mesh, entry_b.world_mesh)
    if volume is None:
        return "contact", False  # non-watertight mesh: cannot judge, fail open
    if volume < _FUSION_VOLUME:
        return f"overlap {volume * 1e9:.0f}mm3 -- effectively none", True
    return f"overlap {volume * 1e9:.0f}mm3", False
