---
title: "The build123d Examples"
source_html: "https://build123d.readthedocs.io/en/latest/examples_1.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "97-181"
generated_on: "2026-07-01"
---

# The build123d Examples

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 97 -->

1.9.6 The build123d Examples

Overview

In the GitHub repository you will find an examples folder.

Most of the examples show the builder and algebra modes.

![Extracted image from PDF page 97](../images/examples_1/p097_img001_0dea09178b01.png)

<!-- PDF page 98 -->

![Extracted image from PDF page 98](../images/examples_1/p098_img002_98668e7c3210.png)

Benchy  Benchy

Bicycle Tire Bicycle Tire

<!-- PDF page 99 -->

Bracelet Bracelet

Canadian  Flag Blowing  in  The   Wind            Canadian  Flag  Blowing  in  The  Wind

<!-- PDF page 100 -->

![Extracted image from PDF page 100](../images/examples_1/p100_img003_347516cd0544.png)

<!-- PDF page 101 -->

![Extracted image from PDF page 101](../images/examples_1/p101_img004_9d5bd4c35d64.png)

Cast Bearing Unit Cast Bearing Unit

<!-- PDF page 102 -->

Circuit Board With Holes Circuit Board With Holes

<!-- PDF page 103 -->

Clock Face Clock Face

<!-- PDF page 104 -->

Fast Grid Holes Fast Grid Holes

<!-- PDF page 105 -->

![Extracted image from PDF page 105](../images/examples_1/p105_img005_5d4c0ce57b84.png)

Handle  Handle

<!-- PDF page 106 -->

Heat Exchanger Heat Exchanger

<!-- PDF page 107 -->

![Extracted image from PDF page 107](../images/examples_1/p107_img006_5fe1d74182f5.png)

Key Cap  Key Cap

<!-- PDF page 108 -->

(former) build123d Logo Former build123d Logo

<!-- PDF page 109 -->

Maker Coin Maker Coin

<!-- PDF page 110 -->

Multi-Sketch Loft Multi-Sketch Loft

<!-- PDF page 111 -->

Peg Board J Hook Peg Board Hook

<!-- PDF page 112 -->

Platonic Solids Platonic Solids

<!-- PDF page 113 -->

Playing Cards Playing Cards

<!-- PDF page 114 -->

Stud Wall Stud Wall

<!-- PDF page 115 -->

Tea Cup Tea Cup

<!-- PDF page 116 -->

Toy Truck Toy Truck

Vase  Vase

<!-- PDF page 117 -->

Benchy

![Extracted image from PDF page 117](../images/examples_1/p117_img007_a49b55762054.png)

The Benchy examples shows how to import a STL model as a Solid object with the class Mesher and modify it by
replacing chimney with a BREP version.

• Benchy STL model: low_poly_benchy.stl

<!-- PDF page 118 -->

Gallery

![Extracted image from PDF page 118](../images/examples_1/p118_img008_eaba09efbf1b.png)

<!-- PDF page 119 -->

![Extracted image from PDF page 119](../images/examples_1/p119_img009_c0637291930a.png)

Reference Implementation (Builder Mode)

```python
# Import the benchy as a Solid model
importer = Mesher()
benchy_stl = importer.read("low_poly_benchy.stl")[0]
```

```python
with BuildPart() as benchy:
```

```python
    add(benchy_stl)
```

```python
    # Determine the plane that defines the top of the roof
    vertices = benchy.vertices()
    roof_vertices = vertices.filter_by_position(Axis.Z, 38, 42)
    roof_plane_vertices = [
        roof_vertices.group_by(Axis.Y, tol_digits=2)[-1].sort_by(Axis.X)[0],
        roof_vertices.sort_by(Axis.Z)[0],
        roof_vertices.group_by(Axis.Y, tol_digits=2)[0].sort_by(Axis.X)[0],
    ]
    roof_plane = Plane(
```

```python
        Face(Wire.make_polygon([v.to_tuple() for v in roof_plane_vertices]))
    )
    # Remove the faceted smoke stack
    split(bisect_by=roof_plane, keep=Keep.BOTTOM)
```

```python
    # Determine the position and size of the smoke stack
    smoke_stack_vertices = vertices.group_by(Axis.Z, tol_digits=0)[-1]
```

<!-- PDF page 120 -->

```python
                                                                      (continued from previous page)
    smoke_stack_center = sum(
        [Vector(v.X, v.Y, v.Z) for v in smoke_stack_vertices], Vector()
    ) * (1 / len(smoke_stack_vertices))
    smoke_stack_radius = max(
        [
            (Vector(*v.to_tuple()) - smoke_stack_center).length
            for v in smoke_stack_vertices
        ]
    )
```

```python
    # Create the new smoke stack
    with BuildSketch(Plane(smoke_stack_center)):
```

```python
        Circle(smoke_stack_radius)
        Circle(smoke_stack_radius - 2 * MM, mode=Mode.SUBTRACT)
    extrude(amount=-3 * MM)
    with BuildSketch(Plane(smoke_stack_center)):
```

```python
        Circle(smoke_stack_radius - 0.5 * MM)
        Circle(smoke_stack_radius - 2 * MM, mode=Mode.SUBTRACT)
    extrude(amount=roof_plane_vertices[1].Z - smoke_stack_center.Z)
```

```python
show(benchy)
```

Bicycle Tire

![Extracted image from PDF page 120](../images/examples_1/p120_img010_98668e7c3210.png)

This example demonstrates how to model a realistic bicycle tire with a patterned tread using build123d. The key concept
showcased here is the use of wrap_faces to project 2D planar geometry onto a curved 3D surface.

<!-- PDF page 121 -->

Reference Implementation (Builder Mode)

```python
import copy
from build123d import *
from ocp_vscode import show
```

```python
wheel_diameter = 740 * MM
```

```python
with BuildSketch() as tire_profile:
```

```python
    with BuildLine() as build_profile:
        l00 = Bezier((0.0, 0.0), (7.05, 0.0), (12.18, 1.54), (15.13, 4.54))
        l01 = Bezier(l00 @ 1, (15.81, 5.22), (15.98, 5.44), (16.5, 6.23))
        l02 = Bezier(l01 @ 1, (18.45, 9.19), (19.61, 13.84), (19.94, 20.06))
        l03 = Bezier(l02 @ 1, (20.1, 23.24), (19.93, 27.48), (19.56, 29.45))
        l04 = Bezier(l03 @ 1, (19.13, 31.69), (18.23, 33.67), (16.91, 35.32))
        l05 = Bezier(l04 @ 1, (16.26, 36.12), (15.57, 36.77), (14.48, 37.58))
        l06 = Bezier(l05 @ 1, (12.77, 38.85), (11.51, 40.28), (10.76, 41.78))
        l07 = Bezier(l06 @ 1, (10.07, 43.16), (10.15, 43.81), (11.03, 43.98))
        l08 = Bezier(l07 @ 1, (11.82, 44.13), (12.15, 44.55), (12.08, 45.33))
        l09 = Bezier(l08 @ 1, (12.01, 46.07), (11.84, 46.43), (11.43, 46.69))
        l10 = Bezier(l09 @ 1, (10.98, 46.97), (10.07, 46.7), (9.47, 46.1))
        l11 = Bezier(l10 @ 1, (9.03, 45.65), (8.88, 45.31), (8.84, 44.65))
        l12 = Bezier(l11 @ 1, (8.78, 43.6), (9.11, 42.26), (9.72, 41.0))
        l13 = Bezier(l12 @ 1, (10.43, 39.54), (11.52, 38.2), (12.78, 37.22))
        l14 = Bezier(l13 @ 1, (15.36, 35.23), (16.58, 33.76), (17.45, 31.62))
        l15 = Bezier(l14 @ 1, (17.91, 30.49), (18.22, 29.27), (18.4, 27.8))
        l16 = Bezier(l15 @ 1, (18.53, 26.78), (18.52, 23.69), (18.37, 22.61))
        l17 = Bezier(l16 @ 1, (17.8, 18.23), (16.15, 14.7), (13.39, 11.94))
        l18 = Bezier(l17 @ 1, (11.89, 10.45), (10.19, 9.31), (8.09, 8.41))
        l19 = Bezier(l18 @ 1, (3.32, 6.35), (0.0, 6.64))
        mirror(about=Plane.YZ)
    make_face()
```

```python
tire = revolve(Pos(Y=-wheel_diameter / 2) * tire_profile.face(), Axis.X)
```

```python
with BuildSketch() as tread_pattern:
```

```python
    with Locations((1, 1)):
```

```python
        Trapezoid(15, 12, 60, 120, align=Align.MIN)
    with Locations((1, 8)):
```

```python
        with GridLocations(0, 5, 1, 2):
```

```python
            Rectangle(50, 2, mode=Mode.SUBTRACT)
```

```python
# Define the surface and path that the tread pattern will be wrapped onto
half_road_surface = Face.revolve(Pos(Y=-wheel_diameter / 2) * l00, 360, Axis.X)
tread_path = half_road_surface.edges().sort_by(Axis.X)[0]
```

```python
# Wrap the planar tread pattern onto the tire's outside surface
tread_faces = half_road_surface.wrap_faces(tread_pattern.faces(), tread_path)
```

```python
# Mirror the faces to the other half of the tire
tread_faces.extend([mirror(t, Plane.YZ) for t in tread_faces])
```

```python
# Thicken the tread to become solid nubs
```

<!-- PDF page 122 -->

```python
                                                                      (continued from previous page)
# tread_prime = [Solid.thicken(f, 3 * MM) for f in tread_faces]
tread_prime = [thicken(f, 3 * MM) for f in tread_faces]
```

```python
# Copy the nubs around the whole tire
tread = [Rot(X=r) * copy.copy(t) for t in tread_prime for r in range(0, 360, 2)]
```

```python
show(tire, tread)
```

Bracelet

![Extracted image from PDF page 122](../images/examples_1/p122_img011_9ac1b1be206d.png)

Doubly-curved bracelet with an embossed label

This model is a good “stress test” for OCCT because most of the final boundary surfaces are freeform (not analytic
planes/cylinders/spheres). The geometry is assembled from:

• a swept center section (using a curved solid end-face as the sweep profile)

• two freeform “tip caps” built as Gordon surfaces (network of curves)

• an optional embossed text label projected onto a curved solid

• alignment holes for splitting/printing/assembly

Key techniques demonstrated:

• using location_at/position_at/tangent (%) to extract local frames & tangents

• projecting curves onto a non-planar surface to create “true” 3D guide curves

• Gordon surfaces to build high-quality doubly-curved skins

• projecting faces (text) onto a complex solid and thickening them

<!-- PDF page 123 -->

