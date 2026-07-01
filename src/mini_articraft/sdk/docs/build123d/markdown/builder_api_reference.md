---
title: "Builder Common API Reference"
source_html: "https://build123d.readthedocs.io/en/latest/builder_api_reference.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "381-387"
generated_on: "2026-07-01"
---

# Builder Common API Reference

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 381 -->

1.21 Builder Common API Reference

The following are common to all the builders.

1.21.1 Selector Methods

Builder.vertices(select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Vertex]

Return Vertices

Return either all or the vertices created during the last operation.

Parameters

```python
            select (Select, optional) – Vertex selector. Defaults to Select.ALL.
```

Returns

Vertices extracted

Return type

ShapeList[Vertex]

Builder.faces(select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Face]

Return Faces

Return either all or the faces created during the last operation.

<!-- PDF page 382 -->

Parameters

```python
            select (Select, optional) – Face selector. Defaults to Select.ALL.
```

Returns

Faces extracted

Return type

ShapeList[Face]

Builder.edges(select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Edge]

Return Edges

Return either all or the edges created during the last operation.

Parameters

```python
            select (Select, optional) – Edge selector. Defaults to Select.ALL.
```

Returns

Edges extracted

Return type

ShapeList[Edge]

Builder.wires(select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Wire]

Return Wires

Return either all or the wires created during the last operation.

Parameters

```python
            select (Select, optional) – Wire selector. Defaults to Select.ALL.
```

Returns

Wires extracted

Return type

ShapeList[Wire]

Builder.solids(select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Solid]

Return Solids

Return either all or the solids created during the last operation.

Parameters

```python
            select (Select, optional) – Solid selector. Defaults to Select.ALL.
```

Returns

Solids extracted

Return type

ShapeList[Solid]

1.21.2 Enums

```python
class Align(value)
```

Align object about Axis

```python
     CENTER = 2
```

```python
     MAX = 3
```

```python
     MIN = 1
```

<!-- PDF page 383 -->

```python
     NONE = None
```

```python
class CenterOf(value)
```

Center Options

```python
     BOUNDING_BOX = 3
```

```python
     GEOMETRY = 1
```

```python
     MASS = 2
```

```python
class FontStyle(value)
```

Text Font Styles

```python
     BOLD = 2
```

```python
     BOLDITALIC = 4
```

```python
     ITALIC = 3
```

```python
     REGULAR = 1
```

```python
class GeomType(value)
```

CAD geometry object type

```python
     BEZIER = 6
```

```python
     BSPLINE = 7
```

```python
     CIRCLE = 12
```

```python
     CONE = 3
```

```python
     CYLINDER = 2
```

```python
     ELLIPSE = 13
```

```python
     EXTRUSION = 9
```

```python
     HYPERBOLA = 14
```

```python
     LINE = 11
```

```python
     OFFSET = 10
```

```python
     OTHER = 16
```

```python
     PARABOLA = 15
```

```python
     PLANE = 1
```

```python
     REVOLUTION = 8
```

```python
     SPHERE = 4
```

```python
     TORUS = 5
```

```python
class Keep(value)
```

Split options

<!-- PDF page 384 -->

```python
     ALL = 1
```

```python
     BOTH = 3
```

```python
     BOTTOM = 2
```

```python
     INSIDE = 4
```

```python
     OUTSIDE = 5
```

```python
     TOP = 6
```

```python
class Kind(value)
```

Offset corner transition

```python
     ARC = 1
```

```python
     INTERSECTION = 2
```

```python
     TANGENT = 3
```

```python
class Mode(value)
```

Combination Mode

```python
     ADD = 1
```

```python
     INTERSECT = 3
```

```python
     PRIVATE = 5
```

```python
     REPLACE = 4
```

```python
     SUBTRACT = 2
```

```python
class Select(value)
```

Selector scope - all, last operation or new objects

```python
     ALL = 1
```

```python
     LAST = 2
```

```python
     NEW = 3
```

```python
class SortBy(value)
```

Sorting criteria

```python
     AREA = 3
```

```python
     DISTANCE = 5
```

```python
     LENGTH = 1
```

```python
     RADIUS = 2
```

```python
     VOLUME = 4
```

```python
class Transition(value)
```

Sweep discontinuity handling option

```python
     RIGHT = 1
```

<!-- PDF page 385 -->

```python
     ROUND = 2
```

```python
     TRANSFORMED = 3
```

```python
class Until(value)
```

Extrude limit

```python
     FIRST = 4
```

```python
     LAST = 2
```

```python
     NEXT = 1
```

