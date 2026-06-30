from __future__ import annotations

import cadquery as cq

from mini_articraft.environments.export import export_object
from mini_articraft.sdk import ArticulatedObject


def test_export_object_writes_part_files_and_manifest(tmp_path) -> None:
    obj = ArticulatedObject("hinge")
    base = obj.part("base", cq.Workplane("XY").box(1.0, 1.0, 0.2))
    door = obj.part("door", cq.Workplane("XY").box(0.8, 0.1, 1.0))
    obj.revolute("base_to_door", base, door, axis=(0.0, 0.0, 2.0), limits=(0.0, 1.57))

    result = export_object(obj, tmp_path)

    assert result.manifest.exists()
    assert result.parts["base"].exists()
    assert result.parts["door"].exists()
    assert "parts/base.step" in result.manifest.read_text()
