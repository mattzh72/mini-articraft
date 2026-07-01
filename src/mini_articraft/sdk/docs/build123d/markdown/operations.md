---
title: "Operations"
source_html: "https://build123d.readthedocs.io/en/latest/operations.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "274-287"
generated_on: "2026-07-01"
---

# Operations

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 274 -->

1.11 Operations

Operations are functions that take objects as inputs and transform them into new objects. For example, a 2D Sketch
can be extruded to create a 3D Part. All operations are Python functions which can be applied using both the Algebra
and Builder APIs. It’s important to note that objects created by operations are not affected by Locations, meaning
their position is determined solely by the input objects used in the operation.

Here are a couple ways to use extrude(), in Builder and Algebra mode:

```python
with BuildPart() as cylinder:
```

```python
    with BuildSketch():
```

```python
        Circle(radius)
    extrude(amount=height)
```

```python
cylinder = extrude(Circle(radius), amount=height)
```

The following table summarizes all of the available operations. Operations marked as 1D are applicable to BuildLine
and Algebra Curve, 2D to BuildSketch and Algebra Sketch, 3D to BuildPart and Algebra Part.

Operation            Description                 0D   1D  2D   3D   Example

add()                Add object to builder            ✓   ✓    ✓    16
bounding_box()       Add bounding box as Shape        ✓   ✓    ✓
chamfer()            Bevel Vertex or Edge                 ✓    ✓    9
draft()              Add a draft taper to a part               ✓    Cast Bearing Unit
extrude()            Draw 2D Shape into 3D                     ✓    3
fillet()             Radius Vertex or Edge                ✓    ✓    9
full_round()         Round-off Face along given Edge      ✓         24-SPO-06 Buffer Stand
loft()               Create 3D Shape from sections             ✓    24
make_brake_formed()  Create sheet metal parts                  ✓
make_face()          Create a Face from Edges             ✓         4
make_hull()          Create Convex Hull from Edges        ✓
mirror()             Mirror about Plane               ✓   ✓    ✓    15
offset()             Inset or outset Shape            ✓   ✓    ✓    25
project()            Project points, lines or Faces ✓ ✓   ✓
project_workplane()  Create workplane for projection
revolve()            Swing 2D Shape about Axis                 ✓    23
scale()              Change size of Shape             ✓   ✓    ✓
section()            Generate 2D slices from 3D Shape          ✓
split()              Divide object by Plane           ✓   ✓    ✓    27
sweep()              Extrude 1/2D section(s) along path   ✓    ✓    14
thicken()            Expand 2D section(s)                      ✓
trace()              Convert lines to faces               ✓

The following table summarizes all of the selectors that can be used within the scope of a Builder. Note that they will
extract objects from the builder that is currently within scope without it being explicitly referenced.

<!-- PDF page 275 -->

Builder
Selector    Description                  Line  Sketch  Part

edge()      Select edge from current builder ✓ ✓       ✓
edges()     Select edges from current builder ✓ ✓      ✓
face()      Select face from current builder   ✓       ✓
faces()     Select faces from current builder  ✓       ✓
solid()     Select solid from current builder          ✓
solids()    Select solids from current builder         ✓
vertex()    Select vertex from current builder ✓ ✓     ✓
vertices()  Select vertices from current builder ✓ ✓   ✓
wire()      Select wire from current builder ✓ ✓       ✓
wires()     Select wires from current builder ✓ ✓      ✓

1.11.1 Reference

add(objects: ~build123d.topology.one_d.Edge | ~build123d.topology.one_d.Wire | ~build123d.topology.two_d.Face
| ~build123d.topology.three_d.Solid | ~build123d.topology.composite.Compound |
~build123d.build_common.Builder | ~collections.abc.Iterable[~build123d.topology.one_d.Edge |
~build123d.topology.one_d.Wire | ~build123d.topology.two_d.Face | ~build123d.topology.three_d.Solid |
~build123d.topology.composite.Compound | ~build123d.build_common.Builder], rotation: float |
~build123d.geometry.Rotation | tuple[float, float, float] | None = None, clean: bool = True, mode:
~build123d.build_enums.Mode = <Mode.ADD>) →Compound

Generic Object: Add Object to Part or Sketch