```python
     PREVIOUS = 3
```

1.21.3 Locations

class Locations(*pts: Vector | tuple[float, float] | tuple[float, float, float] | Sequence[float] | Vertex | Location |
Face | Plane | Axis | Iterable[Vector | tuple[float, float] | tuple[float, float, float] |
Sequence[float] | Vertex | Location | Face | Plane | Axis])

Location Context: Push Points

Creates a context of locations for Part or Sketch

Parameters

```python
            pts   (Union[VectorLike, Vertex, Location, Face, Plane, Axis] or iterable
            of same) – sequence of points to push
```

Variables

local_locations (list{Location}) – locations relative to workplane

```python
     local_locations
```

values independent of workplanes

class GridLocations(x_spacing: float, y_spacing: float, x_count: int, y_count: int, align:
~build123d.build_enums.Align | tuple[~build123d.build_enums.Align,
~build123d.build_enums.Align] = (<Align.CENTER>, <Align.CENTER>))

Location Context: Rectangular Array

Creates a context of rectangular array of locations for Part or Sketch

Parameters

• x_spacing (float) – horizontal spacing

• y_spacing (float) – vertical spacing

• x_count (int) – number of horizontal points

• y_count (int) – number of vertical points

```python
              • align (Union[Align, tuple[Align, Align]], optional) – align min, center, or
                max of object. Defaults to (Align.CENTER, Align.CENTER).
```

Variables

• x_spacing (float) – horizontal spacing

• y_spacing (float) – vertical spacing

• x_count (int) – number of horizontal points

• y_count (int) – number of vertical points

<!-- PDF page 386 -->

```python
              • align (Union[Align, tuple[Align, Align]]) – align min, center, or max of object.
```

• local_locations (list{Location}) – locations relative to workplane

Raises

ValueError – Either x or y count must be greater than or equal to one.

```python
     local_locations
```

values independent of workplanes

```python
     max
```

top right corner

```python
     min
```

bottom left corner

```python
     size
```

size of the grid

class HexLocations(radius: float, x_count: int, y_count: int, major_radius: bool = False, align:
~build123d.build_enums.Align | tuple[~build123d.build_enums.Align,
~build123d.build_enums.Align] = (<Align.CENTER>, <Align.CENTER>))

Location Context: Hex Array

Creates a context of hexagon array of locations for Part or Sketch. When creating hex locations for an array of
circles, set radius to the radius of the circle plus one half the spacing between the circles.

Parameters

• radius (float) – distance from origin to vertices (major), or optionally from the origin to
side (minor or apothem) with major_radius = False

• x_count (int) – number of points ( > 0 )

• y_count (int) – number of points ( > 0 )

• major_radius (bool) – If True the radius is the major radius, else the radius is the minor
radius (also known as inscribed radius). Defaults to False.

```python
              • align (Union[Align, tuple[Align, Align]], optional) – align min, center, or
                max of object. Defaults to (Align.CENTER, Align.CENTER).
```

Variables

• radius (float) – distance from origin to vertices (major), or optionally from the origin to
side (minor or apothem) with major_radius = False

• apothem (float) – radius of the inscribed circle, also known as minor radius

• x_count (int) – number of points ( > 0 )

• y_count (int) – number of points ( > 0 )

• major_radius (bool) – If True the radius is the major radius, else the radius is the minor
radius (also known as inscribed radius).

```python
              • align (Union[Align, tuple[Align, Align]]) – align min, center, or max of object.
```

• diagonal (float) – major radius

• local_locations (list{Location}) – locations relative to workplane

Raises

ValueError – Spacing and count must be > 0

<!-- PDF page 387 -->

```python
     local_locations
```

values independent of workplanes

class PolarLocations(radius: float, count: int, start_angle: float = 0.0, angular_range: float = 360.0, rotate:
bool = True, endpoint: bool = False)

Location Context: Polar Array

Creates a context of polar array of locations for Part or Sketch

Parameters

• radius (float) – array radius

• count (int) – Number of points to push

• start_angle (float, optional) – angle to first point from +ve X axis. Defaults to 0.0.

• angular_range (float, optional) – magnitude of array from start angle. Defaults to
360.0.

• rotate (bool, optional) – Align locations with arc tangents. Defaults to True.

• endpoint (bool, optional) – If True, start_angle + angular_range is the last sample.
Otherwise, it is not included. Defaults to False.

Variables

local_locations (list{Location}) – locations relative to workplane

Raises

ValueError – Count must be greater than or equal to 1

```python
     local_locations
```

values independent of workplanes
