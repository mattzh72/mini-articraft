from __future__ import annotations

from pathlib import Path

from mini_articraft.agent.tools._core import workspace_digest
from mini_articraft.junction_report import write_junction_report
from mini_articraft.sdk import ArticulatedObject, BoxGeometry


def _model() -> ArticulatedObject:
    model = ArticulatedObject("t")
    body = model.part("body")
    body.add(BoxGeometry((0.10, 0.10, 0.10)), name="cube", color=(0.5, 0.5, 0.6))
    # Touching neighbour: one junction. Far shape: no junction.
    body.add(BoxGeometry((0.04, 0.04, 0.04)).translate(0.07, 0.0, 0.0), name="nub")
    body.add(BoxGeometry((0.02, 0.02, 0.02)).translate(0.5, 0.0, 0.0), name="far")
    return model


def test_write_junction_report_lists_touching_pairs(tmp_path: Path) -> None:
    count = write_junction_report(_model(), tmp_path)
    text = (tmp_path / "junctions.md").read_text(encoding="utf-8")
    assert count == 1
    assert "body/cube <-> body/nub" in text
    assert "far" not in text  # 0.4m away: not a junction


def test_kinematic_interfaces_are_not_flagged_as_tangent_contact(tmp_path: Path) -> None:
    from mini_articraft.sdk import ArticulationType, CylinderGeometry, MotionLimits, Origin

    model = ArticulatedObject("t")
    body = model.part("body")
    body.add(BoxGeometry((0.10, 0.10, 0.02)), name="plate", color=(0.5, 0.5, 0.6))
    lid = model.part("lid")
    # A barrel resting tangent on the plate: grazing, but across an articulation.
    # (Child geometry is authored relative to the joint origin.)
    lid.add(CylinderGeometry(0.01, 0.06).rotate_y(1.5708), name="barrel")
    model.articulation(
        "hinge",
        ArticulationType.REVOLUTE,
        body,
        lid,
        origin=Origin(xyz=(0.0, 0.0, 0.02)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=1.0, velocity=1.0, lower=0.0, upper=1.0),
    )
    write_junction_report(model, tmp_path)
    text = (tmp_path / "junctions.md").read_text(encoding="utf-8")
    assert "body/plate <-> lid/barrel" in text  # listed as a junction
    assert "TANGENT CONTACT" not in text  # but not flagged: kinematic clearance


def test_junctions_file_does_not_change_workspace_digest(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    before = workspace_digest(tmp_path)
    (tmp_path / "junctions.md").write_text("# Junction report\n", encoding="utf-8")
    assert workspace_digest(tmp_path) == before


def test_flush_contact_flags_and_embedded_passes(tmp_path: Path) -> None:
    from mini_articraft.sdk import CylinderGeometry

    # A long leg flush against a top: zero overlap volume -> tangent, regardless of
    # how small the contact is relative to the leg's total surface.
    flush = ArticulatedObject("t")
    table = flush.part("table")
    table.add(BoxGeometry((0.60, 0.40, 0.02)).translate(0, 0, 0.71), name="top")
    table.add(CylinderGeometry(0.025, 0.70).translate(0.25, 0.15, 0.35), name="leg")
    write_junction_report(flush, tmp_path)
    assert "TANGENT CONTACT" in (tmp_path / "junctions.md").read_text(encoding="utf-8")

    # The same leg embedded 10mm into the top: real shared volume -> passes.
    embedded = ArticulatedObject("t")
    table = embedded.part("table")
    table.add(BoxGeometry((0.60, 0.40, 0.02)).translate(0, 0, 0.71), name="top")
    table.add(CylinderGeometry(0.025, 0.71).translate(0.25, 0.15, 0.355), name="leg")
    write_junction_report(embedded, tmp_path)
    text = (tmp_path / "junctions.md").read_text(encoding="utf-8")
    assert "TANGENT CONTACT" not in text
    assert "overlap" in text
