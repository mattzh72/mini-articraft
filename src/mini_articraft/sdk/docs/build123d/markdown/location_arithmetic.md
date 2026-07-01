---
title: "Location arithmetic for algebra mode"
source_html: "https://build123d.readthedocs.io/en/latest/location_arithmetic.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "365-370"
generated_on: "2026-07-01"
---

# Location arithmetic for algebra mode

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 365 -->

1.18.2 Location arithmetic for algebra mode

Position a shape relative to the XY plane

For the following use the helper function:

```python
def location_symbol(location: Location, scale: float = 1) -> Compound:
```

```python
    return Compound.make_triad(axes_scale=scale).locate(location)
```

```python
def plane_symbol(plane: Plane, scale: float = 1) -> Compound:
    triad = Compound.make_triad(axes_scale=scale)
    circle = Circle(scale * .8).edge()
    return (triad + circle).locate(plane.location)
```

1. Positioning at a location

```python
         loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
```

```python
         face = loc * Rectangle(1, 2)
```

```python
         show_object(face, name="face")
         show_object(location_symbol(loc), name="location")
```

![Extracted image from PDF page 365](../images/location_arithmetic/p365_img001_3e2e7d6726ce.png)

2) Positioning on a plane

<!-- PDF page 366 -->

```python
         plane = Plane.XZ
```

```python
         face = plane * Rectangle(1, 2)
```

```python
         show_object(face, name="face")
         show_object(plane_symbol(plane), name="plane")
```

![Extracted image from PDF page 366](../images/location_arithmetic/p366_img002_a0f792530c7a.png)

Note: The x-axis and the y-axis of the plane are on the x-axis and the z-axis of the world coordinate system (red and
blue axis).

Relative positioning to a plane

1. Position an object on a plane relative to the plane

```python
         loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
```

```python
         face = loc * Rectangle(1,2)
```

```python
         box = Plane(loc) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
         # box = Plane(face.location) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
         # box = loc * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
```

```python
         show_object(face, name="face")
         show_object(location_symbol(loc), name="location")
         show_object(box, name="box")
```

<!-- PDF page 367 -->

![Extracted image from PDF page 367](../images/location_arithmetic/p367_img003_b85a077345ab.png)

The X, Y, Z components of Pos(0.2, 0.4, 0.1) are relative to the x-axis, y-axis or z-axis of the underlying location
loc.

Note: Plane(loc) *, Plane(face.location) * and loc * are equivalent in this example.

2. Rotate an object on a plane relative to the plane

```python
         loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
```

```python
         face = loc * Rectangle(1,2)
```

```python
         box = Plane(loc) * Rot(Z=80) * Box(0.2, 0.2, 0.2)
```

```python
         show_object(face, name="face")
         show_object(location_symbol(loc), name="location")
         show_object(box, name="box")
```

![Extracted image from PDF page 367](../images/location_arithmetic/p367_img004_206821142f97.png)

The box is rotated via Rot(Z=80) around the z-axis of the underlying location (and not of the z-axis of the world).

More general:

```python
     loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
```

<!-- PDF page 368 -->

```python
                                                                 (continued from previous page)
     face = loc * Rectangle(1,2)
```

```python
     box = loc * Rot(20, 40, 80) * Box(0.2, 0.2, 0.2)
```

```python
     show_object(face, name="face")
     show_object(location_symbol(loc), name="location")
     show_object(box, name="box")
```

![Extracted image from PDF page 368](../images/location_arithmetic/p368_img005_17904e274c19.png)

The box is rotated via Rot(20, 40, 80) around all three axes relative to the plane.

3. Rotate and position an object relative to a location

```python
         loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
```

```python
         face = loc * Rectangle(1,2)
```

```python
         box = loc * Rot(20, 40, 80) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
```

```python
         show_object(face, name="face")
         show_object(location_symbol(loc), name="location")
         show_object(box, name="box")
         show_object(location_symbol(loc * Rot(20, 40, 80), 0.5), options=
```

```python
         ˓→{"color":(0, 255, 255)}, name="local_location")
```

<!-- PDF page 369 -->

![Extracted image from PDF page 369](../images/location_arithmetic/p369_img006_0832c371a197.png)

The box is positioned via Pos(0.2, 0.4, 0.1) relative to the location loc * Rot(20, 40, 80)

4. Position and rotate an object relative to a location

```python
         loc = Location((0.1, 0.2, 0.3), (10, 20, 30))
```

```python
         face = loc * Rectangle(1,2)
```

```python
         box = loc * Pos(0.2, 0.4, 0.1) * Rot(20, 40, 80) * Box(0.2, 0.2, 0.2)
```

```python
         show_object(face, name="face")
         show_object(location_symbol(loc), name="location")
         show_object(box, name="box")
         show_object(location_symbol(loc * Pos(0.2, 0.4, 0.1), 0.5), options=
```

```python
         ˓→{"color":(0, 255, 255)}, name="local_location")
```

![Extracted image from PDF page 369](../images/location_arithmetic/p369_img007_19811e8e3a47.png)

```python
Note: This is the same as box = loc * Location((0.2, 0.4, 0.1), (20, 40, 80)) * Box(0.2, 0.2, 0.
2)
```
