---
title: "Performance considerations in algebra mode"
source_html: "https://build123d.readthedocs.io/en/latest/algebra_performance.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "364-365"
generated_on: "2026-07-01"
---

# Performance considerations in algebra mode

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 364 -->

1.18.1 Performance considerations in algebra mode

Creating lots of Shapes in a loop means for every step fuse and clean will be called. In an example like the below,
both functions get slower and slower the more objects are already fused. Overall it takes on an M1 Mac 4.76 sec.

```python
diam = 80
holes = Sketch()
r = Rectangle(2, 2)
for loc in GridLocations(4, 4, 20, 20):
```

```python
    if loc.position.X**2 + loc.position.Y**2 < (diam / 2 - 1.8) ** 2:
        holes += loc * r
```

```python
c = Circle(diam / 2) - holes
```

One way to avoid it is to use lazy evaluation for the algebra operations. Just collect all objects and then call fuse (+)
once with all objects and clean once. Overall it takes 0.19 sec.

```python
r = Rectangle(2, 2)
holes = [
    loc * r
    for loc in GridLocations(4, 4, 20, 20).locations
    if loc.position.X**2 + loc.position.Y**2 < (diam / 2 - 1.8) ** 2
```

<!-- PDF page 365 -->

]

```python
c = Circle(diam / 2) - holes
```

Another way to leverage the vectorized algebra operations is to add a list comprehension of objects to an empty Part,
Sketch or Curve:

```python
polygons = Sketch() + [
    loc * RegularPolygon(radius=5, side_count=5)
    for loc in GridLocations(40, 30, 2, 2)
]
```

This again ensures one single fuse and clean call.