Add an object to a builder.

BuildPart:

Edges and Wires are added to pending_edges. Compounds of Face are added to pending_faces. Solids or
Compounds of Solid are combined into the part.

BuildSketch:

Edges and Wires are added to pending_edges. Compounds of Face are added to sketch.

BuildLine:

Edges and Wires are added to line.

Parameters

```python
              • objects (Edge | Wire | Face | Solid | Compound or Iterable of) – objects
                to add
```

• rotation (float | RotationLike, optional) – rotation angle for sketch, rotation
about each axis for part. Defaults to None.

• clean – Remove extraneous internal structure. Defaults to True.

bounding_box(objects: ~build123d.topology.shape_core.Shape |
~collections.abc.Iterable[~build123d.topology.shape_core.Shape] | None = None, mode:
~build123d.build_enums.Mode = <Mode.PRIVATE>) →Sketch | Part

Generic Operation: Add Bounding Box

Applies to: BuildSketch and BuildPart

Add the 2D or 3D bounding boxes of the object sequence

Parameters

<!-- PDF page 276 -->

• objects (Shape or Iterable of) – objects to create bbox for

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

chamfer(objects: Edge | Vertex | Iterable[Edge | Vertex], length: float, length2: float | None = None, angle: float |
None = None, reference: Edge | Face | None = None) →Sketch | Part

Generic Operation: chamfer

Applies to 2 and 3 dimensional objects.

Chamfer the given sequence of edges or vertices.

Parameters

```python
              • objects (Edge | Vertex or Iterable of) – edges or vertices to chamfer
```

• length (float) – chamfer size

• length2 (float, optional) – asymmetric chamfer size. Defaults to None.

• angle (float, optional) – chamfer angle in degrees. Defaults to None.

• reference (Edge | Face) – identifies the side where length is measured. Edge(s) must be
part of the face. Vertex/Vertices must be part of edge

Raises

• ValueError – no objects provided

• ValueError – objects must be Edges

• ValueError – objects must be Vertices

• ValueError – Only one of length2 or angle should be provided

• ValueError – reference can only be used in conjunction with length2 or angle

draft(faces: Face | Iterable[Face], neutral_plane: Plane, angle: float) →Part

Part Operation: draft

Apply a draft angle to the given faces of the part

Parameters

• faces – Faces to which the draft should be applied.

• neutral_plane – Plane defining the neutral direction and position.

• angle – Draft angle in degrees.

extrude(to_extrude: ~build123d.topology.two_d.Face | ~build123d.topology.composite.Sketch | None = None,
amount: float | None = None, dir: ~build123d.geometry.Vector | tuple[float, float] | tuple[float, float, float]
| ~collections.abc.Sequence[float] | None = None, until: ~build123d.build_enums.Until | None = None,
target: ~build123d.topology.three_d.Solid | ~build123d.topology.composite.Compound | None = None,
both: bool = False, taper: float = 0.0, clean: bool = True, mode: ~build123d.build_enums.Mode =
<Mode.ADD>) →Part

Part Operation: extrude

Extrude a sketch or face by an amount or until another object.

Parameters

```python
              • to_extrude (Union[Face, Sketch], optional) – object to extrude. Defaults to None.
```

• amount (float, optional) – distance to extrude, sign controls direction. Defaults to
None.

<!-- PDF page 277 -->

• dir (VectorLike, optional) – direction. Defaults to None.

• until (Until, optional) – extrude limit. Defaults to None.

• target (Shape, optional) – extrude until target. Defaults to None.

• both (bool, optional) – extrude in both directions. Defaults to False.

• taper (float, optional) – taper angle. Defaults to 0.0.

• clean (bool, optional) – Remove extraneous internal structure. Defaults to True.

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

Raises

• ValueError – No object to extrude

• ValueError – No target object

Returns

extruded object

Return type

Part

fillet(objects: Edge | Vertex | Iterable[Edge | Vertex], radius: float) →Sketch | Part | Curve

Generic Operation: fillet

Applies to 2 and 3 dimensional objects.

Fillet the given sequence of edges or vertices. Note that vertices on either end of an open line will be automatically
skipped.

Parameters

```python
              • objects (Edge | Vertex or Iterable of) – edges or vertices to fillet
```

