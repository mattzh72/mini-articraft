---
title: "Surface Modeling"
source_html: "https://build123d.readthedocs.io/en/latest/tutorial_surface_modeling.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "224-225"
generated_on: "2026-07-01"
---

# Surface Modeling

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 224 -->

1.9.9 Surface Modeling

Surface modeling refers to the direct creation and manipulation of the skin of a 3D object—its bounding faces—rather
than starting from volumetric primitives or solid operations.

Instead of defining a shape by extruding or revolving a 2D profile to fill a volume, surface modeling focuses on building
the individual curved or planar faces that together define the outer boundary of a part. This approach allows for precise
control of complex freeform geometry such as aerodynamic surfaces, boat hulls, or organic transitions that cannot
easily be expressed with simple parametric solids.

In build123d, as in other CAD kernels based on BREP (Boundary Representation) modeling, all solids are ultimately
defined by their boundaries: a hierarchy of faces, edges, and vertices. Each face represents a finite patch of a geometric

<!-- PDF page 225 -->

surface (plane, cylinder, Bézier patch, etc.) bounded by one or more edge loops or wires. When adjacent faces share
edges consistently and close into a continuous boundary, they form a manifold Shell—the watertight surface of a
volume. If this shell is properly oriented and encloses a finite region of space, the model becomes a solid.

Surface modeling therefore operates at the most fundamental level of BREP construction. Rather than relying on higher-
level modeling operations to implicitly generate faces, it allows you to construct and connect those faces explicitly.
This provides a path to build geometry that blends analytical and freeform shapes seamlessly, with full control over
continuity, tangency, and curvature across boundaries.

This section provides: - A concise overview of surface-building tools in build123d - Hands-on tutorials, from funda-
mentals to advanced techniques like Gordon surfaces

Available surface methods

Methods on Face for creating non-planar surfaces:

• make_bezier_surface()

• make_gordon_surface()

• make_surface()

• make_surface_from_array_of_points()

• make_surface_from_curves()

• make_surface_patch()

Note

Surface modeling is an advanced technique. Robust results usually come from reusing the same Edge objects across
adjacent faces and ensuring the final Shell is water-tight or manifold (no gaps).
