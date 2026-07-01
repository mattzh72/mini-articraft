---
title: "CAD Object Centers"
source_html: "https://build123d.readthedocs.io/en/latest/center.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "371"
generated_on: "2026-07-01"
---

# CAD Object Centers

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 371 -->

1.18.4 CAD Object Centers

Finding the center of a CAD object is a surprisingly complex operation. To illustrate let’s consider two examples: a
simple isosceles triangle and a curved line (their bounding boxes are shown with dashed lines):

One can see that there is are significant differences between the different types of centers. To allow the designer to
choose the center that makes the most sense for the given shape there are three possible values for the CenterOf
Enum:

CenterOf                Symbol   1D   2D  3D   Compound

CenterOf.BOUNDING_BOX            ✓    ✓   ✓    ✓
CenterOf.GEOMETRY                ✓    ✓
CenterOf.MASS                    ✓    ✓   ✓    ✓
