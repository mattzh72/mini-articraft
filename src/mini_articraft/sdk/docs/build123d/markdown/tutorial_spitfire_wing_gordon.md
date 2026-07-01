---
title: "Tutorial: Spitfire Wing with Gordon Surface"
source_html: "https://build123d.readthedocs.io/en/latest/tutorial_spitfire_wing_gordon.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "230-234"
generated_on: "2026-07-01"
---

# Tutorial: Spitfire Wing with Gordon Surface

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 230 -->

Tutorial: Spitfire Wing with Gordon Surface

In this advanced tutorial we construct a Supermarine Spitfire wing as a make_gordon_surface()—a powerful tech-
nique for surfacing from intersecting profiles and guides. A Gordon surface blends a grid of curves into a smooth,
coherent surface as long as the profiles and guides intersect consistently.

Note

Gordon surfaces work best when each profile intersects each guide exactly once, producing a well-formed curve
network.

Overview

We will:

1. Define overall wing dimensions and elliptic leading/trailing edge guide curves

2. Sample the guides to size the root and tip airfoils (different NACA profiles)

3. Build the Gordon surface from the airfoil profiles and wing-edge guides

4. Close the root with a planar face and build the final Solid

Step 1 — Dimensions and guide curves

We model a single wing (half-span), with an elliptic leading and trailing edge. These two edges act as the guides for
the Gordon surface.

```python
from build123d import *
from ocp_vscode import show
```

```python
wing_span = 36 * FT + 10 * IN
wing_leading = 2.5 * FT
wing_trailing = wing_span / 4 - wing_leading
wing_leading_fraction = wing_leading / (wing_leading + wing_trailing)
wing_tip_section = wing_span / 2 - 1 * IN  # distance from root to last section
```

```python
# Create leading and trailing edges
leading_edge = EllipticalCenterArc(
```

<!-- PDF page 231 -->

```python
                                                                      (continued from previous page)
    (0, 0), wing_span / 2, wing_leading, start_angle=270, end_angle=360
)
trailing_edge = EllipticalCenterArc(
    (0, 0), wing_span / 2, wing_trailing, start_angle=0, end_angle=90
)
```

Step 2 — Root and tip airfoil sizing

We intersect the guides with planes normal to the span to size the airfoil sections. The resulting chord lengths define
uniform scales for each airfoil curve.

```python
# Calculate the airfoil sizes from the leading/trailing edges
airfoil_sizes = []
for i in [0, 1]:
    tip_axis = Axis(i * (wing_tip_section, 0, 0), (0, 1, 0))
    leading_pnt = leading_edge.intersect(tip_axis)[0]
    trailing_pnt = trailing_edge.intersect(tip_axis)[0]
    airfoil_sizes.append(trailing_pnt.Y - leading_pnt.Y)
```

Step 3 — Build airfoil profiles (root and tip)

We place two different NACA airfoils on Plane.YZ—with the airfoil origins shifted so the leading edge fraction is
aligned—then scale to the chord lengths from Step 2.

```python
# Create the root and tip airfoils - note that they are different NACA profiles
airfoil_root = Plane.YZ * scale(
```

```python
    Airfoil("2213").translate((-wing_leading_fraction, 0, 0)), airfoil_sizes[0]
)
airfoil_tip = (
```

```python
    Plane.YZ
    * Pos(Z=wing_tip_section)
    * scale(Airfoil("2205").translate((-wing_leading_fraction, 0, 0)), airfoil_sizes[1])
)
```

Step 4 — Gordon surface construction

A Gordon surface needs profiles and guides. Here the airfoil edges are the profiles; the elliptic edges are the guides.
We also add the wing tip section so the profile grid closes at the tip.

```python
# Create the Gordon surface profiles and guides
profiles = airfoil_root.edges() + airfoil_tip.edges()
profiles.append(leading_edge @ 1)  # wing tip
guides = [leading_edge, trailing_edge]
# Create the wing surface as a Gordon Surface
wing_surface = -Face.make_gordon_surface(profiles, guides)
# Create the root of the wing
wing_root = -Face(Wire(wing_surface.edges().filter_by(Edge.is_closed)))
```

<!-- PDF page 232 -->

Step 5 — Cap the root and create the solid

We extract the closed root edge loop, make a planar cap, and form a solid shell.

```python
# Create the wing Solid
wing = Solid(Shell([wing_surface, wing_root]))
wing.color = 0x99A3B9  # Azure Blue
```

```python
show(wing)
```

![Extracted image from PDF page 232](../images/tutorial_spitfire_wing_gordon/p232_img001_9f217becdba6.png)

Tips for robust Gordon surfaces

• Ensure each profile intersects each guide once and only once

• Keep the curve network coherent (no duplicated or missing intersections)

• When possible, reuse the same Edge objects across adjacent faces

Complete listing

For convenience, here is the full script in one block:

```python
from build123d import *
from ocp_vscode import show
```

```python
wing_span = 36 * FT + 10 * IN
```

<!-- PDF page 233 -->

```python
                                                                      (continued from previous page)
wing_leading = 2.5 * FT
wing_trailing = wing_span / 4 - wing_leading
wing_leading_fraction = wing_leading / (wing_leading + wing_trailing)
wing_tip_section = wing_span / 2 - 1 * IN  # distance from root to last section
```

```python
# Create leading and trailing edges
leading_edge = EllipticalCenterArc(
    (0, 0), wing_span / 2, wing_leading, start_angle=270, end_angle=360
)
trailing_edge = EllipticalCenterArc(
    (0, 0), wing_span / 2, wing_trailing, start_angle=0, end_angle=90
)
```

```python
# [AirfoilSizes]
# Calculate the airfoil sizes from the leading/trailing edges
airfoil_sizes = []
for i in [0, 1]:
    tip_axis = Axis(i * (wing_tip_section, 0, 0), (0, 1, 0))
    leading_pnt = leading_edge.intersect(tip_axis)[0]
    trailing_pnt = trailing_edge.intersect(tip_axis)[0]
    airfoil_sizes.append(trailing_pnt.Y - leading_pnt.Y)
```

```python
# [Airfoils]
# Create the root and tip airfoils - note that they are different NACA profiles
airfoil_root = Plane.YZ * scale(
```

```python
    Airfoil("2213").translate((-wing_leading_fraction, 0, 0)), airfoil_sizes[0]
)
airfoil_tip = (
```

```python
    Plane.YZ
    * Pos(Z=wing_tip_section)
    * scale(Airfoil("2205").translate((-wing_leading_fraction, 0, 0)), airfoil_sizes[1])
)
```

```python
# [Profiles]
# Create the Gordon surface profiles and guides
profiles = airfoil_root.edges() + airfoil_tip.edges()
profiles.append(leading_edge @ 1)  # wing tip
guides = [leading_edge, trailing_edge]
# Create the wing surface as a Gordon Surface
wing_surface = -Face.make_gordon_surface(profiles, guides)
# Create the root of the wing
wing_root = -Face(Wire(wing_surface.edges().filter_by(Edge.is_closed)))
```

```python
# [Solid]
# Create the wing Solid
wing = Solid(Shell([wing_surface, wing_root]))
wing.color = 0x99A3B9  # Azure Blue
```

```python
show(wing)
```
