---
title: "Group Examples"
source_html: "https://build123d.readthedocs.io/en/latest/topology_selection/group_examples.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "300-307"
generated_on: "2026-07-01"
---

# Group Examples

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 300 -->

Group Examples

Axis and Length

This heatsink component could use fillets on the ends of the fins on the long ends. One way to accomplish this is to
filter by length, sort by axis, and slice the result knowing how many edges to expect.

<!-- PDF page 301 -->

![Extracted image from PDF page 301](../images/topology_group_examples/p301_img001_81b8741b5339.png)

<!-- PDF page 302 -->

Setup

```python
from build123d import *
```

```python
with BuildPart() as fins:
```

```python
    with GridLocations(4, 6, 4, 4):
```

```python
        Box(2, 3, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
```

```python
with BuildPart() as part:
```

```python
    Box(34, 48, 5, align=(Align.CENTER, Align.CENTER, Align.MAX))
    with GridLocations(20, 27, 2, 2):
```

```python
        add(fins)
```

![Extracted image from PDF page 302](../images/topology_group_examples/p302_img002_2dca9e0cd8b0.png)

However, group_by can be used to first group all the edges by z-axis position and then group again by length. In both
cases, you can select the desired edges from the last group.

```python
    target = part.edges().group_by(Axis.Z)[-1].group_by(Edge.length)[-1]
    fillet(target, .75)
```

Hole Area

Callables are available to group_by, like sort_by. Here, the first inner wire is converted to a face and then that area
is the grouping criteria to find the faces with the largest hole.

<!-- PDF page 303 -->

![Extracted image from PDF page 303](../images/topology_group_examples/p303_img003_75bfbc455930.png)

Setup

```python
from build123d import *
```

```python
with BuildPart() as part:
```

```python
    Cylinder(10, 30, rotation=(90, 0, 0))
    Cylinder(8, 40, rotation=(90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MAX))
    Cylinder(8, 23, rotation=(90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    Cylinder(5, 40, rotation=(90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildSketch(Plane.XY.offset(8)) as s:
```

```python
        SlotCenterPoint((0, 38), (0, 48), 5)
    extrude(amount=2.5, both=True, mode=Mode.SUBTRACT)
```

```python
    faces = part.faces().group_by(
```

```python
        lambda f: Face(f.inner_wires()[0]).area if f.inner_wires() else 0
    )
    chamfer([f.outer_wire().edges() for f in faces[-1]], 0.5)
```

![Extracted image from PDF page 303](../images/topology_group_examples/p303_img004_e2ddad1dfb1f.png)

<!-- PDF page 304 -->

Properties with Keys

Groups are usually selected by list slice, often smallest [0] or largest [-1], but they can also be selected by key with
the group method if the keys are known. Starting with an incomplete bearing block we are looking to add fillets to the
ribs and corners. We know the edge lengths so the edges can be grouped by Edge.Length and then the desired groups
are selected with the group method using the lengths as keys.

Setup

```python
from build123d import *
```

```python
with BuildPart() as part:
```

```python
    with BuildSketch(Plane.XZ) as sketch:
```

```python
        with BuildLine():
```

```python
            CenterArc((-6, 12), 10, 0, 360)
            Line((-16, 0), (16, 0))
        make_hull()
        Rectangle(50, 5, align=(Align.CENTER, Align.MAX))
```

```python
    extrude(amount=12)
```

```python
    Box(38, 6, 22, align=(Align.CENTER, Align.MAX, Align.MIN), mode=Mode.SUBTRACT)
```

```python
    circle = part.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Y)[0]
    with Locations(Plane(circle.arc_center, z_dir=circle.normal())):
```

```python
        CounterBoreHole(13 / 2, 16 / 2, 4)
```

```python
    mirror(about=Plane.XZ)
```

```python
    length_groups = part.edges().group_by(Edge.length)
    fillet(length_groups.group(6) + length_groups.group(5), 4)
```

![Extracted image from PDF page 304](../images/topology_group_examples/p304_img005_070930112064.png)

<!-- PDF page 305 -->

Next, we add alignment pin and counterbore holes after the fillets to make sure screw heads sit flush where they overlap
the fillet. Once that is done, it’s time to finalize the tight-tolerance bearing and pin holes with chamfers to make
installation easier. We can filter by GeomType.CIRCLE and group by Edge.radius to group the circular edges. Again,
the radii are known, so we can retrieve those groups directly and then further specify only the edges the bearings and
pins are installed from.

Adding holes

```python
    with BuildSketch() as pins:
```

```python
        with Locations((-21, 0)):
```

```python
            Circle(3 / 2)
        with Locations((21, 0)):
```

```python
            SlotCenterToCenter(1, 3)
    extrude(amount=-12, mode=Mode.SUBTRACT)
```

```python
    with GridLocations(42, 16, 2, 2):
```

```python
        CounterBoreHole(3.5 / 2, 3.5, 0)
```

```python
    radius_groups = part.edges().filter_by(GeomType.CIRCLE).group_by(Edge.radius)
    bearing_edges = radius_groups.group(8).group_by(SortBy.DISTANCE)[-1]
    pin_edges = radius_groups.group(1.5).filter_by_position(Axis.Z, -5, -5)
    chamfer([pin_edges, bearing_edges], .5)
```

![Extracted image from PDF page 305](../images/topology_group_examples/p305_img006_ebb74859b9a9.png)

Note that group_by is not the only way to capture edges with a known property value! filter_by with a lambda
expression can be used as well:

```python
radius_groups = part.edges().filter_by(GeomType.CIRCLE)
bearing_edges = radius_groups.filter_by(lambda e: e.radius == 8)
pin_edges = radius_groups.filter_by(lambda e: e.radius == 1.5)
```

<!-- PDF page 306 -->

![Extracted image from PDF page 306](../images/topology_group_examples/p306_img007_825a2dc5b0d9.png)

![Extracted image from PDF page 306](../images/topology_group_examples/p306_img008_adc4221c7ba0.png)

Axis and Length Axis and Length

![Extracted image from PDF page 306](../images/topology_group_examples/p306_img009_f52dddd66122.png)

Hole Area Hole Area

Properties with Keys Properties with Keys

<!-- PDF page 307 -->

Filter

A ShapeList can be filtered with the filter_by() and filter_by_position() methods based on a filtering cri-
teria. Filters are flexible way to isolate (or exclude) features based on known criteria.

Lets say we need all the faces with a normal in the +Z direction. One way to do this might be with a list comprehension,
however filter_by() has the capability to take a lambda function as a filter condition on the entire list. In this case,
the normal of each face can be checked against a vector direction and filtered accordingly.

```python
part.faces().filter_by(lambda f: f.normal_at() == Vector(0, 0, 1))
```

![Extracted image from PDF page 307](../images/topology_group_examples/p307_img010_a4db1e7b3e9c.png)

Examples