Reference Implementation (Algebra Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
# Define input parameters
# - radii: ellipse radii (X, Y) controlling the bracelet centerline shape
# - width: bracelet width (along Z for the center sweep)
# - thickness: bracelet thickness (radial thickness of the cross section)
# - opening_angle: the missing angle that creates the wrist opening
# - label_str: optional text to emboss on the outside surface
# - Define input parameters
# radii, width, thickness, opening_angle, label_str = (45, 30), 25, 5, 80, "build123d"
radii, width, thickness, opening_angle, label_str = (45, 30), 25, 5, 80, ""
```

```python
# Step 1: Create an elliptical arc defining the *centerline* of the bracelet.
# The arc is truncated to leave an opening (the "gap" where the bracelet goes on).
# Angles are in degrees; 270° points downward, which keeps the opening centered at the␣
```

```python
˓→bottom.
center_arc = EllipticalCenterArc(
    (0, 0), *radii, 270 + opening_angle / 2, arc_size=360 - opening_angle
)
```

```python
# Step 2: Create HALF of the end cross-section, positioned at the end of the arc.
# We build only half so we can later mirror it to enforce symmetry and reduce
# curve-network complexity when building the freeform tip.
#
# location_at(1) returns a local coordinate frame at the arc end (tangent-aware).
# x_dir is chosen so the section’s local "X" is well-defined and stable.
end_center_arc = center_arc.location_at(1, x_dir=(0, 0, 1))
half_x_section = EllipticalCenterArc(
    (0, 0), width / 2, thickness / 2, 90, arc_size=180
).locate(end_center_arc)
```

```python
# Step 3: Create a doubly-curved "tip edge" curve.
# The tip edge must live in 3D and conform to the outside of the bracelet.
# To do that, we:
#   1) create a surface by extruding the center_arc into a sheet (a ribbon surface)
#   2) build a planar arc in a local frame at the end of that surface
#   3) project the planar arc onto the curved surface to get a true 3D curve
#
# The resulting tip_arc is a 3D edge that naturally matches the bracelet curvature.
center_surface = -Face.extrude(center_arc, (0, 0, 2 * width)).moved(
```

```python
    Location((0, 0, -width), (0, 0, 180))
)
tip_center_loc = -center_surface.location_at(center_arc @ 1, x_dir=(1, 0, 0))
normal_at_tip_center = tip_center_loc.z_axis.direction
```

```python
# A planar arc that would represent the outer boundary of the tip *if* the surface
# were flat. We immediately project it to make it truly conformal in 3D.
planar_tip_arc = CenterArc((0, 0), width / 2, 270, 180).locate(tip_center_loc).edge()
tip_arc = planar_tip_arc.project_to_shape(center_surface, -normal_at_tip_center)[0]
```

<!-- PDF page 124 -->

```python
                                                                      (continued from previous page)
# Step 4: Build the tip as a Gordon surface (a surface fit through a curve network).
# Gordon surfaces are ideal when:
#   - you don’t have an obvious analytic surface
#   - curvature changes in two directions (doubly-curved "cap")
#   - you can define a consistent set of profile curves + guide curves
#
# Here:
#   - profiles define "across the tip" shape (section -> bulged spline -> mirrored␣
```

```python
˓→section)
#   - guides define "along the tip" rails (start point -> projected 3D arc -> end point)
#
# Tangents are used to encourage smoothness where the tip joins the swept center section.
profile = Spline(
    half_x_section @ 0,
    tip_arc @ 0.5,
    half_x_section @ 1,
    tangents=(center_arc % 1, -(center_arc % 1)),
)
tip_surface = Face.make_gordon_surface(
    profiles=[half_x_section, profile, half_x_section.mirror(Plane.XY)],
    guides=[half_x_section @ 0, tip_arc, half_x_section @ 1],
)
```

```python
# Step 5: Close the tip surface into a watertight Solid.
# tip_surface is the outer "skin"; we create a side face from its boundary wire
# and make a shell, then a solid.
tip_side = Face(tip_surface.wire())
tip = Solid(Shell([tip_side, tip_surface]))
```

```python
# Step 6: Sweep the *flat end face* of the tip around the center arc.
# This is the trick that makes the center section compatible with the freeform tip:
# the sweep profile is the same face that bounds the tip, so the join is naturally␣
```

```python
˓→aligned.
center_section = sweep(tip_side, center_arc).solid()
```

```python
# Step 7: Assemble the bracelet from the center and two mirrored tips.
# Mirror across YZ to create the opposite end cap.
bracelet = Solid() + [tip, center_section, tip.mirror(Plane.YZ)]
```

```python
# Step 8: Add an embossed label.
# This is often the hardest operation for OCCT in this model:
# projecting text onto a doubly-curved surface can create many small faces/edges,
# and thickening them adds even more boolean complexity.
if label_str:
    label = Text(label_str, font_size=width * 0.8, align=Align.CENTER)
```

```python
    # Project the text onto the bracelet using a path-based placement along center_arc.
    # The parameter offsets the label so it sits centered along arc-length.
    p_labels = bracelet.project_faces(
        label, center_arc, 0.5 - 0.5 * (label.bounding_box().size.X) / center_arc.length
    )
    # Turn the projected faces into solids via thickening (embossing).
```

<!-- PDF page 125 -->

```python
                                                                      (continued from previous page)
    embossed_label = [Solid.thicken(f, 0.5) for f in p_labels.faces()]
    bracelet += embossed_label
```

```python
# Step 9: Add alignment holes to aid assembly after 3D printing in two halves.
# These are placed at evenly spaced locations along the arc (including both ends).
# A small clearance (+0.15) is included for typical FDM tolerances.
alignment_holes = [
```

```python
    Pos(p) * Cylinder(1.75 / 2 + 0.15, 8)
    for p in [center_arc.position_at(i / 4) for i in range(5)]
]
bracelet -= alignment_holes
```

```python
show(bracelet)
```

Former build123d Logo

![Extracted image from PDF page 125](../images/examples_1/p125_img012_95d3dc12e701.png)

This example creates the former build123d logo (new logo was created in the end of 2023).

Using text and lines to create the first build123d logo. The builder mode example also generates the SVG file logo.svg.

<!-- PDF page 126 -->

Reference Implementation (Builder Mode)

```python
with BuildSketch() as logo_text:
```

```python
    Text("123d", font_size=10, align=(Align.MIN, Align.MIN))
    font_height = logo_text.vertices().sort_by(Axis.Y)[-1].Y
```

```python
with BuildSketch() as build_text:
```

```python
    Text("build", font_size=5, align=(Align.CENTER, Align.CENTER))
    build_bb = bounding_box(build_text.sketch, mode=Mode.PRIVATE)
    build_vertices = build_bb.vertices().sort_by(Axis.X)
    build_width = build_vertices[-1].X - build_vertices[0].X
```

```python
with BuildLine() as one:
    l1 = Line((font_height * 0.3, 0), (font_height * 0.3, font_height))
    TangentArc(l1 @ 1, (0, font_height * 0.7), tangent=(l1 % 1) * -1)
```

```python
with BuildSketch() as two:
```

```python
    with Locations((font_height * 0.35, 0)):
```

```python
        Text("2", font_size=10, align=(Align.MIN, Align.MIN))
```

```python
with BuildPart() as three_d:
```

```python
    with BuildSketch(Plane((font_height * 1.1, 0))):
```

```python
        Text("3d", font_size=10, align=(Align.MIN, Align.MIN))
    extrude(amount=font_height * 0.3)
    logo_width = three_d.vertices().sort_by(Axis.X)[-1].X
```

```python
with BuildLine() as arrow_left:
    t1 = TangentArc((0, 0), (1, 0.75), tangent=(1, 0))
    mirror(t1, Plane.XZ)
```

```python
ext_line_length = font_height * 0.5
dim_line_length = (logo_width - build_width - 2 * font_height * 0.05) / 2
with BuildLine() as extension_lines:
    l1 = Line((0, -font_height * 0.1), (0, -ext_line_length - font_height * 0.1))
    l2 = Line(
        (logo_width, -font_height * 0.1),
        (logo_width, -ext_line_length - font_height * 0.1),
    )
    with Locations(l1 @ 0.5):
```

```python
        add(arrow_left.line)
    with Locations(l2 @ 0.5):
```

```python
        add(arrow_left.line, rotation=180.0)
    Line(l1 @ 0.5, l1 @ 0.5 + Vector(dim_line_length, 0))
    Line(l2 @ 0.5, l2 @ 0.5 - Vector(dim_line_length, 0))
```

```python
# Precisely center the build Faces
with BuildSketch() as build:
```

```python
    with Locations(
        (l1 @ 0.5 + l2 @ 0.5) / 2
        - Vector((build_vertices[-1].X + build_vertices[0].X) / 2, 0)
    ):
```

```python
        add(build_text.sketch)
```

<!-- PDF page 127 -->

```python
if True:
    logo = Compound(
        children=[
            one.line,
            two.sketch,
            three_d.part,
            extension_lines.line,
            build.sketch,
        ]
    )
```

```python
    # logo.export_step("logo.step")
    def add_svg_shape(svg: ExportSVG, shape: Shape, color: tuple[float, float, float]):
```

```python
        global counter
        try:
            counter += 1
        except:
            counter = 1
```

```python
        visible, _hidden = shape.project_to_viewport(
            (-5, 1, 10), viewport_up=(0, 1, 0), look_at=(0, 0, 0)
        )
        if color is not None:
            svg.add_layer(str(counter), fill_color=color, line_weight=1)
        else:
            svg.add_layer(str(counter), line_weight=1)
        svg.add_shape(visible, layer=str(counter))
```

```python
    svg = ExportSVG(scale=20)
    add_svg_shape(svg, logo, None)
    # add_svg_shape(svg, Compound(children=[one.line, extension_lines.line]), None)
    # add_svg_shape(svg, Compound(children=[two.sketch, build.sketch]), (170, 204, 255))
    # add_svg_shape(svg, three_d.part, (85, 153, 255))
    svg.write("logo.svg")
```

```python
show_object(one, name="one")
show_object(two, name="two")
show_object(three_d, name="three_d")
show_object(extension_lines, name="extension_lines")
show_object(build, name="build")
```

Reference Implementation (Algebra Mode)

```python
logo_text = Text("123d", font_size=10, align=Align.MIN)
font_height = logo_text.vertices().sort_by(Axis.Y).last.Y
```

```python
build_text = Text("build", font_size=5, align=Align.CENTER)
build_bb = build_text.bounding_box()
build_width = build_bb.max.X - build_bb.min.X
```

<!-- PDF page 128 -->

```python
                                                                      (continued from previous page)
l1 = Line((font_height * 0.3, 0), (font_height * 0.3, font_height))
one = l1 + TangentArc(l1 @ 1, (0, font_height * 0.7), tangent=(l1 % 1) * -1)
```

```python
two = Pos(font_height * 0.35, 0) * Text("2", font_size=10, align=Align.MIN)
```

```python
three_d = Text("3d", font_size=10, align=Align.MIN)
three_d = Pos(font_height * 1.1, 0) * extrude(three_d, amount=font_height * 0.3)
logo_width = three_d.vertices().sort_by(Axis.X).last.X
```

```python
t1 = TangentArc((0, 0), (1, 0.75), tangent=(1, 0))
arrow_left = t1 + mirror(t1, Plane.XZ)
```

```python
ext_line_length = font_height * 0.5
dim_line_length = (logo_width - build_width - 2 * font_height * 0.05) / 2
```

```python
l1 = Line((0, -font_height * 0.1), (0, -ext_line_length - font_height * 0.1))
l2 = Line(
    (logo_width, -font_height * 0.1),
    (logo_width, -ext_line_length - font_height * 0.1),
)
extension_lines = Curve() + (l1 + l2)
extension_lines += Pos(*(l1 @ 0.5)) * arrow_left
extension_lines += (Pos(*(l2 @ 0.5)) * Rot(Z=180)) * arrow_left
extension_lines += Line(l1 @ 0.5, l1 @ 0.5 + Vector(dim_line_length, 0))
extension_lines += Line(l2 @ 0.5, l2 @ 0.5 - Vector(dim_line_length, 0))
```

```python
# Precisely center the build Faces
p1 = Pos((l1 @ 0.5 + l2 @ 0.5) / 2 - Vector((build_bb.max.X + build_bb.min.X) / 2, 0))
build = p1 * build_text
```

```python
cmpd = Compound([three_d, two, one, build, extension_lines])
```

```python
show_object(cmpd, name="compound")
```

<!-- PDF page 129 -->

Cast Bearing Unit

![Extracted image from PDF page 129](../images/examples_1/p129_img013_347516cd0544.png)

This example demonstrates the creation of a castable flanged bearing housing using the draft operation to add appro-
priate draft angles for mold release.

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
A, A1, Db2, H, J = 26, 11, 57, 98.5, 76.5
with BuildPart() as oval_flanged_bearing_unit:
```

```python
    with BuildSketch() as plan:
        housing = Circle(Db2 / 2)
        with GridLocations(J, 0, 2, 1) as bolt_centers:
```