• radius (float) – fillet size - must be less than 1/2 local width

Raises

• ValueError – no objects provided

• ValueError – objects must be Edges

• ValueError – objects must be Vertices

• ValueError – nothing to fillet

full_round(edge: ~build123d.topology.one_d.Edge, invert: bool = False, voronoi_point_count: int = 100, mode:
~build123d.build_enums.Mode = <Mode.REPLACE>) →tuple[Sketch, Vector, float]

Sketch Operation: full_round

Given an edge from a Face/Sketch, modify the face by replacing the given edge with the arc of the Voronoi largest
empty circle that will fit within the Face. This “rounds off” the end of the object.

Parameters

• edge (Edge) – target Edge to remove

• invert (bool, optional) – make the arc concave instead of convex. Defaults to False.

• voronoi_point_count (int, optional) – number of points along each edge used to
create the voronoi vertices as potential locations for the center of the largest empty circle.
Defaults to 100.

• mode (Mode, optional) – combination mode. Defaults to Mode.REPLACE.

<!-- PDF page 278 -->

Raises

ValueError – Invalid geometry

Returns

the modified shape

Return type

Sketch

loft(sections: ~build123d.topology.two_d.Face | ~build123d.topology.composite.Sketch |
~collections.abc.Iterable[~build123d.topology.zero_d.Vertex | ~build123d.topology.two_d.Face |
~build123d.topology.composite.Sketch] | None = None, ruled: bool = False, clean: bool = True, mode:
~build123d.build_enums.Mode = <Mode.ADD>) →Part

Part Operation: loft

Loft the pending sketches/faces, across all workplanes, into a solid.

Parameters

• sections (Vertex, Face, Sketch) – slices to loft into object. If not provided, pend-
ing_faces will be used. If vertices are to be used, a vertex can be the first, last, or first and
last elements.

• ruled (bool, optional) – discontiguous layer tangents. Defaults to False.

• clean (bool, optional) – Remove extraneous internal structure. Defaults to True.

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

make_brake_formed(thickness: float, station_widths: float | ~collections.abc.Iterable[float], line:
~build123d.topology.one_d.Edge | ~build123d.topology.one_d.Wire |
~build123d.topology.composite.Curve | None = None, side: ~build123d.build_enums.Side =
<Side.LEFT>, kind: ~build123d.build_enums.Kind = <Kind.ARC>, clean: bool = True,
mode: ~build123d.build_enums.Mode = <Mode.ADD>) →Part

Create a part typically formed with a sheet metal brake from a single outline. The line parameter describes how
the material is to be bent. Either a single width value or a width value at each vertex or station is provided to
control the width of the end part. Note that if multiple values are provided there must be one for each vertex and
that the resulting part is composed of linear segments.

Parameters

• thickness (float) – sheet metal thickness

• station_widths (Union[float, Iterable[float]]) – width of part at each vertex or
a single value. Note that this width is perpendicular to the provided line/plane.

```python
              • line (Union[Edge, Wire, Curve], optional) – outline of part. Defaults to None.
```

• side (Side, optional) – offset direction. Defaults to Side.LEFT.

• kind (Kind, optional) – offset intersection type. Defaults to Kind.ARC.

• clean (bool, optional) – clean the resulting solid. Defaults to True.

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

Raises

• ValueError – invalid line type

• ValueError – not line provided

• ValueError – line not suitable

• ValueError – incorrect # of width values

<!-- PDF page 279 -->

Returns

sheet metal part

Return type

Part

make_face(edges: ~build123d.topology.one_d.Edge | ~build123d.topology.one_d.Wire |
~build123d.topology.composite.Curve | ~collections.abc.Iterable[~build123d.topology.one_d.Edge |
~build123d.topology.one_d.Wire | ~build123d.topology.composite.Curve] | None = None, mode:
~build123d.build_enums.Mode = <Mode.ADD>) →Sketch

Sketch Operation: make_face

Create a face from the given perimeter edges.

Parameters

```python
              • edges (Edge | Wire | Curve) – perimeter edges that must combine into a single closed
                wire. Defaults to all sketch pending edges.
```

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

