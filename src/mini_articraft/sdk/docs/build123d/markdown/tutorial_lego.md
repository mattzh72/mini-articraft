---
title: "Lego Tutorial"
source_html: "https://build123d.readthedocs.io/en/latest/tutorial_lego.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "83-90"
generated_on: "2026-07-01"
---

# Lego Tutorial

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 83 -->

1.9.4 Lego Tutorial

This tutorial provides a step by step guide to creating a script to build a parametric Lego block as shown here:

Step 1: Setup

Before getting to the CAD operations, this Lego script needs to import the build123d environment. There are over
100 python classes in build123d so we’ll just import them all with a from build123d import * but there are other
options that we won’t explore here.

The dimensions of the Lego block follow. A key parameter is pip_count, the length of the Lego blocks in pips. This
parameter must be at least 2.

```python
from build123d import *
from ocp_vscode import show_object
pip_count = 6
```

```python
lego_unit_size = 8
pip_height = 1.8
pip_diameter = 4.8
block_length = lego_unit_size * pip_count
block_width = 16
base_height = 9.6
block_height = base_height + pip_height
support_outer_diameter = 6.5
support_inner_diameter = 4.8
ridge_width = 0.6
ridge_depth = 0.3
wall_thickness = 1.2
```

Step 2: Part Builder

The Lego block will be created by the BuildPart builder as it’s a discrete three dimensional part; therefore, we’ll
instantiate a BuildPart with the name lego.

```python
with BuildPart() as lego:
```

Step 3: Sketch Builder

Lego blocks have quite a bit of internal structure. To create this structure we’ll draw a two dimensional sketch that
will later be extruded into a three dimensional object. As this sketch will be part of the lego part, we’ll create a sketch
builder in the context of the part builder as follows:

<!-- PDF page 84 -->

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

Note that builder instance names are optional - we’ll use plan to reference the sketch. Also note that all sketch objects
are filled or 2D faces not just perimeter lines.

Step 4: Perimeter Rectangle

The first object in the sketch is going to be a rectangle with the dimensions of the outside of the Lego block. The
following step is going to refer to this rectangle, so it will be assigned the identifier perimeter.

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

```python
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
```

Once the Rectangle object is created the sketch appears as follows:

Step 5: Offset to Create Walls

To create the walls of the block the rectangle that we’ve created needs to be hollowed out. This will be done with the
Offset operation which is going to create a new object from perimeter.

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

```python
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
        # Subtract an offset to create the block walls
        offset(
```

```python
            perimeter,
            -wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
```

The first parameter to Offset is the reference object. The amount is a negative value to indicate that the offset should
be internal. The kind parameter controls the shape of the corners - Kind.INTERSECTION will create square corners.
Finally, the mode parameter controls how this object will be placed in the sketch - in this case subtracted from the
existing sketch. The result is shown here:

Now the sketch consists of a hollow rectangle.

Step 6: Create Internal Grid

The interior of the Lego block has small ridges on all four internal walls. These ridges will be created as a grid of thin
rectangles so the positions of the centers of these rectangles need to be defined. A pair of GridLocations location
contexts will define these positions, one for the horizontal bars and one for the vertical bars. As the Rectangle objects
are in the scope of a location context (GridLocations in this case) that defined multiple points, multiple rectangles
are created.

<!-- PDF page 85 -->

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

```python
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
        # Subtract an offset to create the block walls
        offset(
            perimeter,
            -wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
        # Add a grid of lengthwise and widthwise bars
        with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
```

```python
            Rectangle(width=block_length, height=ridge_width)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
```

```python
            Rectangle(width=ridge_width, height=block_width)
```

Here we can see that the first GridLocations creates two positions which causes two horizontal rectangles to be cre-
ated. The second GridLocations works in the same way but creates pip_count positions and therefore pip_count
rectangles. Note that keyword parameter are optional in this case.

The result looks like this:

Step 7: Create Ridges

To convert the internal grid to ridges, the center needs to be removed. This will be done with another Rectangle.

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

```python
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
        # Subtract an offset to create the block walls
        offset(
            perimeter,
            -wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
        # Add a grid of lengthwise and widthwise bars
        with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
```

```python
            Rectangle(width=block_length, height=ridge_width)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
```

```python
            Rectangle(width=ridge_width, height=block_width)
        # Subtract a rectangle leaving ribs on the block walls
        Rectangle(
```

```python
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
```

The Rectangle is subtracted from the sketch to leave the ridges as follows:

<!-- PDF page 86 -->

Step 8: Hollow Circles

Lego blocks use a set of internal hollow cylinders that the pips push against to hold two blocks together. These will be
created with Circle.

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

```python
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
        # Subtract an offset to create the block walls
        offset(
            perimeter,
            -wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
        # Add a grid of lengthwise and widthwise bars
        with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
```

```python
            Rectangle(width=block_length, height=ridge_width)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
```

```python
            Rectangle(width=ridge_width, height=block_width)
        # Subtract a rectangle leaving ribs on the block walls
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        # Add a row of hollow circles to the center
        with GridLocations(
```

```python
            x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
        ):
```

```python
            Circle(radius=support_outer_diameter / 2)
            Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)
```

Here another GridLocations is used to position the centers of the circles. Note that since both Circle objects are in
the scope of the location context, both Circles will be positioned at these locations.

Once the Circles are added, the sketch is complete and looks as follows:

