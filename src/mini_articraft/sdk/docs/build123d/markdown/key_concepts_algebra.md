---
title: "Key Concepts (algebra mode)"
source_html: "https://build123d.readthedocs.io/en/latest/key_concepts_algebra.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "26-27"
generated_on: "2026-07-01"
---

# Key Concepts (algebra mode)

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 26 -->

1.5 Key Concepts (algebra mode)

Build123d’s algebra mode works on objects of the classes Shape, Part, Sketch and Curve and is based on two
concepts:

1. Object arithmetic

2. Placement arithmetic

1.5.1 Object arithmetic

• Creating a box and a cylinder centered at (0, 0, 0)

```python
     b = Box(1, 2, 3)
     c = Cylinder(0.2, 5)
```

• Fusing a box and a cylinder

```python
     r = Box(1, 2, 3) + Cylinder(0.2, 5)
```

• Cutting a cylinder from a box

```python
     r = Box(1, 2, 3) - Cylinder(0.2, 5)
```

• Intersecting a box and a cylinder

```python
     r = Box(1, 2, 3) & Cylinder(0.2, 5)
```

Notes:

• b, c and r are instances of class Compound and can be viewed with every viewer that can show build123d.
Compound objects.

• A discussion around performance can be found in Performance considerations in algebra mode.

• A mathematically formal definition of the algebra can be found in Algebraic definition.

1.5.2 Placement arithmetic

A Part, Sketch or Curve does not have any location or rotation parameter. The rationale is that an object defines its
topology (shape, sizes and its center), but does not know where in space it will be located. Instead, it will be relocated
with the * operator onto a plane and to location relative to the plane (similar moved).

The generic forms of object placement are:

1. Placement on plane or at location relative to XY plane:

```python
         plane * alg_compound
         location * alg_compound
```

2. Placement on the plane and then moved relative to the plane by location (the location is relative to the local
coordinate system of the plane).

```python
     plane * location * alg_compound
```

Details can be found in Location arithmetic for algebra mode.

Examples:

• Box on the XY plane, centered at (0, 0, 0) (both forms are equivalent):

<!-- PDF page 27 -->

```python
     Plane.XY * Box(1, 2, 3)
```

```python
     Box(1, 2, 3)
```

Note: On the XY plane no placement is needed (mathematically Plane.XY * will not change the location of an
object).

• Box on the XY plane centered at (0, 1, 0) (all three are equivalent):

```python
     Plane.XY * Pos(0, 1, 0) * Box(1, 2, 3)
```

```python
     Pos(0, 1, 0) * Box(1, 2, 3)
```

```python
     Pos(Y=1) * Box(1, 2, 3)
```

Note: Again, Plane.XY can be omitted.

• Box on plane Plane.XZ:

```python
     Plane.XZ * Box(1, 2, 3)
```

• Box on plane Plane.XZ with a location (X=1, Y=2, Z=3) relative to the XZ plane, i.e., using the x-, y- and
z-axis of the XZ plane:

```python
     Plane.XZ * Pos(1, 2, 3) * Box(1, 2, 3)
```

• Box on plane Plane.XZ moved to (X=1, Y=2, Z=3) relative to this plane and rotated there by the angles (X=0,
Y=100, Z=45) around Plane.XZ axes:

```python
     Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3)
```

```python
     Location((1, 2, 3), (0, 100, 45)) * Box(1, 2, 3)
```

Note: Pos * Rot is the same as using Location directly

• Box on plane Plane.XZ rotated on this plane by the angles (X=0, Y=100, Z=45) (using the x-, y- and z-axis
of the XZ plane) and then moved to (X=1, Y=2, Z=3) relative to the XZ plane:

```python
     Plane.XZ * Rot(0, 100, 45) * Pos(0,1,2) * Box(1, 2, 3)
```

1.5.3 Combing both concepts

Object arithmetic and Placement at locations can be combined:

```python
     b = Plane.XZ * Rot(X=30) * Box(1, 2, 3) + Plane.YZ * Pos(X=-1) * Cylinder(0.2,␣
```

˓→5)

Note: In Python * binds stronger then +, -, &, hence brackets are not needed.