make_hull(edges: ~build123d.topology.one_d.Edge | ~collections.abc.Iterable[~build123d.topology.one_d.Edge] |
None = None, mode: ~build123d.build_enums.Mode = <Mode.ADD>) →Sketch

Sketch Operation: make_hull

Create a face from the convex hull of the given edges

Parameters

• edges (Edge, optional) – sequence of edges to hull. Defaults to all sketch pending edges.

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

mirror(objects: ~build123d.topology.one_d.Edge | ~build123d.topology.one_d.Wire |
~build123d.topology.two_d.Face | ~build123d.topology.composite.Compound |
~build123d.topology.composite.Curve | ~build123d.topology.composite.Sketch |
~build123d.topology.composite.Part | ~collections.abc.Iterable[~build123d.topology.one_d.Edge |
~build123d.topology.one_d.Wire | ~build123d.topology.two_d.Face |
~build123d.topology.composite.Compound | ~build123d.topology.composite.Curve |
~build123d.topology.composite.Sketch | ~build123d.topology.composite.Part] | None = None, about:
~build123d.geometry.Plane = Plane((0, 0, 0), (1, 0, 0), (0, -1, 0)), mode: ~build123d.build_enums.Mode =
<Mode.ADD>) →Curve | Sketch | Part | Compound

Generic Operation: mirror

Applies to 1, 2, and 3 dimensional objects.

Mirror a sequence of objects over the given plane.

Parameters

```python
              • objects (Edge | Face | Compound or Iterable of) – objects to mirror
```

• about (Plane, optional) – reference plane. Defaults to “XZ”.

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

Raises

ValueError – missing objects

<!-- PDF page 280 -->

offset(objects: ~build123d.topology.one_d.Edge | ~build123d.topology.two_d.Face |
~build123d.topology.three_d.Solid | ~build123d.topology.composite.Compound |
~collections.abc.Iterable[~build123d.topology.one_d.Edge | ~build123d.topology.two_d.Face |
~build123d.topology.three_d.Solid | ~build123d.topology.composite.Compound] | None = None, amount:
float = 0, openings: ~build123d.topology.two_d.Face | list[~build123d.topology.two_d.Face] | None =
None, kind: ~build123d.build_enums.Kind = <Kind.ARC>, side: ~build123d.build_enums.Side =
<Side.BOTH>, closed: bool = True, min_edge_length: float | None = None, mode:
~build123d.build_enums.Mode = <Mode.REPLACE>) →Curve | Sketch | Part | Compound

Generic Operation: offset

Applies to 1, 2, and 3 dimensional objects.

Offset the given sequence of Edges, Faces, Compound of Faces, or Solids. The kind parameter controls the shape
of the transitions. For Solid objects, the openings parameter allows selected faces to be open, like a hollow box
with no lid.

Parameters

```python
              • objects (Edge | Face | Solid | Compound or Iterable of) – objects to offset
```

• amount (float) – positive values external, negative internal

• openings (list[Face], optional) – Defaults to None.

• kind (Kind, optional) – transition shape. Defaults to Kind.ARC.

• side (Side, optional) – side to place offset. Defaults to Side.BOTH.

• closed (bool, optional) – if Side!=BOTH, close the LEFT or RIGHT offset. Defaults
to True.

• min_edge_length (float, optional) – repair degenerate edges generated by offset by
eliminating edges of minimum length in offset wire. Defaults to None.

• mode (Mode, optional) – combination mode. Defaults to Mode.REPLACE.

Raises

• ValueError – missing objects

• ValueError – Invalid object type

project(objects: ~build123d.topology.one_d.Edge | ~build123d.topology.two_d.Face |
~build123d.topology.one_d.Wire | ~build123d.geometry.Vector | ~build123d.topology.zero_d.Vertex |
~collections.abc.Iterable[~build123d.topology.one_d.Edge | ~build123d.topology.two_d.Face |
~build123d.topology.one_d.Wire | ~build123d.geometry.Vector | ~build123d.topology.zero_d.Vertex] |
None = None, workplane: ~build123d.geometry.Plane | None = None, target:
~build123d.topology.three_d.Solid | ~build123d.topology.composite.Compound |
~build123d.topology.composite.Part | None = None, mode: ~build123d.build_enums.Mode =
<Mode.ADD>) →Curve | Sketch | Compound | ShapeList[Vector]

