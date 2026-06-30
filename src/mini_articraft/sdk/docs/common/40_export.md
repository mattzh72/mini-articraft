---
name: sdk-export
description: Read this when you need to understand export_object, ExportResult, part file formats, CadQuery shape handling, or the model.json manifest.
metadata:
  short-description: Export helper and manifest layout.
---

# Export

## Purpose

Use `export_object(...)` to write CadQuery part files and a small JSON manifest
for an `ArticulatedObject`.

The local compile worker calls this helper automatically. Call it directly only
for standalone scripts or tests.

## Import

```python
from mini_articraft.sdk import ExportResult, export_object
```

## Recommended Surface

- `export_object(...)`
- `ExportResult`

## Export Helper

### `export_object(...)`

```python
export_object(
    obj: ArticulatedObject,
    output_dir: pathlib.Path | str,
    *,
    part_format: str = "step",
) -> ExportResult
```

- `obj`: model to validate and export.
- `output_dir`: directory where files should be written.
- `part_format`: one of `"step"`, `"stp"`, or `"stl"`.

The helper calls `obj.validate()` before writing files.

## Result

### `ExportResult`

```python
ExportResult(
    root: pathlib.Path,
    manifest: pathlib.Path,
    parts: dict[str, pathlib.Path],
)
```

- `root`: output directory.
- `manifest`: path to `model.json`.
- `parts`: map from part name to exported part file.

## Output Layout

For this call:

```python
result = export_object(object_model, "result", part_format="step")
```

The output layout is:

```text
result/
  model.json
  parts/
    base.step
    lid.step
```

Part filenames are derived from part names. Characters outside
`A-Z`, `a-z`, `0-9`, `_`, `.`, and `-` are replaced with `_`.

## Manifest Shape

`model.json` contains the model dictionary plus exported file paths.

```json
{
  "name": "example_box_lid",
  "parts": [
    {
      "name": "base",
      "shape_type": "Workplane"
    },
    {
      "name": "lid",
      "shape_type": "Workplane"
    }
  ],
  "joints": [
    {
      "name": "base_to_lid",
      "type": "revolute",
      "parent": "base",
      "child": "lid",
      "origin": {
        "xyz": [0.0, 0.0, 0.0],
        "rpy": [0.0, 0.0, 0.0]
      },
      "axis": [0.0, 0.0, 1.0],
      "limits": {
        "lower": 0.0,
        "upper": 1.2,
        "effort": 1.0,
        "velocity": 1.0
      }
    }
  ],
  "files": {
    "parts": {
      "base": "parts/base.step",
      "lid": "parts/lid.step"
    }
  }
}
```

## CadQuery Shape Handling

Each part shape must be one of:

- `cadquery.Workplane`
- `cadquery.Shape`
- `cadquery.Assembly`

Export behavior:

- `Assembly` values are saved directly through CadQuery.
- `Shape` values are exported directly.
- `Workplane` values are resolved with `vals()`.
- A `Workplane` with one shape exports that shape.
- A `Workplane` with several shapes exports a CadQuery compound.
- A `Workplane` with no exportable shapes raises an error.

## Example

```python
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, Origin, export_object


model = ArticulatedObject("hinged_panel")
base = model.part("base", cq.Workplane("XY").box(0.3, 0.2, 0.04))
panel = model.part("panel", cq.Workplane("XY").box(0.26, 0.16, 0.02))

model.revolute(
    "base_to_panel",
    base,
    panel,
    origin=Origin(xyz=(-0.13, 0.0, 0.04)),
    axis=(0.0, -1.0, 0.0),
    limits=(0.0, 1.57),
)

result = export_object(model, "result")
print(result.manifest)
print(result.parts["base"])
```

## See Also

- `30_articulated_object.md` for validation rules.
- `35_joints.md` for joint metadata written into the manifest.