```python
            Circle((H - J) / 2)
        make_hull()
    extrude(amount=A1)
    extrude(housing, amount=A)
    drafted_faces = oval_flanged_bearing_unit.faces().filter_by(Axis.Z, reverse=True)
    draft(drafted_faces, Plane.XY, 4)
    fillet(oval_flanged_bearing_unit.edges(), 1)
    with Locations(oval_flanged_bearing_unit.faces().sort_by(Axis.Z)[-1]):
```

<!-- PDF page 130 -->

```python
                                                                      (continued from previous page)
        CounterBoreHole(14 / 2, 47 / 2, 14)
    with Locations(*bolt_centers):
```

```python
        Hole(5)
```

```python
oval_flanged_bearing_unit.part.color = Color(0x4C6377)
```

```python
show(oval_flanged_bearing_unit)
```

Canadian Flag Blowing in The Wind

![Extracted image from PDF page 130](../images/examples_1/p130_img014_3d8a248b8371.png)

A Canadian Flag blowing in the wind created by projecting planar faces onto a non-planar face (the_wind).

This example also demonstrates building complex lines that snap to existing features.

<!-- PDF page 131 -->

More Images

![Extracted image from PDF page 131](../images/examples_1/p131_img015_56709887ead7.png)

![Extracted image from PDF page 131](../images/examples_1/p131_img016_6dfd21d82cb9.png)

Reference Implementation (Builder Mode)

```python
def surface(amplitude, u, v):
```

```python
    """Calculate the surface displacement of the flag at a given position"""
    return v * amplitude / 20 * cos(3.5 * pi * u) + amplitude / 10 * v * sin(
```

```python
        1.1 * pi * v
    )
```

<!-- PDF page 132 -->

```python
# Note that the surface to project on must be a little larger than the faces
# being projected onto it to create valid projected faces
the_wind = Face.make_surface_from_array_of_points(
    [
        [
```

```python
            Vector(
                width * (v * 1.1 / 40 - 0.05),
                height * (u * 1.2 / 40 - 0.1),
                height * surface(wave_amplitude, u / 40, v / 40) / 2,
            )
            for u in range(41)
        ]
        for v in range(41)
    ]
)
with BuildSketch(Plane.XY.offset(10)) as west_field_builder:
```

```python
    Rectangle(width / 4, height, align=(Align.MIN, Align.MIN))
west_field_planar = west_field_builder.sketch.faces()[0]
east_field_planar = west_field_planar.mirror(Plane.YZ.offset(width / 2))
```

```python
with BuildSketch(Plane((width / 2, 0, 10))) as center_field_builder:
```

```python
    Rectangle(width / 2, height, align=(Align.CENTER, Align.MIN))
    with BuildSketch(
```

```python
        Plane((width / 2, 0, 10)), mode=Mode.SUBTRACT
    ) as maple_leaf_builder:
```

```python
        with BuildLine() as outline:
            l1 = Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
            l2 = Polyline((0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125))
            RadiusArc(l1 @ 1, l2 @ 0, 0.0271)
            l3 = Polyline((0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071))
            TangentArc(l2 @ 1, l3 @ 0, tangent=l2 % 1)
            l4 = Polyline((0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188))
            SagittaArc(l3 @ 1, l4 @ 0, 0.003)
            l5 = Polyline((0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835))
            ThreePointArc(
                l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0
            )
            l6 = Polyline((0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752))
            Spline(
                l5 @ 1,
                l6 @ 0,
                tangents=(l5 % 1, l6 % 0),
                tangent_scalars=(2, 2),
            )
            l7 = Line((0.0692, 0.7808), (0.0000, 0.9167))
            TangentArc(l6 @ 1, l7 @ 0, tangent=l6 % 1)
            mirror(outline.edges(), Plane.YZ)
        make_face()
        scale(by=height)
maple_leaf_planar = maple_leaf_builder.sketch.faces()[0]
```

<!-- PDF page 133 -->

```python
                                                                      (continued from previous page)
center_field_planar = center_field_builder.sketch.faces()[0]
```

```python
west_field = west_field_planar.project_to_shape(the_wind, (0, 0, -1))[0]
west_field.color = Color("red")
east_field = east_field_planar.project_to_shape(the_wind, (0, 0, -1))[0]
east_field.color = Color("red")
center_field = center_field_planar.project_to_shape(the_wind, (0, 0, -1))[0]
center_field.color = Color("white")
maple_leaf = maple_leaf_planar.project_to_shape(the_wind, (0, 0, -1))[0]
maple_leaf.color = Color("red")
```

```python
canadian_flag = Compound(children=[west_field, east_field, center_field, maple_leaf])
show(Rot(90, 0, 0) * canadian_flag)
```

Reference Implementation (Algebra Mode)

```python
def surface(amplitude, u, v):
```

```python
    """Calculate the surface displacement of the flag at a given position"""
    return v * amplitude / 20 * cos(3.5 * pi * u) + amplitude / 10 * v * sin(
```

```python
        1.1 * pi * v
    )
```

```python
# Note that the surface to project on must be a little larger than the faces
# being projected onto it to create valid projected faces
the_wind = Face.make_surface_from_array_of_points(
    [
        [
```

```python
            Vector(
                width * (v * 1.1 / 40 - 0.05),
                height * (u * 1.2 / 40 - 0.1),
                height * surface(wave_amplitude, u / 40, v / 40) / 2,
            )
            for u in range(41)
        ]
        for v in range(41)
    ]
)
```

```python
field_planar = Plane.XY.offset(10) * Rectangle(width / 4, height, align=Align.MIN)
west_field_planar = field_planar.faces()[0]
east_field_planar = mirror(west_field_planar, Plane.YZ.offset(width / 2))
```

```python
l1 = Polyline((0.0000, 0.0771), (0.0187, 0.0771), (0.0094, 0.2569))
l2 = Polyline((0.0325, 0.2773), (0.2115, 0.2458), (0.1873, 0.3125))
r1 = RadiusArc(l1 @ 1, l2 @ 0, 0.0271)
l3 = Polyline((0.1915, 0.3277), (0.3875, 0.4865), (0.3433, 0.5071))
r2 = TangentArc(l2 @ 1, l3 @ 0, tangent=l2 % 1)
l4 = Polyline((0.3362, 0.5235), (0.375, 0.6427), (0.2621, 0.6188))
r3 = SagittaArc(l3 @ 1, l4 @ 0, 0.003)
l5 = Polyline((0.2469, 0.6267), (0.225, 0.6781), (0.1369, 0.5835))
```

<!-- PDF page 134 -->

```python
                                                                      (continued from previous page)
r4 = ThreePointArc(l4 @ 1, (l4 @ 1 + l5 @ 0) * 0.5 + Vector(-0.002, -0.002), l5 @ 0)
l6 = Polyline((0.1138, 0.5954), (0.1562, 0.8146), (0.0881, 0.7752))
s = Spline(
    l5 @ 1,
    l6 @ 0,
    tangents=(l5 % 1, l6 % 0),
    tangent_scalars=(2, 2),
)
l7 = Line((0.0692, 0.7808), (0.0000, 0.9167))
r5 = TangentArc(l6 @ 1, l7 @ 0, tangent=l6 % 1)
```

```python
outline = l1 + [l2, r1, l3, r2, l4, r3, l5, r4, l6, s, l7, r5]
outline += mirror(outline, Plane.YZ)
```

```python
maple_leaf_planar = make_face(outline)
```

```python
center_field_planar = (
```

```python
    Rectangle(1, 1, align=(Align.CENTER, Align.MIN)) - maple_leaf_planar
)
```

```python
def scale_move(obj):
```

```python
    return Plane((width / 2, 0, 10)) * scale(obj, height)
```

```python
def project(obj):
```

```python
    return obj.faces()[0].project_to_shape(the_wind, (0, 0, -1))[0]
```

```python
maple_leaf_planar = scale_move(maple_leaf_planar)
center_field_planar = scale_move(center_field_planar)
```

```python
west_field = project(west_field_planar)
west_field.color = Color("red")
east_field = project(east_field_planar)
east_field.color = Color("red")
center_field = project(center_field_planar)
center_field.color = Color("white")
maple_leaf = project(maple_leaf_planar)
maple_leaf.color = Color("red")
```

```python
canadian_flag = Compound(children=[west_field, east_field, center_field, maple_leaf])
show(Rot(90, 0, 0) * canadian_flag)
```

<!-- PDF page 135 -->

Circuit Board With Holes

![Extracted image from PDF page 135](../images/examples_1/p135_img017_774458b4bfd7.png)

This example demonstrates placing holes around a part.

• Builder mode uses Locations context to place the positions.

• Algebra mode uses product and range to calculate the positions.

<!-- PDF page 136 -->

More Images

![Extracted image from PDF page 136](../images/examples_1/p136_img018_785e85eea7f2.png)

Reference Implementation (Builder Mode)

```python
with BuildPart() as pcb:
```

```python
    with BuildSketch():
```

```python
        Rectangle(pcb_length, pcb_width)
```

```python
        for i in range(65 // 5):
            x = i * 5 - 30
            with Locations((x, -15), (x, -10), (x, 10), (x, 15)):
```

```python
                Circle(1, mode=Mode.SUBTRACT)
        for i in range(30 // 5 - 1):
            y = i * 5 - 10
            with Locations((30, y), (35, y)):
```

```python
                Circle(1, mode=Mode.SUBTRACT)
        with GridLocations(60, 20, 2, 2):
```

```python
            Circle(2, mode=Mode.SUBTRACT)
    extrude(amount=pcb_height)
```

```python
show_object(pcb.part.wrapped)
```

Reference Implementation (Algebra Mode)

```python
x_coords = product(range(65 // 5), (-15, -10, 10, 15))
y_coords = product((30, 35), range(30 // 5 - 1))
```

```python
pcb = Rectangle(pcb_length, pcb_width)
pcb -= [Pos(i * 5 - 30, y) * Circle(1) for i, y in x_coords]
```

<!-- PDF page 137 -->

```python
                                                                      (continued from previous page)
pcb -= [Pos(x, i * 5 - 10) * Circle(1) for x, i in y_coords]
pcb -= [loc * Circle(2) for loc in GridLocations(60, 20, 2, 2)]
```

```python
pcb = extrude(pcb, pcb_height)
```

```python
show(pcb)
```

Clock Face

![Extracted image from PDF page 137](../images/examples_1/p137_img019_f936f2d8dae9.png)

<!-- PDF page 138 -->

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
clock_radius = 10
with BuildSketch() as minute_indicator:
```

```python
    with BuildLine() as outline:
        l1 = CenterArc((0, 0), clock_radius * 0.975, 0.75, 4.5)
        l2 = CenterArc((0, 0), clock_radius * 0.925, 0.75, 4.5)
        Line(l1 @ 0, l2 @ 0)
        Line(l1 @ 1, l2 @ 1)
    make_face()
    fillet(minute_indicator.vertices(), radius=clock_radius * 0.01)
```

```python
with BuildSketch() as clock_face:
```

```python
    Circle(clock_radius)
    with PolarLocations(0, 60):
```

```python
        add(minute_indicator.sketch, mode=Mode.SUBTRACT)
    with PolarLocations(clock_radius * 0.875, 12):
```

```python
        SlotOverall(clock_radius * 0.05, clock_radius * 0.025, mode=Mode.SUBTRACT)
    for hour in range(1, 13):
```

```python
        with PolarLocations(clock_radius * 0.75, 1, -hour * 30 + 90, 360, rotate=False):
```

```python
            Text(
```

```python
                str(hour),
                font_size=clock_radius * 0.175,
                font_style=FontStyle.BOLD,
                mode=Mode.SUBTRACT,
            )
```

```python
show(clock_face)
```

Reference Implementation (Algebra Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
clock_radius = 10
```