Generic Operation: project

Applies to 0, 1, and 2 dimensional objects.

Project the given objects or points onto a BuildLine or BuildSketch workplane in the direction of the normal of
that workplane. When projecting onto a sketch a Face(s) are generated while Edges are generated for BuildLine.
Will only use the first if BuildSketch has multiple active workplanes. In algebra mode a workplane must be
provided and the output is either a Face, Curve, Sketch, Compound, or ShapeList[Vector].

Note that only if mode is not Mode.PRIVATE only Faces can be projected into BuildSketch and Edge/Wires into
BuildLine.

Parameters

<!-- PDF page 281 -->

```python
              • objects (Edge | Face | Wire | VectorLike | Vertex or Iterable of) – ob-
                jects or points to project
```

• workplane (Plane, optional) – screen workplane

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

Raises

• ValueError – project doesn’t accept group_by

• ValueError – Either a workplane must be provided or a builder must be active

• ValueError – Points and faces can only be projected in PRIVATE mode

• ValueError – Edges, wires and points can only be projected in PRIVATE mode

• RuntimeError – BuildPart doesn’t have a project operation

project_workplane(origin: Vector | tuple[float, float] | tuple[float, float, float] | Sequence[float] | Vertex, x_dir:
Vector | tuple[float, float] | tuple[float, float, float] | Sequence[float] | Vertex, projection_dir:
Vector | tuple[float, float] | tuple[float, float, float] | Sequence[float], distance: float) →Plane

Part Operation: project_workplane

Return a plane to be used as a BuildSketch or BuildLine workplane with a known origin and x direction. The
plane’s origin will be the projection of the provided origin (in 3D space). The plane’s x direction will be the
projection of the provided x_dir (in 3D space).

Parameters

• origin (Union[VectorLike, Vertex]) – origin in 3D space

• x_dir (Union[VectorLike, Vertex]) – x direction in 3D space

• projection_dir (VectorLike) – projection direction

• distance (float) – distance from origin to workplane

Raises

• RuntimeError – Not suitable for BuildLine or BuildSketch

• ValueError – x_dir perpendicular to projection_dir

Returns

workplane aligned for projection

Return type

Plane

revolve(profiles: ~build123d.topology.two_d.Face | ~collections.abc.Iterable[~build123d.topology.two_d.Face] |
None = None, axis: ~build123d.geometry.Axis = Axis((0, 0, 0), (0, 0, 1)), revolution_arc: float = 360.0,
clean: bool = True, mode: ~build123d.build_enums.Mode = <Mode.ADD>) →Part

Part Operation: Revolve

Revolve the profile or pending sketches/face about the given axis. Note that the most common use case is when
the axis is in the same plane as the face to be revolved but this isn’t required.

Parameters

• profiles (Face, optional) – 2D profile(s) to revolve.

• axis (Axis, optional) – axis of rotation. Defaults to Axis.Z.

• revolution_arc (float, optional) – angular size of revolution. Defaults to 360.0.

• clean (bool, optional) – Remove extraneous internal structure. Defaults to True.

<!-- PDF page 282 -->

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

Raises

ValueError – Invalid axis of revolution

scale(objects: ~build123d.topology.shape_core.Shape |
~collections.abc.Iterable[~build123d.topology.shape_core.Shape] | None = None, by: float | tuple[float,
float, float] = 1, about: ~build123d.geometry.Vector | tuple[float, float] | tuple[float, float, float] |
~collections.abc.Sequence[float] | None = None, mode: ~build123d.build_enums.Mode =
<Mode.REPLACE>) →Curve | Sketch | Part | Compound

Generic Operation: scale

Applies to 1, 2, and 3 dimensional objects.

Scale a sequence of objects. Note that when scaling non-uniformly across the three axes, the type of the under-
lying object may change to bspline from line, circle, etc.

Parameters

```python
              • objects (Edge | Face | Compound | Solid or Iterable of) – objects to scale
```

• by (float | tuple[float, float, float]) – scale factor

• about (VectorLike, optional) – point to scale about. Defaults to each object’s location
position.

• mode (Mode, optional) – combination mode. Defaults to Mode.REPLACE.

Raises

ValueError – missing objects

