"""Score agent-produced rigs against hand-written expected articulation.

GT is cheap: for each test object we write down joint COUNT, TYPE, and (where
unambiguous) AXIS direction. Greedy-match produced joints to expected; report
type accuracy + axis angle error. Run after agent_group runs.

Run: .venv/bin/python examples/eval_rigs.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# axis=None -> direction not scored (e.g. scissors pivot normal is mesh-specific)
EXPECTED = {
    "drawer": [{"type": "prismatic", "axis": (0, -1, 0)}] * 3,
    "scissors": [{"type": "revolute", "axis": None}],
    "laptop_sharp": [{"type": "revolute", "axis": (1, 0, 0)}],
    "oven": [{"type": "revolute", "axis": (1, 0, 0)},      # door folds down
             {"type": "prismatic", "axis": (0, -1, 0)}],   # bottom drawer
    "toolbox": [{"type": "revolute", "axis": (1, 0, 0)}],
    # cabinet: VERIFIED BY LOOKING (bookcase: open shelves + 2 bottom doors).
    # earlier GT of 5 drawers + 2 doors was copied from a hallucinating run.
    "cabinet": [{"type": "revolute", "axis": None}] * 2,
    "microwave_oven": [{"type": "revolute", "axis": (0, 0, 1)}],  # side-hinged door
}


def axis_err_deg(a, b) -> float:
    a = np.asarray(a, float); a /= np.linalg.norm(a) + 1e-12
    b = np.asarray(b, float); b /= np.linalg.norm(b) + 1e-12
    return float(np.degrees(np.arccos(np.clip(abs(a @ b), 0, 1))))  # sign-agnostic


def joints_from_usd(path: Path) -> list[dict]:
    """Read joints back out of an exported USD (axis = localRot0 * +X)."""
    from pxr import Gf, Usd, UsdPhysics
    stage = Usd.Stage.Open(str(path))
    out = []
    for prim in stage.Traverse():
        for cls, jtype in ((UsdPhysics.PrismaticJoint, "prismatic"),
                           (UsdPhysics.RevoluteJoint, "revolute")):
            j = cls(prim)
            if not j or not prim.IsA(cls):
                continue
            rot = j.GetLocalRot0Attr().Get() or Gf.Quatf(1.0)
            ax = Gf.Rotation(Gf.Quatd(rot)).TransformDir(Gf.Vec3d(1, 0, 0))
            out.append({"name": prim.GetName(), "type": jtype,
                        "axis": [ax[0], ax[1], ax[2]]})
    return out


def find_rig(name: str, root: str = "data/group_runs") -> Path | None:
    hits = sorted(Path(root).rglob("rig.json")) + sorted(Path(root).rglob("*.usda"))
    for h in hits:
        d = h.parent if h.parent.name != "out" else h.parent.parent
        if d.name == name:
            return h
    return None


def score(name: str, expected: list[dict], root: str = "data/group_runs") -> dict:
    p = find_rig(name, root)
    if p is None:
        return {"object": name, "status": "NO RUN"}
    if p.suffix == ".usda":
        joints = joints_from_usd(p)
    else:
        joints = json.loads(p.read_text())["joints"]
    got_n, want_n = len(joints), len(expected)
    unmatched = list(joints)
    rows, type_ok, axis_errs = [], 0, []
    for e in expected:
        # match by type first, then smallest axis error
        cands = [j for j in unmatched if j["type"] == e["type"]] or unmatched
        if not cands:
            rows.append(("MISSING", e["type"], None))
            continue
        if e["axis"] is not None:
            j = min(cands, key=lambda j: axis_err_deg(j["axis"], e["axis"]))
        else:
            j = cands[0]
        unmatched.remove(j)
        ok = j["type"] == e["type"]
        type_ok += ok
        err = axis_err_deg(j["axis"], e["axis"]) if e["axis"] is not None else None
        if err is not None:
            axis_errs.append(err)
        rows.append((j["name"], "ok" if ok else f"type={j['type']}!={e['type']}",
                     None if err is None else round(err, 1)))
    return {"object": name, "joints": f"{got_n}/{want_n}",
            "type_acc": f"{type_ok}/{want_n}",
            "axis_err_deg": [r[2] for r in rows if r[2] is not None],
            "extra_joints": len(unmatched), "detail": rows}


def main():
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "data/group_runs"
    print(f"scoring runs under {root}\n")
    print(f"{'object':14s} {'joints':8s} {'types':7s} {'axis err (deg)':16s} extra")
    for name, exp in EXPECTED.items():
        s = score(name, exp, root)
        if s.get("status") == "NO RUN":
            print(f"{name:14s} -- no run --")
            continue
        errs = ", ".join(f"{e:.0f}" for e in s["axis_err_deg"]) or "-"
        print(f"{s['object']:14s} {s['joints']:8s} {s['type_acc']:7s} {errs:16s} {s['extra_joints']}")


if __name__ == "__main__":
    main()