```python
l1 = CenterArc((0, 0), clock_radius * 0.975, 0.75, 4.5)
l2 = CenterArc((0, 0), clock_radius * 0.925, 0.75, 4.5)
l3 = Line(l1 @ 0, l2 @ 0)
l4 = Line(l1 @ 1, l2 @ 1)
minute_indicator = make_face([l1, l3, l2, l4])
minute_indicator = fillet(minute_indicator.vertices(), radius=clock_radius * 0.01)
```

```python
clock_face = Circle(clock_radius)
clock_face -= PolarLocations(0, 60) * minute_indicator
clock_face -= PolarLocations(clock_radius * 0.875, 12) * SlotOverall(
    clock_radius * 0.05, clock_radius * 0.025
)
```

```python
clock_face -= [
```

<!-- PDF page 139 -->

```python
                                                                      (continued from previous page)
    loc
    * Text(
```

```python
        str(hour + 1),
        font_size=clock_radius * 0.175,
        font_style=FontStyle.BOLD,
        align=Align.CENTER,
    )
    for hour, loc in enumerate(
```

```python
        PolarLocations(clock_radius * 0.75, 12, 60, -360, rotate=False)
    )
]
```

```python
show(clock_face)
```

The Python code utilizes the build123d library to create a 3D model of a clock face. It defines a minute indicator with
arcs and lines, applying fillets, and then integrates it into the clock face sketch. The clock face includes a circular outline,
hour labels, and slots at specified positions. The resulting 3D model represents a detailed and visually appealing clock
design.

PolarLocations are used to position features on the clock face.

Fast Grid Holes

![Extracted image from PDF page 139](../images/examples_1/p139_img020_b12712ba46db.png)

Reference Implementation (Algebra Mode)

```python
import timeit
from build123d import *
from ocp_vscode import show
```

<!-- PDF page 140 -->

```python
start_time = timeit.default_timer()
```

```python
# Calculate the locations of 625 holes
major_r = 10
hole_locs = HexLocations(major_r, 25, 25)
```

```python
# Create wires for both the perimeter and all the holes
face_perimeter = Rectangle(500, 600).wire()
hex_hole = RegularPolygon(major_r - 1, 6, major_radius=True).wire()
holes = hole_locs * hex_hole
```

```python
# Create a new Face from the perimeter and hole wires
grid_pattern = Face(face_perimeter, holes)
```

```python
# Extrude to a 3D part
grid = extrude(grid_pattern, 1)
```

```python
print(f"Time: {timeit.default_timer() - start_time:0.3f}s")
show(grid)
```

This example demonstrates an efficient approach to creating a large number of holes (625 in this case) in a planar part
using build123d.

Instead of modeling and subtracting 3D solids for each hole—which is computationally expensive—this method con-
structs a 2D Face from an outer perimeter wire and a list of hole wires. The entire face is then extruded in a single
operation to form the final 3D object. This approach significantly reduces modeling time and complexity.

The hexagonal hole pattern is generated using HexLocations, and each location is populated with a hexagonal wire.
These wires are passed directly to the Face constructor as holes. On a typical Linux laptop, this script completes in
approximately 1.02 seconds, compared to substantially longer runtimes for boolean subtraction of individual holes in
3D.

<!-- PDF page 141 -->

Handle

![Extracted image from PDF page 141](../images/examples_1/p141_img021_ad05750ec844.png)

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import show_object
```

```python
segment_count = 6
```

```python
with BuildPart() as handle:
```

```python
    # Create a path for the sweep along the handle - added to pending_edges
    with BuildLine() as handle_center_line:
```

```python
        Spline(
            (-10, 0, 0),
            (0, 0, 5),
            (10, 0, 0),
            tangents=((0, 0, 1), (0, 0, -1)),
            tangent_scalars=(1.5, 1.5),
        )
```

```python
    # Create the cross sections - added to pending_faces
```

<!-- PDF page 142 -->

```python
                                                                      (continued from previous page)
    for i in range(segment_count + 1):
```

```python
        with BuildSketch(handle_center_line.line ^ (i / segment_count)) as section:
```

```python
            if i % segment_count == 0:
```

```python
                Circle(1)
            else:
```

```python
                Rectangle(1.25, 3)
                fillet(section.vertices(), radius=0.2)
    # Record the sections for display
    sections = handle.pending_faces
```

```python
    # Create the handle by sweeping along the path
    sweep(multisection=True)
```

```python
assert abs(handle.part.volume - 94.77361455046953) < 1e-3
```

```python
show_object(handle_center_line.line, name="handle_center_line")
for i, section in enumerate(sections):
    show_object(section, name="section" + str(i))
show_object(handle.part, name="handle", options=dict(alpha=0.6))
```

Reference Implementation (Algebra Mode)

```python
from build123d import *
from ocp_vscode import show_object
```

```python
segment_count = 6
```

```python
# Create a path for the sweep along the handle - added to pending_edges
handle_center_line = Spline(
    (-10, 0, 0),
    (0, 0, 5),
    (10, 0, 0),
    tangents=((0, 0, 1), (0, 0, -1)),
    tangent_scalars=(1.5, 1.5),
)
```

```python
# Create the cross sections - added to pending_faces
sections = Sketch()
for i in range(segment_count + 1):
    location = handle_center_line ^ (i / segment_count)
    if i % segment_count == 0:
        circle = location * Circle(1)
    else:
        circle = location * Rectangle(1.25, 3)
        circle = fillet(circle.vertices(), radius=0.2)
    sections += circle
```

```python
# Create the handle by sweeping along the path
handle = sweep(sections, path=handle_center_line, multisection=True)
```

```python
show_object(handle_center_line, name="handle_path")
```

<!-- PDF page 143 -->

```python
                                                                      (continued from previous page)
for i, circle in enumerate(sections):
    show_object(circle, name="section" + str(i))
show_object(handle, name="handle", options=dict(alpha=0.6))
```

This example demonstrates multisection sweep creating a drawer handle.

<!-- PDF page 144 -->

Heat Exchanger

![Extracted image from PDF page 144](../images/examples_1/p144_img022_5d4c0ce57b84.png)

<!-- PDF page 145 -->

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
exchanger_diameter = 10 * CM
exchanger_length = 30 * CM
plate_thickness = 5 * MM
# 149 tubes
tube_diameter = 5 * MM
tube_spacing = 2 * MM
tube_wall_thickness = 0.5 * MM
tube_extension = 3 * MM
bundle_diameter = exchanger_diameter - 2 * tube_diameter
fillet_radius = tube_spacing / 3
assert tube_extension > fillet_radius
```

```python
# Build the heat exchanger
with BuildPart() as heat_exchanger:
```

```python
    # Generate list of tube locations
    tube_locations = [
        l
        for l in HexLocations(
            radius=(tube_diameter + tube_spacing) / 2,
            x_count=exchanger_diameter // tube_diameter,
            y_count=exchanger_diameter // tube_diameter,
        )
        if l.position.length < bundle_diameter / 2
    ]
    tube_count = len(tube_locations)
    with BuildSketch() as tube_plan:
```

```python
        with Locations(*tube_locations):
```

```python
            Circle(radius=tube_diameter / 2)
            Circle(radius=tube_diameter / 2 - tube_wall_thickness, mode=Mode.SUBTRACT)
    extrude(amount=exchanger_length / 2)
    with BuildSketch(
```

```python
        Plane(
            origin=(0, 0, exchanger_length / 2 - tube_extension - plate_thickness),
            z_dir=(0, 0, 1),
        )
    ) as plate_plan:
```

```python
        Circle(radius=exchanger_diameter / 2)
        with Locations(*tube_locations):
```

```python
            Circle(radius=tube_diameter / 2 - tube_wall_thickness, mode=Mode.SUBTRACT)
    extrude(amount=plate_thickness)
    half_volume_before_fillet = heat_exchanger.part.volume
    # Simulate welded tubes by adding a fillet to the outside radius of the tubes
    fillet(
        heat_exchanger.edges()
        .filter_by(GeomType.CIRCLE)
        .sort_by(SortBy.RADIUS)
        .sort_by(Axis.Z, reverse=True)[2 * tube_count : 3 * tube_count],
        radius=fillet_radius,
```

<!-- PDF page 146 -->

```python
                                                                      (continued from previous page)
    )
    half_volume_after_fillet = heat_exchanger.part.volume
    mirror(about=Plane.XY)
```

```python
fillet_volume = 2 * (half_volume_after_fillet - half_volume_before_fillet)
assert abs(fillet_volume - 469.88331045553787) < 1e-3
```

```python
show(heat_exchanger)
```

