---
title: "Topology Selection and Exploration"
source_html: "https://build123d.readthedocs.io/en/latest/topology_selection.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "287-292"
generated_on: "2026-07-01"
---

# Topology Selection and Exploration

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 287 -->

1.12 Topology Selection and Exploration

Topology is the structure of build123d geometric features and traversing the topology of a part is often required to spec-
ify objects for an operation or to locate a CAD feature. Selectors allow selection of topology objects into a ShapeList.
Operators are powerful methods further explore and refine a ShapeList for subsequent operations.

1.12.1 Selectors

Selectors provide methods to extract all or a subset of a feature type in the referenced object. These methods select
Edges, Faces, Solids, Vertices, or Wires in Builder objects or from Shape objects themselves. All of these methods
return a ShapeList, which is a subclass of list and may be sorted, grouped, or filtered by Operators.

Overview

Selector    Criteria         Applicability                   Description

vertices()  ALL, LAST        BuildLine, BuildSketch, BuildPart Vertex extraction
edges()     ALL, LAST, NEW   BuildLine, BuildSketch, BuildPart Edge extraction
wires()     ALL, LAST        BuildLine, BuildSketch, BuildPart Wire extraction
faces()     ALL, LAST        BuildSketch, BuildPart          Face extraction
solids()    ALL, LAST        BuildPart                       Solid extraction

Both shape objects and builder objects have access to selector methods to select all of a feature as long as they can
contain the feature being selected.

```python
# In context
with BuildSketch() as context:
```

```python
    Rectangle(1, 1)
    context.edges()
```

```python
    # Build context implicitly has access to the selector
    edges()
```

```python
# Taking the sketch out of context
context.sketch.edges()
```

```python
# Create sketch out of context
Rectangle(1, 1).edges()
```

Select In Build Context

Build contexts track the last operation and their selector methods can take Select as criteria to specify a subset of
features to extract. By default, a selector will select ALL of a feature, while LAST selects features created or altered by
the most recent operation. edges() can uniquely specify NEW to only select edges created in the last operation which
neither existed in the referenced object before the last operation, nor the modifying object.

s Important

```python
 Select as selector criteria is only valid for builder objects!
 # In context
 with BuildPart() as context:
```

```python
     Box(2, 2, 1)
```

<!-- PDF page 288 -->

```python
     Cylinder(1, 2)
     context.edges(Select.LAST)
```

```python
 # Does not work out of context!
 context.part.edges(Select.LAST)
 (Box(2, 2, 1) + Cylinder(1, 2)).edges(Select.LAST)
```

Create a simple part to demonstrate selectors. Select using the default criteria Select.ALL. Specifying Select.ALL
for the selector is not required.

```python
with BuildPart() as part:
```

```python
    Box(5, 5, 1)
    Cylinder(1, 5)
```

```python
    part.vertices()
    part.edges()
    part.faces()
```

```python
    # Is the same as
    part.vertices(Select.ALL)
    part.edges(Select.ALL)
    part.faces(Select.ALL)
```

![Extracted image from PDF page 288](../images/topology_selection/p288_img001_50bcf4d8b4d5.png)

Fig. 1: The default Select.ALL features

Select features changed in the last operation with criteria Select.LAST.

```python
with BuildPart() as part:
```

```python
    Box(5, 5, 1)
    Cylinder(1, 5)
```

```python
    part.vertices(Select.LAST)
    part.edges(Select.LAST)
    part.faces(Select.LAST)
```

Select only new edges from the last operation with Select.NEW. This option is only available for a ShapeList of
edges!

```python
with BuildPart() as part:
```

```python
    Box(5, 5, 1)
    Cylinder(1, 5)
```

```python
    part.edges(Select.NEW)
```

<!-- PDF page 289 -->

![Extracted image from PDF page 289](../images/topology_selection/p289_img002_ff5eb09926f9.png)

Fig. 2: Select.LAST features

![Extracted image from PDF page 289](../images/topology_selection/p289_img003_884ab70bce19.png)

Fig. 3: Select.NEW edges where box and cylinder intersect

This only returns new edges which are not reused from Box or Cylinder, in this case where the objects intersect. But
what happens if the objects don’t intersect and all the edges are reused?