section(obj: ~build123d.topology.composite.Part | None = None, section_by: ~build123d.geometry.Plane |
~collections.abc.Iterable[~build123d.geometry.Plane] = Plane((0, 0, 0), (1, 0, 0), (0, -1, 0)), height: float
= 0.0, clean: bool = True, mode: ~build123d.build_enums.Mode = <Mode.PRIVATE>) →Sketch

Part Operation: section

Slices current part at the given height by section_by or current workplane(s).

Parameters

• obj (Part, optional) – object to section. Defaults to None.

• section_by (Plane, optional) – plane(s) to section object. Defaults to None.

• height (float, optional) – workplane offset. Defaults to 0.0.

• clean (bool, optional) – Remove extraneous internal structure. Defaults to True.

• mode (Mode, optional) – combination mode. Defaults to Mode.INTERSECT.

split(objects: ~build123d.topology.one_d.Edge | ~build123d.topology.one_d.Wire |
~build123d.topology.two_d.Face | ~build123d.topology.three_d.Solid |
~collections.abc.Iterable[~build123d.topology.one_d.Edge | ~build123d.topology.one_d.Wire |
~build123d.topology.two_d.Face | ~build123d.topology.three_d.Solid] | None = None, bisect_by:
~build123d.geometry.Plane | ~build123d.topology.two_d.Face | ~build123d.topology.two_d.Shell =
Plane((0, 0, 0), (1, 0, 0), (0, -1, 0)), keep: ~build123d.build_enums.Keep = <Keep.TOP>, mode:
~build123d.build_enums.Mode = <Mode.REPLACE>)

Generic Operation: split

Applies to 1, 2, and 3 dimensional objects.

Bisect object with plane and keep either top, bottom or both.

Parameters

<!-- PDF page 283 -->

```python
              • objects (Edge | Wire | Face | Solid or Iterable of)
```

```python
              • bisect_by (Plane | Face, optional) – plane to segment part. Defaults to Plane.XZ.
```

• keep (Keep, optional) – selector for which segment to keep. Defaults to Keep.TOP.

• mode (Mode, optional) – combination mode. Defaults to Mode.REPLACE.

Raises

ValueError – missing objects

sweep(sections: ~build123d.topology.composite.Compound | ~build123d.topology.one_d.Edge |
~build123d.topology.one_d.Wire | ~build123d.topology.two_d.Face | ~build123d.topology.three_d.Solid |
~collections.abc.Iterable[~build123d.topology.composite.Compound | ~build123d.topology.one_d.Edge |
~build123d.topology.one_d.Wire | ~build123d.topology.two_d.Face | ~build123d.topology.three_d.Solid] |
None = None, path: ~build123d.topology.composite.Curve | ~build123d.topology.one_d.Edge |
~build123d.topology.one_d.Wire | ~collections.abc.Iterable[~build123d.topology.one_d.Edge] | None =
None, multisection: bool = False, is_frenet: bool = False, transition: ~build123d.build_enums.Transition =
<Transition.TRANSFORMED>, normal: ~build123d.geometry.Vector | tuple[float, float] | tuple[float, float,
float] | ~collections.abc.Sequence[float] | None = None, binormal: ~build123d.topology.one_d.Edge |
~build123d.topology.one_d.Wire | None = None, clean: bool = True, mode: ~build123d.build_enums.Mode
= <Mode.ADD>) →Part | Sketch

Generic Operation: sweep

Sweep pending 1D or 2D objects along path.

Parameters

```python
              • sections (Compound | Edge | Wire | Face | Solid) – cross sections to sweep into
                object
```

```python
              • path (Curve | Edge | Wire, optional) – path to follow. Defaults to context pend-
                ing_edges.
```

• multisection (bool, optional) – sweep multiple on path. Defaults to False.

• is_frenet (bool, optional) – use frenet algorithm. Defaults to False.

• transition (Transition, optional) – discontinuity handling option. Defaults to Tran-
sition.TRANSFORMED.

• normal (VectorLike, optional) – fixed normal. Defaults to None.

```python
              • binormal (Edge | Wire, optional) – guide rotation along path. Defaults to None.
```

• clean (bool, optional) – Remove extraneous internal structure. Defaults to True.