Reference Implementation (Algebra Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
exchanger_diameter = 10 * CM
exchanger_length = 30 * CM
plate_thickness = 5 * MM
# 149 tubes
tube_diameter = 5 * MM
tube_spacing = 2 * MM
tube_wall_thickness = 0.5 * MM
tube_extension = 3 * MM
bundle_diameter = exchanger_diameter - 2 * tube_diameter
fillet_radius = tube_spacing / 3
assert tube_extension > fillet_radius
```

```python
# Build the heat exchanger
tube_locations = [
    l
    for l in HexLocations(
        radius=(tube_diameter + tube_spacing) / 2,
        x_count=exchanger_diameter // tube_diameter,
        y_count=exchanger_diameter // tube_diameter,
    )
    if l.position.length < bundle_diameter / 2
]
```

```python
ring = Circle(tube_diameter / 2) - Circle(tube_diameter / 2 - tube_wall_thickness)
tube_plan = Sketch() + tube_locations * ring
```

```python
heat_exchanger = extrude(tube_plan, exchanger_length / 2)
```

```python
plate_plane = Plane(
    origin=(0, 0, exchanger_length / 2 - tube_extension - plate_thickness),
    z_dir=(0, 0, 1),
)
plate = Circle(radius=exchanger_diameter / 2) - tube_locations * Circle(
    radius=tube_diameter / 2 - tube_wall_thickness
)
```

```python
heat_exchanger += extrude(plate_plane * plate, plate_thickness)
```

<!-- PDF page 147 -->

```python
                                                                      (continued from previous page)
edges = (
    heat_exchanger.edges()
    .filter_by(GeomType.CIRCLE)
    .group_by(SortBy.RADIUS)[1]
    .group_by()[2]
)
half_volume_before_fillet = heat_exchanger.volume
heat_exchanger = fillet(edges, radius=fillet_radius)
half_volume_after_fillet = heat_exchanger.volume
heat_exchanger += mirror(heat_exchanger, Plane.XY)
```

```python
fillet_volume = 2 * (half_volume_after_fillet - half_volume_before_fillet)
assert abs(fillet_volume - 469.88331045553787) < 1e-3
```

```python
show(heat_exchanger)
```

This example creates a model of a parametric heat exchanger core. The positions of the tubes are defined with
HexLocations and further limited to fit within the circular end caps. The ends of the tubes are filleted to the end
plates to simulate welding.

Key Cap

![Extracted image from PDF page 147](../images/examples_1/p147_img023_8f0397796848.png)

<!-- PDF page 148 -->

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import *
```

```python
with BuildPart() as key_cap:
```

```python
    # Start with the plan of the key cap and extrude it
    with BuildSketch() as plan:
```

```python
        Rectangle(18 * MM, 18 * MM)
    extrude(amount=10 * MM, taper=15)
    # Create a dished top
    with Locations((0, -3 * MM, 47 * MM)):
```

```python
        Sphere(40 * MM, mode=Mode.SUBTRACT, rotation=(90, 0, 0))
    # Fillet all the edges except the bottom
    fillet(
        key_cap.edges().filter_by_position(Axis.Z, 0, 30 * MM, inclusive=(False, True)),
        radius=1 * MM,
    )
    # Hollow out the key by subtracting a scaled version
    scale(by=(0.925, 0.925, 0.85), mode=Mode.SUBTRACT)
```

```python
    # Add supporting ribs while leaving room for switch activation
    with BuildSketch(Plane(origin=(0, 0, 4 * MM))):
```

```python
        Rectangle(15 * MM, 0.5 * MM)
        Rectangle(0.5 * MM, 15 * MM)
        Circle(radius=5.5 * MM / 2)
    # Extrude the mount and ribs to the key cap underside
    extrude(until=Until.NEXT)
    # Find the face on the bottom of the ribs to build onto
    rib_bottom = key_cap.faces().filter_by_position(Axis.Z, 4 * MM, 4 * MM)[0]
    # Add the switch socket
    with BuildSketch(rib_bottom) as cruciform:
```

```python
        Circle(radius=5.5 * MM / 2)
        Rectangle(4.1 * MM, 1.17 * MM, mode=Mode.SUBTRACT)
        Rectangle(1.17 * MM, 4.1 * MM, mode=Mode.SUBTRACT)
    extrude(amount=3.5 * MM, mode=Mode.ADD)
```

```python
assert abs(key_cap.part.volume - 644.8900473617498) < 1e-3
```

```python
show(key_cap, alphas=[0.3])
```

Reference Implementation (Algebra Mode)

```python
from build123d import *
from ocp_vscode import *
```

```python
# Taper Extrude and Extrude to "next" while creating a Cherry MX key cap
# See: https://www.cherrymx.de/en/dev.html
```

```python
plan = Rectangle(18 * MM, 18 * MM)
key_cap = extrude(plan, amount=10 * MM, taper=15)
```

```python
# Create a dished top
```

<!-- PDF page 149 -->

```python
                                                                      (continued from previous page)
key_cap -= Location((0, -3 * MM, 47 * MM), (90, 0, 0)) * Sphere(40 * MM)
```

```python
# Fillet all the edges except the bottom
key_cap = fillet(
    key_cap.edges().filter_by_position(Axis.Z, 0, 30 * MM, inclusive=(False, True)),
    radius=1 * MM,
)
```

```python
# Hollow out the key by subtracting a scaled version
key_cap -= scale(key_cap, (0.925, 0.925, 0.85))
```

```python
# Add supporting ribs while leaving room for switch activation
ribs = Rectangle(17.5 * MM, 0.5 * MM)
ribs += Rectangle(0.5 * MM, 17.5 * MM)
ribs += Circle(radius=5.51 * MM / 2)
```

```python
# Extrude the mount and ribs to the key cap underside
key_cap += extrude(Pos(0, 0, 4 * MM) * ribs, until=Until.NEXT, target=key_cap)
```

```python
# Find the face on the bottom of the ribs to build onto
rib_bottom = key_cap.faces().filter_by_position(Axis.Z, 4 * MM, 4 * MM)[0]
```

```python
# Add the switch socket
socket = Circle(radius=5.5 * MM / 2)
socket -= Rectangle(4.1 * MM, 1.17 * MM)
socket -= Rectangle(1.17 * MM, 4.1 * MM)
key_cap += extrude(Plane(rib_bottom) * socket, amount=3.5 * MM)
```

```python
show(key_cap, alphas=[0.3])
```

This example demonstrates the design of a Cherry MX key cap by using extrude with a taper and extrude until next.

<!-- PDF page 150 -->

Maker Coin

![Extracted image from PDF page 150](../images/examples_1/p150_img024_61d84b6f4edc.png)

This example creates the maker coin as defined by Angus on the Maker’s Muse YouTube channel. There are two key
features:

1. the use of DoubleTangentArc to create a smooth transition from the central dish to the outside arc, and

2. embossing the text into the top of the coin not just as a simple extrude but from a projection which results in text
with even depth.

Reference Implementation (Builder Mode)

```python
# Coin Parameters
diameter, thickness = 50 * MM, 10 * MM
```

```python
with BuildPart() as maker_coin:
```

```python
    # On XZ plane draw the profile of half the coin
    with BuildSketch(Plane.XZ) as profile:
```

```python
        with BuildLine() as outline:
            l1 = Polyline((0, thickness * 0.6), (0, 0), ((diameter - thickness) / 2, 0))
            l2 = JernArc(
                start=l1 @ 1, tangent=l1 % 1, radius=thickness / 2, arc_size=300
```

<!-- PDF page 151 -->

```python
                                                                      (continued from previous page)
            )  # extend the arc beyond the intersection but not closed
            l3 = DoubleTangentArc(l1 @ 0, tangent=(1, 0), other=l2)
        make_face()  # make it a 2D shape
    revolve()  # revolve 360°
```

```python
    # Pattern the detents around the coin
    with BuildSketch() as detents:
```

```python
        with PolarLocations(radius=(diameter + 5) / 2, count=8):
```

```python
            Circle(thickness * 1.4 / 2)
    extrude(amount=thickness, mode=Mode.SUBTRACT)  # cut away the detents
```

```python
    fillet(maker_coin.edges(Select.NEW), 2)  # fillet the cut edges
```

```python
    # Add an embossed label
    with BuildSketch(Plane.XY.offset(thickness)) as label:  # above coin
        Text("OS", font_size=15)
    project()  # label on top of coin
    extrude(amount=-thickness / 5, mode=Mode.SUBTRACT)  # emboss label
```

```python
show(maker_coin)
```

<!-- PDF page 152 -->

Multi-Sketch Loft

![Extracted image from PDF page 152](../images/examples_1/p152_img025_5a4ff437ddb8.png)

This example demonstrates lofting a set of sketches, selecting the top and bottom by type, and shelling.

Reference Implementation (Builder Mode)

```python
from math import pi, sin
from build123d import *
from ocp_vscode import show
```

```python
with BuildPart() as art:
    slice_count = 10
    for i in range(slice_count + 1):
```

<!-- PDF page 153 -->

```python
                                                                      (continued from previous page)
        with BuildSketch(Plane(origin=(0, 0, i * 3), z_dir=(0, 0, 1))) as slice:
```

```python
            Circle(10 * sin(i * pi / slice_count) + 5)
    loft()
    top_bottom = art.faces().filter_by(GeomType.PLANE)
    offset(openings=top_bottom, amount=0.5)
```

```python
want = 1306.3405290344635
got = art.part.volume
delta = abs(got - want)
tolerance = want * 1e-5
assert delta < tolerance, f"{delta=} is greater than {tolerance=}; {got=}, {want=}"
```

```python
show(art, names=["art"])
```

Reference Implementation (Algebra Mode)

```python
from math import pi, sin
from build123d import *
from ocp_vscode import show
```

```python
slice_count = 10
```

```python
art = Sketch()
for i in range(slice_count + 1):
    plane = Plane(origin=(0, 0, i * 3), z_dir=(0, 0, 1))
    art += plane * Circle(10 * sin(i * pi / slice_count) + 5)
```

```python
art = loft(art)
top_bottom = art.faces().filter_by(GeomType.PLANE)
art = offset(art, openings=top_bottom, amount=0.5)
```

```python
show(art, names=["art"])
```

<!-- PDF page 154 -->

Peg Board Hook

![Extracted image from PDF page 154](../images/examples_1/p154_img026_4c00dcb31c34.png)

<!-- PDF page 155 -->

This script creates a a J-shaped pegboard hook. These hooks are commonly used for organizing tools in garages,
workshops, or other spaces where tools and equipment need to be stored neatly and accessibly. The hook is created by
defining a complex path and then sweeping it to define the hook. The sides of the hook are flattened to aid 3D printing.

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
pegd = 6.35 + 0.1  # mm ~0.25inch
c2c = 25.4  # mm 1.0inch
arcd = 7.2
both = 10
topx = 6
midx = 8
maind = 0.82 * pegd
midd = 1.0 * pegd
hookd = 23
hookx = 10
splitz = maind / 2 - 0.1
topangs = 70
```

```python
with BuildPart() as mainp:
```

```python
    with BuildLine(mode=Mode.PRIVATE) as sprof:
        l1 = Line((-both, 0), (c2c - arcd / 2 - 0.5, 0))
        l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=arcd / 2, arc_size=topangs)
        l3 = PolarLine(
            start=l2 @ 1,
            length=topx,
            direction=l2 % 1,
        )
        l4 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=arcd / 2, arc_size=-topangs)
        l5 = PolarLine(
            start=l4 @ 1,
            length=topx,
            direction=l4 % 1,
        )
        l6 = JernArc(
            start=l1 @ 0, tangent=(l1 % 0).reverse(), radius=hookd / 2, arc_size=170
        )
        l7 = PolarLine(
            start=l6 @ 1,
            length=hookx,
            direction=l6 % 1,
        )
    with BuildSketch(Plane.YZ):
```

```python
        Circle(radius=maind / 2)
    sweep(path=sprof.wires()[0])
    with BuildLine(mode=Mode.PRIVATE) as stub:
        l7 = Line((0, 0), (0, midx + maind / 2))
    with BuildSketch(Plane.XZ):
```

```python
        Circle(radius=midd / 2)
    sweep(path=stub.wires()[0])
```

<!-- PDF page 156 -->

```python
                                                                      (continued from previous page)
    # splits help keep the object 3d printable by reducing overhang
    split(bisect_by=Plane(origin=(0, 0, -splitz)))
    split(bisect_by=Plane(origin=(0, 0, splitz)), keep=Keep.BOTTOM)
```

```python
show(mainp)
```

Reference Implementation (Algebra Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
pegd = 6.35 + 0.1  # mm ~0.25inch
c2c = 25.4  # mm 1.0inch
arcd = 7.2
both = 10
topx = 6
midx = 8
maind = 0.82 * pegd
midd = 1.0 * pegd
hookd = 23
hookx = 10
splitz = maind / 2 - 0.1
topangs = 70
```

```python
l1 = Line((-both, 0), (c2c - arcd / 2 - 0.5, 0))
l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=arcd / 2, arc_size=topangs)
l3 = PolarLine(
    start=l2 @ 1,
    length=topx,
    direction=l2 % 1,
)
l4 = JernArc(start=l3 @ 1, tangent=l3 % 1, radius=arcd / 2, arc_size=-topangs)
l5 = PolarLine(
    start=l4 @ 1,
    length=topx,
    direction=l4 % 1,
)
l6 = JernArc(start=l1 @ 0, tangent=(l1 % 0).reverse(), radius=hookd / 2, arc_size=170)
l7 = PolarLine(
    start=l6 @ 1,
    length=hookx,
    direction=l6 % 1,
)
sprof = Curve() + (l1, l2, l3, l4, l5, l6, l7)
wire = Wire(sprof.edges())  #  TODO sprof.wires() fails
mainp = sweep(Plane.YZ * Circle(radius=maind / 2), path=wire)
```

```python
stub = Line((0, 0), (0, midx + maind / 2))
mainp += sweep(Plane.XZ * Circle(radius=midd / 2), path=stub)
```

<!-- PDF page 157 -->

```python
                                                                      (continued from previous page)
# splits help keep the object 3d printable by reducing overhang
mainp = split(mainp, Plane(origin=(0, 0, -splitz)))
mainp = split(mainp, Plane(origin=(0, 0, splitz)), keep=Keep.BOTTOM)
```

```python
show(mainp)
```

Platonic Solids

![Extracted image from PDF page 157](../images/examples_1/p157_img027_97f4f9d6f846.png)

This example creates a custom Part object PlatonicSolid.

Platonic solids are five three-dimensional shapes that are highly symmetrical, known since antiquity and named after
the ancient Greek philosopher Plato. These solids are unique because their faces are congruent regular polygons, with
the same number of faces meeting at each vertex. The five Platonic solids are the tetrahedron (4 triangular faces), cube
(6 square faces), octahedron (8 triangular faces), dodecahedron (12 pentagonal faces), and icosahedron (20 triangular
faces). Each solid represents a unique way in which identical polygons can be arranged in three dimensions to form a
convex polyhedron, embodying ideals of symmetry and balance.

<!-- PDF page 158 -->

Reference Implementation (Algebra Mode)

```python
from build123d import *
from math import sqrt
from typing import Union, Literal
from scipy.spatial import ConvexHull
```

```python
from ocp_vscode import show
```

```python
PHI = (1 + sqrt(5)) / 2  # The Golden Ratio
```

```python
class PlatonicSolid(BasePartObject):
```

