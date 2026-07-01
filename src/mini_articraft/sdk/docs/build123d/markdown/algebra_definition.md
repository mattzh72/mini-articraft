---
title: "Algebraic definition"
source_html: "https://build123d.readthedocs.io/en/latest/algebra_definition.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "370-371"
generated_on: "2026-07-01"
---

# Algebraic definition

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 370 -->

1.18.3 Algebraic definition

Objects and arithmetic

Set definitions:

𝐶3 is the set of all Part objects p with p._dim = 3

𝐶2 is the set of all Sketch objects s with s._dim = 2

𝐶1 is the set of all Curve objects c with c._dim = 1

Neutral elements:

𝑐3 0 is the empty Part object p0 = Part() with p0._dim = 3 and p0.wrapped = None

𝑐2 0 is the empty Sketch object s0 = Sketch() with s0._dim = 2 and s0.wrapped = None

𝑐1 0 is the empty Curve object c0 = Curve() with c0._dim = 1 and c0.wrapped = None

Sets of predefined basic shapes:

𝐵3 := { Part, Box, Cylinder, Cone, Sphere, Torus, Wedge, Hole, CounterBoreHole, CounterSinkHole }

𝐵2 := { Sketch, Rectangle, Circle, Ellipse, Rectangle, Polygon, RegularPolygon, Text, Trapezoid,
SlotArc, SlotCenterPoint, SlotCenterToCenter, SlotOverall }

𝐵1   :=   { Curve, Bezier, FilletPolyline, PolarLine, Polyline, Spline, Helix, CenterArc,
EllipticalCenterArc,  ParabolicCenterArc,  HyperbolicCenterArc,   RadiusArc,  SagittaArc,
TangentArc, ThreePointArc, JernArc }

with 𝐵3 ⊂𝐶3, 𝐵2 ⊂𝐶2 and 𝐵1 ⊂𝐶1

Operations:

+ : 𝐶𝑛× 𝐶𝑛→𝐶𝑛with (𝑎, 𝑏) ↦→𝑎+ 𝑏, for 𝑛= 1, 2, 3

𝑎+ 𝑏:= a.fuse(b) for each operation

−: 𝐶𝑛→𝐶𝑛with 𝑎↦→−𝑎, for 𝑛= 1, 2, 3

𝑏+ (−𝑎) := b.cut(a) for each operation (implicit definition)

& : 𝐶𝑛× 𝐶𝑛→𝐶𝑛with (𝑎, 𝑏) ↦→𝑎& 𝑏, for 𝑛= 2, 3

𝑎& 𝑏:= a.intersect(b) for each operation

• & is not defined for 𝑛= 1 in build123d

• The following relationship holds: 𝑎& 𝑏= (𝑎+ 𝑏) + −(𝑎+ (−𝑏)) + −(𝑏+ (−𝑎))

Abelian groups

(𝐶𝑛, 𝑐𝑛 0, +, −) are abelian groups for 𝑛= 1, 2, 3.

• The implementation a - b = a.cut(b) needs to be read as 𝑎+ (−𝑏) since the group does not have a binary
- operation. As such, 𝑎−(𝑏−𝑐) = 𝑎+ −(𝑏+ −𝑐)) ̸= 𝑎−𝑏+ 𝑐

• This definition also includes that neither - nor & are commutative.

Locations, planes and location arithmetic

Set definitions:

𝐿:= { Location((x, y, z), (a, b, c)) : 𝑥, 𝑦, 𝑧∈𝑅∧𝑎, 𝑏, 𝑐∈𝑅}

with 𝑎, 𝑏, 𝑐being angles in degrees.

𝑃:= { Plane(o, x, z) : 𝑜, 𝑥, 𝑧𝑅3 ∧‖𝑥‖ = ‖𝑧‖ = 1}

<!-- PDF page 371 -->

with o being the origin and x, z the x- and z-direction of the plane.

Neutral element: 𝑙0 ∈𝐿: Location()

Operations:

* : 𝐿× 𝐿→𝐿with (𝑙1, 𝑙2) ↦→𝑙1 * 𝑙2

𝑙1 * 𝑙2 := l1 * l2 (multiply two locations)

* : 𝑃× 𝐿→𝑃with (𝑝, 𝑙) ↦→𝑝* 𝑙

𝑝* 𝑙:= Plane(p.location * l) (move plane 𝑝∈𝑃to location 𝑙∈𝐿)

Inverse element: 𝑙−1 ∈𝐿: l.inverse()

Placing objects onto planes

* : 𝑃× 𝐶𝑛→𝐶𝑛with (𝑝, 𝑐) ↦→𝑝* 𝑐, for 𝑛= 1, 2, 3

Locate an object 𝑐∈𝐶𝑛onto plane 𝑝∈𝑃, i.e. c.moved(p.location)

Placing objects at locations

* : 𝐿× 𝐶𝑛→𝐶𝑛with (𝑙, 𝑐) ↦→𝑙* 𝑐, for 𝑛= 1, 2, 3

Locate an object 𝑐∈𝐶𝑛at location 𝑙∈𝐿, i.e. c.moved(l)
