---
title: "BuildLine"
source_html: "https://build123d.readthedocs.io/en/latest/build_line.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "317-321"
generated_on: "2026-07-01"
---

# BuildLine

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 317 -->

1.13.1 BuildLine

BuildLine is a python context manager that is used to create one dimensional objects - objects with the property of
length but not area - that are typically used as part of a BuildSketch sketch or a BuildPart path.

The complete API for BuildLine is located at the end of this section.

Basic Functionality

The following is a simple BuildLine example:

```python
with BuildLine() as example_1:
```

```python
    Line((0, 0), (2, 0))
    ThreePointArc((0, 0), (1, 1), (2, 0))
```

<!-- PDF page 318 -->

The with statement creates the BuildLine context manager with the identifier example_1. The objects and operations
that are within the scope (i.e. indented) of this context will contribute towards the object being created by the context
manager. For BuildLine, this object is line and it’s referenced as example_1.line.

The first object in this example is a Line object which is used to create a straight line from coordinates (0,0) to (2,0)
on the default XY plane. The second object is a ThreePointArc that starts and ends at the two ends of the line.

Constraints

Building with constraints enables the designer to capture design intent and add a high degree of robustness to their
designs. The following sections describe creating positional and tangential constraints as well as using object attributes
to enable this type of design.

@ position_at Operator

In the previous example, the ThreePointArc started and ended at the two ends of the Line but this was done by
referring to the same point (0,0) and (2,0). This can be improved upon by specifying constraints that lock the arc
to those two end points, as follows:

```python
with BuildLine() as example_2:
    l1 = Line((0, 0), (2, 0))
    l2 = ThreePointArc(l1 @ 0, (1, 1), l1 @ 1)
```

Here instance variables l1 and l2 are assigned to the two BuildLine objects and the ThreePointArc references the
beginning of the straight line with l1 @ 0 and the end with l1 @ 1. The @ operator takes a float (or integer) parameter
between 0 and 1 and determines a position at this fractional position along the line’s length.

This example can be improved on further by calculating the mid-point of the arc as follows:

```python
with BuildLine() as example_3:
    l1 = Line((0, 0), (2, 0))
    l2 = ThreePointArc(l1 @ 0, l1 @ 0.5 + (0, 1), l1 @ 1)
```

Here l1 @ 0.5 finds the center of l1 while l1 @ 0.5 + (0, 1) does a vector addition to generate the point (1,1).

To make the design even more parametric, the height of the arc can be calculated from l1 as follows:

```python
with BuildLine() as example_4:
    l1 = Line((0, 0), (2, 0))
    l2 = ThreePointArc(l1 @ 0, l1 @ 0.5 + (0, l1.length / 2), l1 @ 1)
```

The arc height is now calculated as (0, l1.length / 2) by using the length property of Edge and Wire shapes.
At this point the ThreePointArc is fully parametric and able to generate the same shape for any horizontal line.

% tangent_at Operator

The other operator that is commonly used within BuildLine is % the tangent at operator. Here is another example:

```python
with BuildLine() as example_5:
    l1 = Line((0, 0), (5, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, l1.length - 1))
    l3 = JernArc(start=l2 @ 1, tangent=l2 % 1, radius=0.5, arc_size=90)
    l4 = Line(l3 @ 1, (0, l2.length + l3.radius))
```

<!-- PDF page 319 -->

which generates (note that the circles show line junctions):

The JernArc has the following parameters:

• start=l2 @ 1 - start the arc at the end of line l2,

• tangent=l2 % 1 - the tangent of the arc at the start point is equal to the l2's, tangent at its end (shown as a
dashed line)

• radius=0.5 - the radius of the arc, and

• arc_size=90 the angular size of the arc.

The final line starts at the end of l3 and ends at a point calculated from the length of l2 and the radius of arc l3.

Building with constraints as shown here will ensure that your designs both fully represent design intent and are robust
to design changes.

BuildLine to BuildSketch

As mentioned previously, one of the two primary reasons to create BuildLine objects is to use them in BuildSketch.
When a BuildLine context manager exits and is within the scope of a BuildSketch context manager it will transfer the
generated line to BuildSketch. The BuildSketch make_face() or make_hull() operations are then used to transform
the line (specifically a list of Edges) into a Face - the native BuildSketch objects.

Here is an example of using BuildLine to create an object that otherwise might be difficult to create:

```python
with BuildSketch() as example_6:
```

```python
    with BuildLine() as club_outline:
        l0 = Line((0, -188), (76, -188))
        b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
        b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
        b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
        b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
        mirror(about=Plane.YZ)
    make_face()
```

which generates:

Note

SVG import to BuildLine

The BuildLine code used in this example was generated by translating a SVG file into BuildLine source code with
the import_svg_as_buildline_code() function. For example:

```python
 svg_code, builder_name = import_svg_as_buildline_code("club.svg")
```

would translate the “club.svg” image file’s paths into BuildLine code much like that shown above. From there it’s
easy for a user to add constraints or otherwise enhance the original image and use it in their design.

<!-- PDF page 320 -->

BuildLine to BuildPart

The other primary reasons to use BuildLine is to create paths for BuildPart sweep() operations. Here some curved
and straight segments define a path:

```python
with BuildPart() as example_7:
```

```python
    with BuildLine() as example_7_path:
        l1 = RadiusArc((0, 0), (1, 1), 2)
        l2 = Spline(l1 @ 1, (2, 3), (3, 3), tangents=(l1 % 1, (0, -1)))
        l3 = Line(l2 @ 1, (3, 0))
    with BuildSketch(Plane(origin=l1 @ 0, z_dir=l1 % 0)) as example_7_section:
```

```python
        Circle(0.1)
    sweep()
```

which generates:

There are few things to note from this example:

• The @ and % operators are used to create a plane normal to the beginning of the path with which to create the
circular section used by the sweep operation (this plane is not one of the ordinal planes).

• Both the path generated by BuildLine and the section generated by BuildSketch have been transferred to BuildPart
when each of them exit.

• The BuildPart Sweep operation is using the path and section previously transferred to it (as “pending” objects)
as parameters of the sweep. The Sweep operation “consumes” these pending objects as to not interfere with
subsequence operations.

Working on other Planes

So far all of the examples were created on Plane.XY - the default plane - which is equivalent to global coordinates.
Sometimes it’s convenient to work on another plane, especially when creating paths for BuildPart Sweep operations.

```python
with BuildLine(Plane.YZ) as example_8:
    l1 = Line((0, 0), (5, 0))
    l2 = Line(l1 @ 1, l1 @ 1 + (0, l1.length - 1))
    l3 = JernArc(start=l2 @ 1, tangent=l2 % 1, radius=0.5, arc_size=90)
    l4 = Line(l3 @ 1, (0, l2.length + l3.radius))
```

which generates:

Here the BuildLine object is created on Plane.YZ just by specifying the working plane during BuildLine initialization.

There are three rules to keep in mind when working with alternate planes in BuildLine:

1. BuildLine accepts a single Plane to work with as opposed to other Builders that accept more than one work-
plane.

2. Values entered as tuples such as (1, 2) or (1, 2, 3) will be localized to the current workplane. This rule
applies to points and to the use of tuples to modify locations calculated with the @ and % operators such as l1 @
1 + (1, 1). For example, if the workplane is Plane.YZ the local value of (1, 2) would be converted to (0,
1, 2) in global coordinates. Three tuples are converted as well - (1, 2, 3) on Plane.YZ would be (3, 1,
2) in global coordinates. Providing values in local coordinates allows the designer to automate such conversions.

3. Values entered using the Vector class or those generated by the @ operator are considered global values and
are not localized. For example: Line(Vector(1, 2, 3), Vector(4, 5, 6)) will generate the same line

<!-- PDF page 321 -->

independent of the current workplane. It’s unlikely that users will need to use Vector values but the option is
there.

Finally, BuildLine’s workplane need not be one of the predefined ordinal planes, it could be one created from a surface
of a BuildPart part that is currently under construction.

Reference

class BuildLine(workplane: ~build123d.topology.two_d.Face | ~build123d.geometry.Plane |
~build123d.geometry.Location = Plane((0, 0, 0), (1, 0, 0), (0, 0, 1)), mode:
~build123d.build_enums.Mode = <Mode.ADD>)

The BuildLine class is a subclass of Builder for building lines (objects with length but not area or volume). It
has an _obj property that returns the current line being built. The class overrides the faces and solids methods
of Builder since they don’t apply to lines.

BuildLine only works with a single workplane which is used to convert tuples as inputs to global coordinates.
For example:

```python
     with BuildLine(Plane.YZ) as radius_arc:
         RadiusArc((1, 2), (2, 1), 1)
```

creates an arc from global points (0, 1, 2) to (0, 2, 1). Note that points entered as Vector(x, y, z) are considered
global and are not localized.

The workplane is also used to define planes parallel to the workplane that arcs are created on.

Parameters

```python
              • workplane (Union[Face, Plane, Location], optional) – plane used when local
                coordinates are used and when creating arcs. Defaults to Plane.XY.
```

• mode (Mode, optional) – combination mode. Defaults to Mode.ADD.

```python
     face(*args)
```

face() not implemented

```python
     faces(*args)
```

faces() not implemented

```python
     property line:  Curve | None
```

Get the current line

```python
     solid(*args)
```

solid() not implemented

```python
     solids(*args)
```

solids() not implemented