```python
    """Part Object: Platonic Solid
```

```python
    Create one of the five convex Platonic solids.
```

```python
    Args:
```

```python
        face_count (Literal[4,6,8,12,20]): number of faces
        diameter (float): double distance to vertices, i.e. maximum size
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        align (Union[None, Align, tuple[Align, Align, Align]], optional): align min, center,
```

```python
            or max of object. Defaults to None.
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """
```

```python
    tetrahedron_vertices = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
```

```python
    cube_vertices = [(i, j, k) for i in [-1, 1] for j in [-1, 1] for k in [-1, 1]]
```

```python
    octahedron_vertices = (
        [(i, 0, 0) for i in [-1, 1]]
        + [(0, i, 0) for i in [-1, 1]]
        + [(0, 0, i) for i in [-1, 1]]
    )
```

```python
    dodecahedron_vertices = (
        [(i, j, k) for i in [-1, 1] for j in [-1, 1] for k in [-1, 1]]
        + [(0, i / PHI, j * PHI) for i in [-1, 1] for j in [-1, 1]]
        + [(i / PHI, j * PHI, 0) for i in [-1, 1] for j in [-1, 1]]
        + [(i * PHI, 0, j / PHI) for i in [-1, 1] for j in [-1, 1]]
    )
```

```python
    icosahedron_vertices = (
        [(0, i, j * PHI) for i in [-1, 1] for j in [-1, 1]]
        + [(i, j * PHI, 0) for i in [-1, 1] for j in [-1, 1]]
        + [(i * PHI, 0, j) for i in [-1, 1] for j in [-1, 1]]
    )
```

```python
    vertices_lookup = {
```

```python
        4: tetrahedron_vertices,
        6: cube_vertices,
        8: octahedron_vertices,
```

<!-- PDF page 159 -->

```python
                                                                      (continued from previous page)
        12: dodecahedron_vertices,
        20: icosahedron_vertices,
    }
    _applies_to = [BuildPart._tag]
```

```python
    def __init__(
```

```python
        self,
        face_count: Literal[4, 6, 8, 12, 20],
        diameter: float = 1.0,
        rotation: RotationLike = (0, 0, 0),
        align: Union[None, Align, tuple[Align, Align, Align]] = None,
        mode: Mode = Mode.ADD,
    ):
```

```python
        try:
            platonic_vertices = PlatonicSolid.vertices_lookup[face_count]
        except KeyError:
```

```python
            raise ValueError(
```

```python
                f"face_count must be one of 4, 6, 8, 12, or 20 not {face_count}"
            )
```

```python
        # Create a convex hull from the vertices
        hull = ConvexHull(platonic_vertices).simplices.tolist()
```

```python
        # Create faces from the vertex indices
        platonic_faces = []
        for face_vertex_indices in hull:
            corner_vertices = [platonic_vertices[i] for i in face_vertex_indices]
            platonic_faces.append(Face(Wire.make_polygon(corner_vertices)))
```

```python
        # Create the solid from the Faces
        platonic_solid = Solid(Shell(platonic_faces)).clean()
```

```python
        # By definition, all vertices are the same distance from the origin so
        # scale proportionally to this distance
        platonic_solid = platonic_solid.scale(
            (diameter / 2) / Vector(platonic_solid.vertices()[0]).length
        )
```

```python
        super().__init__(part=platonic_solid, rotation=rotation, align=align, mode=mode)
```

```python
solids = [
```

```python
    Rot(0, 0, 72 * i) * Pos(1, 0, 0) * PlatonicSolid(faces)
    for i, faces in enumerate([4, 6, 8, 12, 20])
]
show(solids)
```

<!-- PDF page 160 -->

Playing Cards

![Extracted image from PDF page 160](../images/examples_1/p160_img028_965394814481.png)

This example creates a customs Sketch objects: Club, Spade, Heart, Diamond, and PlayingCard in addition to a two
part playing card box which has suit cutouts in the lid. The four suits are created with Bézier curves that were imported
as code from an SVG file and modified to the code found here.

Reference Implementation (Builder Mode)

```python
from typing import Literal
from build123d import *
from ocp_vscode import show_object
```

<!-- PDF page 161 -->

```python
# [Club]
class Club(BaseSketchObject):
```

```python
    def __init__(
```

```python
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
```

```python
        with BuildSketch() as club:
```

```python
            with BuildLine():
                l0 = Line((0, -188), (76, -188))
                b0 = Bezier(l0 @ 1, (61, -185), (33, -173), (17, -81))
                b1 = Bezier(b0 @ 1, (49, -128), (146, -145), (167, -67))
                b2 = Bezier(b1 @ 1, (187, 9), (94, 52), (32, 18))
                b3 = Bezier(b2 @ 1, (92, 57), (113, 188), (0, 188))
                mirror(about=Plane.YZ)
            make_face()
            scale(by=height / club.sketch.bounding_box().size.Y)
        super().__init__(obj=club.sketch, rotation=rotation, align=align, mode=mode)
```

```python
# [Club]
```

```python
class Spade(BaseSketchObject):
```

```python
    def __init__(
```

```python
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
```

```python
        with BuildSketch() as spade:
```

```python
            with BuildLine():
                b0 = Bezier((0, 198), (6, 190), (41, 127), (112, 61))
                b1 = Bezier(b0 @ 1, (242, -72), (114, -168), (11, -105))
                b2 = Bezier(b1 @ 1, (31, -174), (42, -179), (53, -198))
                l0 = Line(b2 @ 1, (0, -198))
                mirror(about=Plane.YZ)
            make_face()
            scale(by=height / spade.sketch.bounding_box().size.Y)
        super().__init__(obj=spade.sketch, rotation=rotation, align=align, mode=mode)
```

```python
class Heart(BaseSketchObject):
```

```python
    def __init__(
```

```python
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
```

<!-- PDF page 162 -->

```python
                                                                      (continued from previous page)
        mode: Mode = Mode.ADD,
    ):
```

```python
        with BuildSketch() as heart:
```

```python
            with BuildLine():
                b1 = Bezier((0, 146), (20, 169), (67, 198), (97, 198))
                b2 = Bezier(b1 @ 1, (125, 198), (151, 186), (168, 167))
                b3 = Bezier(b2 @ 1, (197, 133), (194, 88), (158, 31))
                b4 = Bezier(b3 @ 1, (126, -13), (94, -48), (62, -95))
                b5 = Bezier(b4 @ 1, (40, -128), (0, -198))
                mirror(about=Plane.YZ)
            make_face()
            scale(by=height / heart.sketch.bounding_box().size.Y)
        super().__init__(obj=heart.sketch, rotation=rotation, align=align, mode=mode)
```

```python
class Diamond(BaseSketchObject):
```

```python
    def __init__(
```

```python
        self,
        height: float,
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
```

```python
        with BuildSketch() as diamond:
```

```python
            with BuildLine():
```

```python
                Bezier((135, 0), (94, 69), (47, 134), (0, 198))
                mirror(about=Plane.XZ)
                mirror(about=Plane.YZ)
            make_face()
            scale(by=height / diamond.sketch.bounding_box().size.Y)
        super().__init__(obj=diamond.sketch, rotation=rotation, align=align, mode=mode)
```

```python
card_width = 2.5 * IN
card_length = 3.5 * IN
deck = 0.5 * IN
wall = 4 * MM
gap = 0.5 * MM
```

```python
with BuildPart() as box_builder:
```

```python
    with BuildSketch() as plan:
```

```python
        Rectangle(card_width + 2 * wall, card_length + 2 * wall)
        fillet(plan.vertices(), radius=card_width / 15)
    extrude(amount=wall / 2)
    with BuildSketch(box_builder.faces().sort_by(Axis.Z)[-1]) as walls:
```

```python
        add(plan.sketch)
        offset(plan.sketch, amount=-wall, mode=Mode.SUBTRACT)
    extrude(amount=deck / 2)
    with BuildSketch(box_builder.faces().sort_by(Axis.Z)[-1]) as inset_walls:
```

```python
        offset(plan.sketch, amount=-(wall + gap) / 2, mode=Mode.ADD)
        offset(plan.sketch, amount=-wall, mode=Mode.SUBTRACT)
    extrude(amount=deck / 2)
```

<!-- PDF page 163 -->

```python
with BuildPart() as lid_builder:
```

```python
    with BuildSketch() as outset_walls:
```

```python
        add(plan.sketch)
        offset(plan.sketch, amount=-(wall - gap) / 2, mode=Mode.SUBTRACT)
    extrude(amount=deck / 2)
    with BuildSketch(lid_builder.faces().sort_by(Axis.Z)[-1]) as top:
```

```python
        add(plan.sketch)
    extrude(amount=wall / 2)
    with BuildSketch(lid_builder.faces().sort_by(Axis.Z)[-1]):
        holes = GridLocations(
```

```python
            3 * card_width / 5, 3 * card_length / 5, 2, 2
        ).local_locations
        for i, hole in enumerate(holes):
```

```python
            with Locations(hole) as hole_loc:
```

```python
                if i == 0:
                    Heart(card_length / 5)
                elif i == 1:
                    Diamond(card_length / 5)
                elif i == 2:
                    Spade(card_length / 5)
                elif i == 3:
                    Club(card_length / 5)
    extrude(amount=-wall, mode=Mode.SUBTRACT)
```

```python
box = Compound(
    [box_builder.part, lid_builder.part.moved(Location((0, 0, (wall + deck) / 2)))]
)
visible, hidden = box.project_to_viewport((70, -50, 120))
max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)
exporter = ExportSVG(scale=100 / max_dimension)
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
exporter.add_shape(visible, layer="Visible")
exporter.add_shape(hidden, layer="Hidden")
# exporter.write(f"assets/card_box.svg")
```

```python
class PlayingCard(BaseSketchObject):
```

```python
    """PlayingCard
```

```python
    A standard playing card modelled as a Face.
```

```python
    Args:
```

```python
        rank (Literal['A', '2' .. '10', 'J', 'Q', 'K']): card rank
        suit (Literal['Clubs', 'Spades', 'Hearts', 'Diamonds']): card suit
    """
```

```python
    width = 2.5 * IN
    height = 3.5 * IN
    suits = {"Clubs": Club, "Spades": Spade, "Hearts": Heart, "Diamonds": Diamond}
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
```

<!-- PDF page 164 -->

```python
    def __init__(
```

```python
        self,
        rank: Literal["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"],
        suit: Literal["Clubs", "Spades", "Hearts", "Diamonds"],
        rotation: float = 0,
        align: tuple[Align, Align] = (Align.CENTER, Align.CENTER),
        mode: Mode = Mode.ADD,
    ):
```

```python
        with BuildSketch() as playing_card:
```

```python
            Rectangle(
                PlayingCard.width, PlayingCard.height, align=(Align.MIN, Align.MIN)
            )
            fillet(playing_card.vertices(), radius=PlayingCard.width / 15)
            with Locations(
                (
                    PlayingCard.width / 7,
                    8 * PlayingCard.height / 9,
                )
            ):
```

```python
                Text(
                    txt=rank,
                    font_size=PlayingCard.width / 7,
                    mode=Mode.SUBTRACT,
                )
            with Locations(
                (
                    PlayingCard.width / 7,
                    7 * PlayingCard.height / 9,
                )
            ):
                PlayingCard.suits[suit](
                    height=PlayingCard.width / 12, mode=Mode.SUBTRACT
                )
            with Locations(
                (
```

```python
                    6 * PlayingCard.width / 7,
                    1 * PlayingCard.height / 9,
                )
            ):
```

```python
                Text(
                    txt=rank,
                    font_size=PlayingCard.width / 7,
                    rotation=180,
                    mode=Mode.SUBTRACT,
                )
            with Locations(
                (
```

```python
                    6 * PlayingCard.width / 7,
                    2 * PlayingCard.height / 9,
                )
            ):
```

<!-- PDF page 165 -->