Step 9: Extruding Sketch into Walls

Now that the sketch is complete it needs to be extruded into the three dimensional wall object.

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

```python
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
        # Subtract an offset to create the block walls
        offset(
```

<!-- PDF page 87 -->

```python
                                                                      (continued from previous page)
            perimeter,
            -wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
        # Add a grid of lengthwise and widthwise bars
        with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
```

```python
            Rectangle(width=block_length, height=ridge_width)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
```

```python
            Rectangle(width=ridge_width, height=block_width)
        # Subtract a rectangle leaving ribs on the block walls
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        # Add a row of hollow circles to the center
        with GridLocations(
            x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
        ):
```

```python
            Circle(radius=support_outer_diameter / 2)
            Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)
    # Extrude this base sketch to the height of the walls
    extrude(amount=base_height - wall_thickness)
```

Note how the Extrude operation is no longer in the BuildSketch scope and has returned back into the BuildPart
scope. This causes BuildSketch to exit and transfer the sketch that we’ve created to BuildPart for further processing
by Extrude.

The result is:

Step 10: Adding a Top

Now that the walls are complete, the top of the block needs to be added. Although this could be done with another
sketch, we’ll add a box to the top of the walls.

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

```python
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
        # Subtract an offset to create the block walls
        offset(
            perimeter,
            -wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
        # Add a grid of lengthwise and widthwise bars
        with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
```

```python
            Rectangle(width=block_length, height=ridge_width)
```

<!-- PDF page 88 -->

```python
                                                                      (continued from previous page)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
```

```python
            Rectangle(width=ridge_width, height=block_width)
        # Subtract a rectangle leaving ribs on the block walls
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        # Add a row of hollow circles to the center
        with GridLocations(
            x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
        ):
```

```python
            Circle(radius=support_outer_diameter / 2)
            Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)
    # Extrude this base sketch to the height of the walls
    extrude(amount=base_height - wall_thickness)
    # Create a box on the top of the walls
    with Locations((0, 0, lego.vertices().sort_by(Axis.Z)[-1].Z)):
```

```python
        # Create the top of the block
        Box(
```

```python
            length=block_length,
            width=block_width,
            height=wall_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
```

To position the top, we’ll describe the top center of the lego walls with a Locations context. To determine the height
we’ll extract that from the lego.part by using the vertices() method which returns a list of the positions of all of
the vertices of the Lego block so far. Since we’re interested in the top, we’ll sort by the vertical (Z) axis and take the
top of the list sort_by(Axis.Z)[-1]. Finally, the Z property of this vertex will return just the height of the top. Note
that the X and Y values are not used from the selected vertex as there are no vertices in the center of the block.

Within the scope of this Locations context, a Box is created, centered at the intersection of the x and y axis but not
in the z thus aligning with the top of the walls.

The base is closed now as shown here:

Step 11: Adding Pips

The final step is to add the pips to the top of the Lego block. To do this we’ll create a new workplane on top of the
block where we can position the pips.

```python
with BuildPart() as lego:
```

```python
    # Draw the bottom of the block
    with BuildSketch() as plan:
```

```python
        # Start with a Rectangle the size of the block
        perimeter = Rectangle(width=block_length, height=block_width)
        # Subtract an offset to create the block walls
        offset(
            perimeter,
            -wall_thickness,
            kind=Kind.INTERSECTION,
```

<!-- PDF page 89 -->

```python
                                                                      (continued from previous page)
            mode=Mode.SUBTRACT,
        )
        # Add a grid of lengthwise and widthwise bars
        with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
```

```python
            Rectangle(width=block_length, height=ridge_width)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
```

```python
            Rectangle(width=ridge_width, height=block_width)
        # Subtract a rectangle leaving ribs on the block walls
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        # Add a row of hollow circles to the center
        with GridLocations(
            x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
        ):
```

```python
            Circle(radius=support_outer_diameter / 2)
            Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)
    # Extrude this base sketch to the height of the walls
    extrude(amount=base_height - wall_thickness)
    # Create a box on the top of the walls
    with Locations((0, 0, lego.vertices().sort_by(Axis.Z)[-1].Z)):
```

```python
        # Create the top of the block
        Box(
            length=block_length,
            width=block_width,
            height=wall_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    # Create a workplane on the top of the block
    with BuildPart(lego.faces().sort_by(Axis.Z)[-1]):
```

```python
        # Create a grid of pips
        with GridLocations(lego_unit_size, lego_unit_size, pip_count, 2):
```

```python
            Cylinder(
```

```python
                radius=pip_diameter / 2,
                height=pip_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
```

In this case, the workplane is created from the top Face of the Lego block by using the faces method and then sorted
vertically and taking the top one sort_by(Axis.Z)[-1].

On the new workplane, a grid of locations is created and a number of Cylinder’s are positioned at each location.

This completes the Lego block. To access the finished product, refer to the builder’s internal object as shown here:

Builder    Object

BuildLine  line
BuildSketch sketch
BuildPart  part

<!-- PDF page 90 -->

so in this case the Lego block is lego.part. To display the part use show_object(lego.part) or show(lego.
part) depending on the viewer. The part could also be exported to a STL or STEP file by referencing lego.part.

Note

Viewers that don’t directly support build123d my require a raw OpenCascade object. In this case, append .wrapped
to the object (e.g.) show_object(lego.part.wrapped).