• mode (Mode, optional) – combination. Defaults to Mode.ADD.

thicken(to_thicken: ~build123d.topology.two_d.Face | ~build123d.topology.composite.Sketch | None = None,
amount: float | None = None, normal_override: ~build123d.geometry.Vector | tuple[float, float] |
tuple[float, float, float] | ~collections.abc.Sequence[float] | None = None, both: bool = False, clean: bool
= True, mode: ~build123d.build_enums.Mode = <Mode.ADD>) →Part

Part Operation: thicken

Create a solid(s) from a potentially non planar face(s) by thickening along the normals.

Parameters

```python
              • to_thicken (Union[Face, Sketch], optional) – object to thicken. Defaults to None.
```

• amount (float) – distance to extrude, sign controls direction.

<!-- PDF page 284 -->

• normal_override (Vector, optional) – The normal_override vector can be used to in-
dicate which way is ‘up’, potentially flipping the face normal direction such that many faces
with different normals all go in the same direction (direction need only be +/- 90 degrees
from the face normal). Defaults to None.

• both (bool, optional) – thicken in both directions. Defaults to False.

• clean (bool, optional) – Remove extraneous internal structure. Defaults to True.

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

Raises

• ValueError – No object to extrude

• ValueError – No target object

Returns

extruded object

Return type

Part

trace(lines: ~build123d.topology.one_d.Edge | ~build123d.topology.one_d.Wire |
~build123d.topology.composite.Curve | ~collections.abc.Iterable[~build123d.topology.one_d.Edge |
~build123d.topology.one_d.Wire | ~build123d.topology.composite.Curve] | None = None, line_width: float =
1, mode: ~build123d.build_enums.Mode = <Mode.ADD>) →Sketch

Sketch Operation: trace

Convert edges, wires or pending edges into faces by sweeping a perpendicular line along them.

Parameters

```python
              • lines (Curve | Edge | Wire | Iterable[Curve | Edge | Wire]], optional)
                – lines to trace. Defaults to sketch pending edges.
```

• line_width (float, optional) – Defaults to 1.

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

Raises

ValueError – No objects to trace

Returns

Traced lines

Return type

Sketch

edge(self , select: ~build123d.build_enums.Select = <Select.ALL>) →Edge

Return Edge

Return an edge.

Parameters

```python
            select (Select, optional) – Edge selector. Defaults to Select.ALL.
```

Returns

Edge extracted

Return type

Edge

<!-- PDF page 285 -->

edges(self , select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Edge]

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

face(self , select: ~build123d.build_enums.Select = <Select.ALL>) →Face

Return Face

Return a face.

Parameters

```python
            select (Select, optional) – Face selector. Defaults to Select.ALL.
```

Returns

Face extracted

Return type

Face

faces(self , select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Face]

Return Faces

Return either all or the faces created during the last operation.

Parameters

```python
            select (Select, optional) – Face selector. Defaults to Select.ALL.
```

Returns

Faces extracted

Return type

ShapeList[Face]

solid(self , select: ~build123d.build_enums.Select = <Select.ALL>) →Solid

Return Solid

Return a solid.

Parameters

```python
            select (Select, optional) – Solid selector. Defaults to Select.ALL.
```

Returns

Solid extracted

Return type

Solid

solids(self , select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Solid]

Return Solids

Return either all or the solids created during the last operation.

Parameters

```python
            select (Select, optional) – Solid selector. Defaults to Select.ALL.
```

<!-- PDF page 286 -->

Returns

Solids extracted

Return type

ShapeList[Solid]

vertex(self , select: ~build123d.build_enums.Select = <Select.ALL>) →Vertex

Return Vertex

Return a vertex.

Parameters

```python
            select (Select, optional) – Vertex selector. Defaults to Select.ALL.
```

Returns

Vertex extracted

Return type

Vertex

vertices(self , select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Vertex]

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

wire(self , select: ~build123d.build_enums.Select = <Select.ALL>) →Wire

Return Wire

Return a wire.

Parameters

```python
            select (Select, optional) – Wire selector. Defaults to Select.ALL.
```

Returns

Wire extracted

Return type

Wire

wires(self , select: ~build123d.build_enums.Select = <Select.ALL>) →ShapeList[Wire]

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