```python
                                                                      (continued from previous page)
                PlayingCard.suits[suit](
                    height=PlayingCard.width / 12, rotation=180, mode=Mode.SUBTRACT
                )
            rank_int = PlayingCard.ranks.index(rank) + 1
            rank_int = rank_int if rank_int < 10 else 1
            with Locations((PlayingCard.width / 2, PlayingCard.height / 2)):
                center_radius = 0 if rank_int == 1 else PlayingCard.width / 3.5
                suit_rotation = 0 if rank_int == 1 else -90
                suit_height = (
```

```python
                    0.00159 * rank_int**2 - 0.0380 * rank_int + 0.37
                ) * PlayingCard.width
                with PolarLocations(
                    radius=center_radius,
                    count=rank_int,
                    start_angle=90 if rank_int > 1 else 0,
                ):
                    PlayingCard.suits[suit](
                        height=suit_height,
                        rotation=suit_rotation,
                        mode=Mode.SUBTRACT,
                    )
        super().__init__(
            obj=playing_card.sketch, rotation=rotation, align=align, mode=mode
        )
```

```python
ace_spades = PlayingCard(rank="A", suit="Spades", align=Align.MIN)
ace_spades.color = Color("white")
king_hearts = PlayingCard(rank="K", suit="Hearts", align=Align.MIN)
king_hearts.color = Color("white")
queen_clubs = PlayingCard(rank="Q", suit="Clubs", align=Align.MIN)
queen_clubs.color = Color("white")
jack_diamonds = PlayingCard(rank="J", suit="Diamonds", align=Align.MIN)
jack_diamonds.color = Color("white")
ten_spades = PlayingCard(rank="10", suit="Spades", align=Align.MIN)
ten_spades.color = Color("white")
```

```python
hand = Compound(
    children=[
```

```python
        Rot(0, 0, -20) * Pos(0, 0, 0) * ace_spades,
        Rot(0, 0, -10) * Pos(0, 0, -1) * king_hearts,
        Rot(0, 0, 0) * Pos(0, 0, -2) * queen_clubs,
        Rot(0, 0, 10) * Pos(0, 0, -3) * jack_diamonds,
        Rot(0, 0, 20) * Pos(0, 0, -4) * ten_spades,
    ]
)
```

```python
show_object(Pos(-20, 40) * hand)
show_object(box_builder.part, "box_builder")
show_object(
```

```python
    Pos(0, 0, (wall + deck) / 2) * lid_builder.part,
    "lid_builder",
```

<!-- PDF page 166 -->

```python
                                                                      (continued from previous page)
    options={"alpha": 0.7},
)
```

Stud Wall

![Extracted image from PDF page 166](../images/examples_1/p166_img029_0f39567a3304.png)

This example demonstrates creating custom Part objects and putting them into assemblies. The custom object is a Stud
used in the building industry while the assembly is a StudWall created from copies of Stud objects for efficiency. Both
the Stud and StudWall objects use RigidJoints to define snap points which are used to position all of objects.

<!-- PDF page 167 -->

Reference Implementation (Algebra Mode)

```python
class Stud(BasePartObject):
```

```python
    """Part Object: Stud
```

```python
    Create a dimensional framing stud.
```

```python
    Args:
```

```python
        length (float): stud size
        width (float): stud size
        thickness (float): stud size
        rotation (RotationLike, optional): angles to rotate about axes. Defaults to (0, 0, 0).
        align (Union[Align, tuple[Align, Align, Align]], optional): align min, center,
```

```python
            or max of object. Defaults to (Align.CENTER, Align.CENTER, Align.MIN).
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """
```

```python
    _applies_to = [BuildPart._tag]
```

```python
    def __init__(
```

```python
        self,
        length: float = 8 * FT,
        width: float = 3.5 * IN,
        thickness: float = 1.5 * IN,
        rotation: RotationLike = (0, 0, 0),
        align: Union[None, Align, tuple[Align, Align, Align]] = (
```

```python
            Align.CENTER,
            Align.CENTER,
            Align.MIN,
        ),
        mode: Mode = Mode.ADD,
    ):
```

```python
        self.length = length
        self.width = width
        self.thickness = thickness
```

```python
        # Create the basic shape
        with BuildPart() as stud:
```

```python
            with BuildSketch():
```

```python
                RectangleRounded(thickness, width, 0.25 * IN)
            extrude(amount=length)
```

```python
        # Create a Part object with appropriate alignment and rotation
        super().__init__(part=stud.part, rotation=rotation, align=align, mode=mode)
```

```python
        # Add joints to the ends of the stud
        RigidJoint("end0", self, Location())
        RigidJoint("end1", self, Location((0, 0, length), (1, 0, 0), 180))
```

```python
class StudWall(Compound):
```

```python
    """StudWall
```

<!-- PDF page 168 -->

A simple stud wall assembly with top and sole plates.

```python
    Args:
```

```python
        length (float): wall length
        depth (float, optional): stud width. Defaults to 3.5*IN.
        height (float, optional): wall height. Defaults to 8*FT.
        stud_spacing (float, optional): center-to-center. Defaults to 16*IN.
        stud_thickness (float, optional): Defaults to 1.5*IN.
    """
```

```python
    def __init__(
```

```python
        self,
        length: float,
        depth: float = 3.5 * IN,
        height: float = 8 * FT,
        stud_spacing: float = 16 * IN,
        stud_thickness: float = 1.5 * IN,
    ):
```

```python
        # Create the object that will be used for top and sole plates
        plate = Stud(
            length,
            depth,
            rotation=(0, -90, 0),
            align=(Align.MIN, Align.CENTER, Align.MAX),
        )
        # Define where studs will go on the plates
        stud_locations = Pos(stud_thickness / 2, 0, stud_thickness) * GridLocations(
            stud_spacing, 0, int(length / stud_spacing) + 1, 1, align=Align.MIN
        )
        stud_locations.append(Pos(length - stud_thickness / 2, 0, stud_thickness))
```

```python
        # Create a single stud that will be copied for efficiency
        stud = Stud(height - 2 * stud_thickness, depth, stud_thickness)
```

```python
        # For efficiency studs in the walls are copies with their own position
        studs = []
        for i, loc in enumerate(stud_locations):
            stud_joint = RigidJoint(f"stud{i}", plate, loc)
            stud_copy = copy.copy(stud)
            stud_joint.connect_to(stud_copy.joints["end0"])
            studs.append(stud_copy)
        top_plate = copy.copy(plate)
        sole_plate = copy.copy(plate)
```

```python
        # Position the top plate relative to the top of the first stud
        studs[0].joints["end1"].connect_to(top_plate.joints["stud0"])
```

```python
        # Build the assembly of parts
        super().__init__(children=[top_plate, sole_plate] + studs)
```

```python
        # Add joints to the wall
        RigidJoint("inside0", self, Location((depth / 2, depth / 2, 0), (0, 0, 1), 90))
```

<!-- PDF page 169 -->

```python
                                                                      (continued from previous page)
        RigidJoint("end0", self, Location())
```

```python
x_wall = StudWall(13 * FT)
y_wall = StudWall(9 * FT)
x_wall.joints["inside0"].connect_to(y_wall.joints["end0"])
```

```python
show(x_wall, y_wall, render_joints=False)
```

Tea Cup

![Extracted image from PDF page 169](../images/examples_1/p169_img030_dfdd6278e3eb.png)

<!-- PDF page 170 -->

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
wall_thickness = 3 * MM
fillet_radius = wall_thickness * 0.49
```

```python
with BuildPart() as tea_cup:
```

```python
    # Create the bowl of the cup as a revolved cross section
    with BuildSketch(Plane.XZ) as bowl_section:
```

```python
        with BuildLine():
```

```python
            # Start & end points with control tangents
            s = Spline(
                (30 * MM, 10 * MM),
                (69 * MM, 105 * MM),
                tangents=((1, 0.5), (0.7, 1)),
                tangent_scalars=(1.75, 1),
            )
            # Lines to finish creating ½ the bowl shape
            Polyline(s @ 0, s @ 0 + (10 * MM, -10 * MM), (0, 0), (0, (s @ 1).Y), s @ 1)
        make_face()  # Create a filled 2D shape
    revolve(axis=Axis.Z)
    # Hollow out the bowl with openings on the top and bottom
    offset(amount=-wall_thickness, openings=tea_cup.faces().filter_by(GeomType.PLANE))
    # Add a bottom to the bowl
    with Locations((0, 0, (s @ 0).Y)):
```

```python
        Cylinder(radius=(s @ 0).X, height=wall_thickness)
    # Smooth out all the edges
    fillet(tea_cup.edges(), radius=fillet_radius)
```

```python
    # Determine where the handle contacts the bowl
    handle_intersections = [
        tea_cup.part.find_intersection_points(
```

```python
            Axis(origin=(0, 0, vertical_offset), direction=(1, 0, 0))
        )[-1][0]
        for vertical_offset in [35 * MM, 80 * MM]
    ]
    # Create a path for handle creation
    with BuildLine(Plane.XZ) as handle_path:
```

```python
        Spline(
            handle_intersections[0] - (wall_thickness / 2, 0),
            handle_intersections[0] + (35 * MM, 30 * MM),
            handle_intersections[0] + (40 * MM, 60 * MM),
            handle_intersections[1] - (wall_thickness / 2, 0),
            tangents=((1, 1.25), (-0.2, -1)),
        )
    # Align the cross section to the beginning of the path
    with BuildSketch(handle_path.line ^ 0) as handle_cross_section:
```

```python
        RectangleRounded(wall_thickness, 8 * MM, fillet_radius)
    sweep()  # Sweep handle cross section along path
```

```python
assert abs(tea_cup.part.volume - 130326) < 1
```

<!-- PDF page 171 -->

```python
show(tea_cup, names=["tea cup"])
```

Reference Implementation (Algebra Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
wall_thickness = 3 * MM
fillet_radius = wall_thickness * 0.49
```

```python
# Create the bowl of the cup as a revolved cross section
```

```python
# Start & end points with control tangents
s = Spline(
    (30 * MM, 10 * MM),
    (69 * MM, 105 * MM),
    tangents=((1, 0.5), (0.7, 1)),
    tangent_scalars=(1.75, 1),
)
# Lines to finish creating ½ the bowl shape
s += Polyline(s @ 0, s @ 0 + (10 * MM, -10 * MM), (0, 0), (0, (s @ 1).Y), s @ 1)
bowl_section = Plane.XZ * make_face(s)  # Create a filled 2D shape
tea_cup = revolve(bowl_section, axis=Axis.Z)
```

```python
# Hollow out the bowl with openings on the top and bottom
tea_cup = offset(
    tea_cup, -wall_thickness, openings=tea_cup.faces().filter_by(GeomType.PLANE)
)
```

```python
# Add a bottom to the bowl
tea_cup += Pos(0, 0, (s @ 0).Y) * Cylinder(radius=(s @ 0).X, height=wall_thickness)
```

```python
# Smooth out all the edges
tea_cup = fillet(tea_cup.edges(), radius=fillet_radius)
```

```python
# Determine where the handle contacts the bowl
handle_intersections = [
    tea_cup.find_intersection_points(
```

```python
        Axis(origin=(0, 0, vertical_offset), direction=(1, 0, 0))
    )[-1][0]
    for vertical_offset in [35 * MM, 80 * MM]
]
```

```python
# Create a path for handle creation
path_spline = Spline(
    handle_intersections[0] - (wall_thickness / 2, 0, 0),
    handle_intersections[0] + (35 * MM, 0, 30 * MM),
    handle_intersections[0] + (40 * MM, 0, 60 * MM),
    handle_intersections[1] - (wall_thickness / 2, 0, 0),
    tangents=((1, 0, 1.25), (-0.2, 0, -1)),
```

<!-- PDF page 172 -->

)

```python
# Align the cross section to the beginning of the path
location = path_spline ^ 0
handle_cross_section = location * RectangleRounded(wall_thickness, 8 * MM, fillet_radius)
```

