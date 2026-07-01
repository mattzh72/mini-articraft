---
title: "Sort Examples"
source_html: "https://build123d.readthedocs.io/en/latest/topology_selection/sort_examples.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "292-300"
generated_on: "2026-07-01"
---

# Sort Examples

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 292 -->

Sort Examples

SortBy

SortBy enums are shape property shorthands which work across Shape multiple object types. SortBy is a criteria for
both sort_by and group_by.

• SortBy.LENGTH works with Edge, Wire

• SortBy.AREA works with Face, Solid

• SortBy.VOLUME works with Solid

• SortBy.RADIUS works with Edge, Face with GeomType CIRCLE, CYLINDER, SPHERE

• SortBy.DISTANCE works Vertex, Edge, Wire, Face, Solid

SortBy is often interchangeable with specific shape properties and can alternatively be used with``group_by``.

Setup

```python
from build123d import *
```

```python
with BuildPart() as part:
```

```python
    Box(5, 5, 1)
    Cylinder(2, 5)
    edges = part.edges().filter_by(lambda a: a.length == 1)
    fillet(edges, 1)
```

```python
part.wires().sort_by(SortBy.LENGTH)[:4]
```

```python
part.wires().sort_by(Wire.length)[:4]
part.wires().group_by(SortBy.LENGTH)[0]
```

<!-- PDF page 293 -->

![Extracted image from PDF page 293](../images/topology_sort_examples/p293_img001_9500181b0095.png)

```python
part.vertices().sort_by(SortBy.DISTANCE)[-2:]
```

```python
part.vertices().sort_by_distance(Vertex())[-2:]
part.vertices().group_by(Vertex().distance)[-1]
```

![Extracted image from PDF page 293](../images/topology_sort_examples/p293_img002_f1264ffe4a17.png)

<!-- PDF page 294 -->

Along Wire

Vertices selected from an edge or wire might have a useful ordering when created from a single object, but when created
from multiple objects, the ordering not useful. For example, when applying incrementing fillet radii to a list of vertices
from the face, the order is random.

Setup

```python
from build123d import *
```

```python
with BuildSketch() as along_wire:
```

```python
    Rectangle(48, 16, align=Align.MIN)
    Rectangle(16, 48, align=Align.MIN)
    Rectangle(32, 32, align=Align.MIN)
```

```python
    for i, v in enumerate(along_wire.vertices()):
```

```python
        fillet(v, i + 1)
```

![Extracted image from PDF page 294](../images/topology_sort_examples/p294_img003_19ca3afc487b.png)

Vertices may be sorted along the wire they fall on to create order. Notice the fillet radii now increase in order.

```python
    sorted_verts = along_wire.vertices().sort_by(along_wire.wire())
    for i, v in enumerate(sorted_verts):
```

```python
        fillet(v, i + 1)
```

<!-- PDF page 295 -->

![Extracted image from PDF page 295](../images/topology_sort_examples/p295_img004_a34ab83dc3c7.png)

Axis

Sorting by axis is often the most straightforward way to optimize selections. In this part we want to revolve the face
at the end around an inside edge of the completed extrusion. First, the face to extrude can be found by sorting along
x-axis and the revolution edge can be found sorting along y-axis.

Setup

```python
from build123d import *
```

```python
with BuildPart() as part:
```

```python
    with BuildSketch(Plane.YZ) as profile:
```

```python
        with BuildLine():
            l1 = FilletPolyline((16, 0), (32, 0), (32, 25), radius=12)
            l2 = FilletPolyline((16, 4), (28, 4), (28, 15), radius=8)
            Line(l1 @ 0, l2 @ 0)
            Polyline(l1 @ 1, l1 @ 1 - Vector(2, 0), l2 @ 1 + Vector(2, 0), l2 @ 1)
        make_face()
    extrude(amount=34)
```

```python
    face = part.faces().sort_by(Axis.X)[-1]
    edge = face.edges().sort_by(Axis.Y)[0]
    revolve(face, -Axis(edge), 90)
```

<!-- PDF page 296 -->

![Extracted image from PDF page 296](../images/topology_sort_examples/p296_img005_c3b1a0c18dad.png)

Distance From

A sort_by_distance can be used to sort objects by their distance from another object. Here we are sorting the boxes
by distance from the origin, using an empty Vertex (at the origin) as the reference shape to find distance to.

Setup

```python
from itertools import product
```

```python
from build123d import *
from ocp_vscode import *
```

```python
boxes = ShapeList(
```