```python
with BuildPart() as part:
```

```python
    Box(5, 5, 1, align=(Align.CENTER, Align.CENTER, Align.MAX))
    Cylinder(2, 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
```

```python
    part.edges(Select.NEW)
```

![Extracted image from PDF page 289](../images/topology_selection/p289_img004_1447dd1e8f2c.png)

Fig. 4: Select.NEW edges when box and cylinder don’t intersect

No edges are selected! Unlike the previous example, the Edge between the Box and Cylinder objects is an edge reused
from the Cylinder. Think of Select.NEW as a way to select only completely new edges created by the operation.

Note

Chamfer and fillet modify the current object, but do not have new edges via Select.NEW.

<!-- PDF page 290 -->

```python
 with BuildPart() as part:
```

```python
     Box(5, 5, 1)
     Cylinder(1, 5)
     edges = part.edges().filter_by(lambda a: a.length == 1)
     fillet(edges, 1)
```

```python
     part.edges(Select.NEW)
```

![Extracted image from PDF page 290](../images/topology_selection/p290_img005_985b73606912.png)

Fig. 5: Left, Select.NEW returns no edges after fillet. Right, Select.LAST

Select New Edges In Algebra Mode

The utility method new_edges compares one or more shape objects to a another “combined” shape object and returns
the edges new to the combined shape. new_edges is available both Algebra mode or Builder mode, but is necessary
in Algebra Mode where Select.NEW is unavailable

```python
box = Box(5, 5, 1)
circle = Cylinder(2, 5)
part = box + circle
edges = new_edges(box, circle, combined=part)
```

![Extracted image from PDF page 290](../images/topology_selection/p290_img006_ba57669ca738.png)

new_edges can also find edges created during a chamfer or fillet operation by comparing the object before the operation
to the “combined” object.

```python
box = Box(5, 5, 1)
circle = Cylinder(2, 5)
part_before = box + circle
edges = part_before.edges().filter_by(lambda a: a.length == 1)
part = fillet(edges, 1)
edges = new_edges(part_before, combined=part)
```

<!-- PDF page 291 -->

![Extracted image from PDF page 291](../images/topology_selection/p291_img007_e5e5076c75b0.png)

1.12.2 Operators

Operators provide methods refine a ShapeList of features isolated by a selector to further specify feature(s). These
methods can sort, group, or filter ShapeList objects and return a modified ShapeList, or in the case of group_by(),
GroupBy, a list of ShapeList objects accessible by index or key.

Overview

Method              Criteria                          Description

Sort ShapeList by criteria

sort_by()           Axis, Edge, Wire, SortBy, callable,
property

Group ShapeList by criteria

sort_by_distance()  Shape, VectorLike                 Sort ShapeList by distance from criteria
group_by()          Axis, Edge, Wire, SortBy, callable,
property

Filter ShapeList by criteria

filter_by()         Axis, Plane, GeomType, callable, prop-
erty

filter_by_position() Axis                             Filter ShapeList by Axis & mix / max
values

Operator methods take criteria to refine ShapeList. Broadly speaking, the criteria fall into the following categories,
though not all operators take all criteria:

• Geometric objects: Axis, Plane

• Topological objects: Edge, Wire

• Enums: SortBy, GeomType

• Properties, eg: Face.area, Edge.length

```python
   • Callable, eg: lambda e: e.is_interior == 1, lambda f: len(f.edges()) >= 3, Vertex().
     distance, topo_distance_to()
```

Sort

A ShapeList can be sorted with the sort_by() and sort_by_distance() methods based on a sorting criteria.
Sorting is a critical step when isolating individual features as a ShapeList from a selector is typically unordered.

Here we want to capture some vertices from the object furthest along X: All the vertices are first captured with the
vertices() selector, then sort by Axis.X. Finally, the vertices can be captured with a list slice for the last 4 list items,
as the items are sorted from least to greatest X position. Remember, ShapeList is a subclass of list, so any list slice
can be used.

```python
part.vertices().sort_by(Axis.X)[-4:]
```

<!-- PDF page 292 -->

![Extracted image from PDF page 292](../images/topology_selection/p292_img008_3229df10bc12.png)

Examples