```python
# Sweep handle cross section along path
tea_cup += sweep(handle_cross_section, path=path_spline)
```

```python
# assert abs(tea_cup.part.volume - 130326.77052487945) < 1e-3
```

```python
show(tea_cup, names=["tea cup"])
```

This example demonstrates the creation a tea cup, which serves as an example of constructing complex, non-flat geo-
metrical shapes programmatically.

The tea cup model involves several CAD techniques, such as:

• Revolve Operations: There is 1 occurrence of a revolve operation. This is used to create the main body of the tea
cup by revolving a profile around an axis, a common technique for generating symmetrical objects like cups.

• Sweep Operations: There are 2 occurrences of sweep operations. The handle are created by sweeping a profile
along a path to generate non-planar surfaces.

• Offset/Shell Operations: the bowl of the cup is hollowed out with the offset operation leaving the top open.

• Fillet Operations: There is 1 occurrence of a fillet operation which is used to round the edges for aesthetic
improvement and to mimic real-world objects more closely.

<!-- PDF page 173 -->

Toy Truck

![Extracted image from PDF page 173](../images/examples_1/p173_img031_08f26841bcad.png)

<!-- PDF page 174 -->

![Extracted image from PDF page 174](../images/examples_1/p174_img032_cc07450564af.jpg)

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import show
```

```python
# Toy Truck Blue
truck_color = Color(0x4683CE)
```

```python
# Create the main truck body — from bumper to bed, excluding the cab
with BuildPart() as body:
```

```python
    # The body has two axes of symmetry, so we start with a centered sketch.
    # The default workplane is Plane.XY.
    with BuildSketch() as body_skt:
```

```python
        Rectangle(20, 35)
        # Fillet all the corners of the sketch.
        # Alternatively, you could use RectangleRounded.
        fillet(body_skt.vertices(), 1)
```

```python
    # Extrude the body shape upward
    extrude(amount=10, taper=4)
    # Reuse the sketch by accessing it explicitly
    extrude(body_skt.sketch, amount=8, taper=2)
```

```python
    # Create symmetric fenders on Plane.YZ
    with BuildSketch(Plane.YZ) as fender:
```

```python
        # The trapezoid has asymmetric angles (80°, 88°)
```

<!-- PDF page 175 -->

```python
                                                                      (continued from previous page)
        Trapezoid(18, 6, 80, 88, align=Align.MIN)
        # Fillet top edge vertices (Y-direction highest group)
        fillet(fender.vertices().group_by(Axis.Y)[-1], 1.5)
```

```python
    # Extrude the fender in both directions
    extrude(amount=10.5, both=True)
```

```python
    # Create wheel wells with a shifted sketch on Plane.YZ
    with BuildSketch(Plane.YZ.shift_origin((0, 3.5, 0))) as wheel_well:
```

```python
        Trapezoid(12, 4, 70, 85, align=Align.MIN)
        fillet(wheel_well.vertices().group_by(Axis.Y)[-1], 2)
```

```python
    # Subtract the wheel well geometry
    extrude(amount=10.5, both=True, mode=Mode.SUBTRACT)
```

```python
    # Fillet the top edges of the body
    fillet(body.edges().group_by(Axis.Z)[-1], 1)
```

```python
    # Isolate a set of body edges and preview before filleting
    body_edges = body.edges().group_by(Axis.Z)[-6]
    fillet(body_edges, 0.1)
```

```python
    # Combine edge groups from both sides of the fender and fillet them
    fender_edges = body.edges().group_by(Axis.X)[0] + body.edges().group_by(Axis.X)[-1]
    fender_edges = fender_edges.group_by(Axis.Z)[1:]
    fillet(fender_edges, 0.4)
```

```python
    # Create a sketch on the front of the truck for the grill
    with BuildSketch(
```

```python
        Plane.XZ.offset(-body.vertices().sort_by(Axis.Y)[-1].Y - 0.5)
    ) as grill:
```

```python
        Rectangle(16, 8.5, align=(Align.CENTER, Align.MIN))
        fillet(grill.vertices().group_by(Axis.Y)[-1], 1)
```

```python
        # Add headlights (subtractive circles)
        with Locations((0, 6.5)):
```

```python
            with GridLocations(12, 0, 2, 1):
```

```python
                Circle(1, mode=Mode.SUBTRACT)
```

```python
        # Add air vents (subtractive slots)
        with Locations((0, 3)):
```

```python
            with GridLocations(0, 0.8, 1, 4):
```

```python
                SlotOverall(10, 0.5, mode=Mode.SUBTRACT)
```

```python
    # Extrude the grill forward
    extrude(amount=2)
```

```python
    # Fillet only the outer grill edges (exclude headlight/vent cuts)
    grill_perimeter = body.faces().sort_by(Axis.Y)[-1].outer_wire()
    fillet(grill_perimeter.edges(), 0.2)
```

```python
    # Create the bumper as a separate part inside the body
```

<!-- PDF page 176 -->

```python
                                                                      (continued from previous page)
    with BuildPart() as bumper:
```

```python
        # Find the midpoint of a front edge and shift slightly to position the bumper
        front_cnt = body.edges().group_by(Axis.Z)[0].sort_by(Axis.Y)[-1] @ 0.5 - (0, 3)
```

```python
        with BuildSketch() as bumper_plan:
```

```python
            # Use BuildLine to draw an elliptical arc and offset
            with BuildLine():
```

```python
                EllipticalCenterArc(front_cnt, 20, 4, start_angle=60, arc_size=60)
                offset(amount=1)
            make_face()
```

```python
        # Extrude the bumper symmetrically
        extrude(amount=1, both=True)
        fillet(bumper.edges(), 0.25)
```

```python
    # Define a joint on top of the body to connect the cab later
    RigidJoint("body_top", joint_location=Location((0, -7.5, 10)))
    body.part.color = truck_color
```

```python
# Create the cab as an independent part to mount on the body
with BuildPart() as cab:
```

```python
    with BuildSketch() as cab_plan:
```

```python
        RectangleRounded(16, 16, 1)
        # Split the sketch to work on one symmetric half
        split(bisect_by=Plane.YZ)
```

```python
    # Extrude the cab forward and upward at an angle
    extrude(amount=7, dir=(0, 0.15, 1))
    fillet(cab.edges().group_by(Axis.Z)[-1].group_by(Axis.X)[1:], 1)
```

```python
    # Rear window
    with BuildSketch(Plane.XZ.shift_origin((0, 0, 3))) as rear_window:
```

```python
        RectangleRounded(8, 4, 0.75)
    extrude(amount=10, mode=Mode.SUBTRACT)
```

```python
    # Front window
    with BuildSketch(Plane.XZ) as front_window:
```

```python
        RectangleRounded(15.2, 11, 0.75)
    extrude(amount=-10, mode=Mode.SUBTRACT)
```

```python
    # Side windows
    with BuildSketch(Plane.YZ) as side_window:
```

```python
        with Locations((3.5, 0)):
```

```python
            with GridLocations(10, 0, 2, 1):
```

```python
                Trapezoid(9, 5.5, 80, 100, align=(Align.CENTER, Align.MIN))
                fillet(side_window.vertices().group_by(Axis.Y)[-1], 0.5)
    extrude(amount=12, both=True, mode=Mode.SUBTRACT)
```

```python
    # Mirror to complete the cab
    mirror(about=Plane.YZ)
```

```python
    # Define joint on cab base
```

<!-- PDF page 177 -->

```python
                                                                      (continued from previous page)
    RigidJoint("cab_base", joint_location=Location((0, 0, 0)))
    cab.part.color = truck_color
```

```python
# Attach the cab to the truck body using joints
body.joints["body_top"].connect_to(cab.joints["cab_base"])
```

```python
# Show the result
show(body.part, cab.part)
```

This example demonstrates how to design a toy truck using BuildPart and BuildSketch in Builder mode. The model
includes a detailed body, cab, grill, and bumper, showcasing techniques like sketch reuse, symmetry, tapered extrusions,
selective filleting, and the use of joints for part assembly. Ideal for learning complex part construction and hierarchical
modeling in build123d.

<!-- PDF page 178 -->

Vase

![Extracted image from PDF page 178](../images/examples_1/p178_img033_dfc509074874.png)

<!-- PDF page 179 -->

Reference Implementation (Builder Mode)

```python
from build123d import *
from ocp_vscode import show_object
```

```python
with BuildPart() as vase:
```

```python
    with BuildSketch() as profile:
```

```python
        with BuildLine() as outline:
            l1 = Line((0, 0), (12, 0))
            l2 = RadiusArc(l1 @ 1, (15, 20), 50)
            l3 = Spline(l2 @ 1, (22, 40), (20, 50), tangents=(l2 % 1, (-0.75, 1)))
            l4 = RadiusArc(l3 @ 1, l3 @ 1 + Vector(0, 5), 5)
            l5 = Spline(
                l4 @ 1,
                l4 @ 1 + Vector(2.5, 2.5),
                l4 @ 1 + Vector(0, 5),
                tangents=(l4 % 1, (-1, 0)),
            )
            Polyline(
                l5 @ 1,
                l5 @ 1 + Vector(0, 1),
                (0, (l5 @ 1).Y + 1),
                l1 @ 0,
            )
        make_face()
    revolve(axis=Axis.Y)
    offset(openings=vase.faces().filter_by(Axis.Y)[-1], amount=-1)
    top_edges = (
        vase.edges().filter_by_position(Axis.Y, 60, 62).filter_by(GeomType.CIRCLE)
    )
    fillet(top_edges, radius=0.25)
    fillet(vase.edges().sort_by(Axis.Y)[0], radius=0.5)
```

```python
show_object(Rot(90, 0, 0) * vase.part, name="vase")
```

Reference Implementation (Algebra Mode)

```python
from build123d import *
from ocp_vscode import show_object
```

```python
l1 = Line((0, 0), (12, 0))
l2 = RadiusArc(l1 @ 1, (15, 20), 50)
l3 = Spline(l2 @ 1, (22, 40), (20, 50), tangents=(l2 % 1, (-0.75, 1)))
l4 = RadiusArc(l3 @ 1, l3 @ 1 + Vector(0, 5), 5)
l5 = Spline(
    l4 @ 1,
    l4 @ 1 + Vector(2.5, 2.5),
    l4 @ 1 + Vector(0, 5),
    tangents=(l4 % 1, (-1, 0)),
)
outline = l1 + l2 + l3 + l4 + l5
outline += Polyline(
```

<!-- PDF page 180 -->

```python
                                                                      (continued from previous page)
    l5 @ 1,
    l5 @ 1 + Vector(0, 1),
    (0, (l5 @ 1).Y + 1),
    l1 @ 0,
)
profile = make_face(outline.edges())
vase = revolve(profile, Axis.Y)
vase = offset(vase, openings=vase.faces().sort_by(Axis.Y).last, amount=-1)
```

```python
top_edges = vase.edges().filter_by(GeomType.CIRCLE).filter_by_position(Axis.Y, 60, 62)
vase = fillet(top_edges, radius=0.25)
```

```python
vase = fillet(vase.edges().sort_by(Axis.Y).first, radius=0.5)
```

```python
show_object(Rot(90, 0, 0) * vase, name="vase")
```

This example demonstrates the build123d techniques involving the creation of a vase. Specifically, it showcases the
processes of revolving a sketch, shelling (creating a hollow object by removing material from its interior), and selecting
edges by position range and type for the application of fillets (rounding off the edges).

• Sketching: Drawing a 2D profile or outline that represents the side view of the vase.

• Revolving: Rotating the sketch around an axis to create a 3D object. This step transforms the 2D profile into a
3D vase shape.

• Offset/Shelling: Removing material from the interior of the solid vase to create a hollow space, making it resem-
ble a real vase more closely.

• Edge Filleting: Selecting specific edges of the vase for filleting, which involves rounding those edges. The edges
are selected based on their position and type.