```python
    Box(1, 1, 1).scale(0.75 if (i, j) == (1, 2) else 0.25).translate((i, j, 0))
    for i, j in product(range(-3, 4), repeat=2)
)
```

```python
boxes = boxes.sort_by_distance(Vertex())
show(*boxes, colors=ColorMap.listed(len(boxes)))
```

The example can be extended by first sorting the boxes by volume using the Solid property volume, and getting the
last (largest) box. Then, the boxes sorted by their distance from the largest box.

```python
boxes = boxes.sort_by_distance(boxes.sort_by(Solid.volume).last)
show(*boxes, colors=ColorMap.listed(len(boxes)))
```

<!-- PDF page 297 -->

![Extracted image from PDF page 297](../images/topology_sort_examples/p297_img006_6ad37d2ba5bd.png)

![Extracted image from PDF page 297](../images/topology_sort_examples/p297_img007_2e1374c15bb7.png)

<!-- PDF page 298 -->

![Extracted image from PDF page 298](../images/topology_sort_examples/p298_img008_746648351db3.png)

![Extracted image from PDF page 298](../images/topology_sort_examples/p298_img009_ed1724972ff8.png)

SortBy SortBy

![Extracted image from PDF page 298](../images/topology_sort_examples/p298_img010_49b9db093e13.png)

Along Wire Along Wire

<!-- PDF page 299 -->

![Extracted image from PDF page 299](../images/topology_sort_examples/p299_img011_bf948184d33d.png)

Axis Axis

Distance From Distance From

Group

A ShapeList can be grouped and sorted with the group_by() method based on a grouping criteria. Grouping can
be a great way to organize features without knowing the values of specific feature properties. Rather than returning a
ShapeList, group_by() returns a GroupBy, a list of ShapeList objects sorted by the grouping criteria. GroupBy
can be printed to view the members of each group, indexed like a list to retrieve a ShapeList, and be accessed using
a key with the group method. If the group keys are unknown they can be discovered with key_to_group_index.

If we want only the edges from the smallest faces by area we can get the faces, then group by SortBy.AREA. The
ShapeList of smallest faces is available from the first list index. Finally, a ShapeList has access to selectors, so
calling edges() will return a new list of all edges in the previous list.

```python
part.faces().group_by(SortBy.AREA)[0].edges())
```

![Extracted image from PDF page 299](../images/topology_sort_examples/p299_img012_e5e5076c75b0.png)

Topological Distance

topo_distance_to() creates a callable key that measures graph distance through topology rather than geometric
distance through space. It is useful when selecting features by adjacency, for example faces connected to a reference
face, or the next ring of faces after that.

Distances are measured within the shared topo_parent of the reference shape. The reference shape has distance 0,
directly adjacent shapes have distance 1, and unreachable shapes have distance inf.

<!-- PDF page 300 -->

```python
box = Box(1, 1, 1)
faces = box.faces()
top_face = faces.sort_by(Axis.Z)[-1]
```

```python
face_rings = faces.group_by(topo_distance_to(top_face))
```

```python
top = face_rings[0]
sides = face_rings[1]
bottom = face_rings[2]
```

Multiple reference shapes can be provided. This is useful for selecting all features within a topological distance from
any reference. In this example, a sphere is converted to a triangular mesh, faces near the middle of the mesh are used
as references, and all mesh faces are grouped into topological rings expanding away from that starting band.

```python
from build123d import *
from pathlib import Path
from tempfile import TemporaryDirectory
```

```python
from ocp_vscode import ColorMap, show
```

```python
mesher = Mesher()
mesher.add_shape(Sphere(1), linear_deflection=0.05, angular_deflection=1)
```

```python
with TemporaryDirectory() as tmp_dir:
    mesh_path = Path(tmp_dir) / "sphere.stl"
    mesher.write(mesh_path)
    mesh_sphere = Mesher().read(mesh_path)[0]
```

```python
sphere_faces = mesh_sphere.faces()
```

```python
vertical_groups = sphere_faces.group_by(Axis.Z)
starting_ring = vertical_groups[len(vertical_groups) // 2]
face_rings = sphere_faces.group_by(topo_distance_to(starting_ring))
```

```python
show(*face_rings, colors=ColorMap.listed(len(face_rings)))
```

The same approach can be used with edges or vertices. For example, a single edge on the mesh can be used as the
starting point for edge-distance rings.

```python
sphere_edges = mesh_sphere.edges()
reference_edge = choice(sphere_edges)
edge_rings = sphere_edges.group_by(topo_distance_to(reference_edge))
```

Examples
