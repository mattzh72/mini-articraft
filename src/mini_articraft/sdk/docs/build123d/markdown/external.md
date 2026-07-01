---
title: "External Tools and Libraries"
source_html: "https://build123d.readthedocs.io/en/latest/external.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "378-381"
generated_on: "2026-07-01"
---

# External Tools and Libraries

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 378 -->

1.20 External Tools and Libraries

The following sections describe tools and libraries external to build123d that extend its functionality.

1.20.1 Editors & Viewers

ocp-vscode

A viewer for OCP based Code-CAD (CadQuery, build123d) integrated into VS Code.

See: ocp-vscode (formerly known as cq_vscode)

Watch Jern create three build123d designs in realtime with Visual Studio Code and the ocp-vscode viewer extension
in a timed event from the TooTallToby 2024 Spring Open Tournament: build123d entry video

cq-editor fork

GUI editor based on PyQT. This fork has changes from jdegenstein to allow easier use with build123d.

See: jdegenstein’s fork of cq-editor

<!-- PDF page 379 -->

Yet Another CAD Viewer

A web-based CAD viewer for OCP models (CadQuery/build123d) that runs in any modern browser and supports static
site deployment. Features include interactive inspection of faces, edges, and vertices, measurement tools, per-model
clipping planes, transparency control, and hot reloading via yacv-server. It also has a build123d playground for
editing and sharing models directly in the browser (demo).

See: Yet Another CAD Viewer

PartCAD VS Code extension

A wrapper around ocp-vscode (see above) which requires build123d scripts to be packaged using PartCAD (see
below). While it requires the overhead of maintaining the package, it provides some convenience features (such as UI
controls to export models) as well as functional features (such as UI controls to pass parameters into build123d scripts
and AI-based generative design tools).

It’s also the most convenient tool to create new packages and parts. More PDM and PLM features are expected to arrive
soon.

1.20.2 Part Libraries

bd_warehouse

On-demand generation of parametric parts that seamlessly integrate into build123d projects.

Parts available include:

• fastener - Nuts, Screws, Washers and custom holes

• flange - Standardized parametric flanges

• pipe - Standardized parametric pipes

• thread - Parametric helical threads (Iso, Acme, Plastic, etc.)

See: bd_warehouse

bd_beams_and_bars

2D sections and 3D beams generation (UPN, IPN, UPE, flat bars, ...)

See: bd_beams_and_bars

Superellipses & Superellipsoids

Superellipses are a more sophisticated alternative to rounded rectangles, with smoothly changing curvature. They are
flexible shapes that can be adjusted by changing the “exponent” to get a result that varies between rectangular and
elliptical, or from square, through squircle, to circle, and beyond...

Superellipses can be found:

• in typefaces such as Melior, Eurostyle, and Computer Modern

• as the shape of airliner windows, tables, plates

• clipping the outline of iOS app icons

They were named and popularized in the 1950s-1960s by the Danish mathematician and poet Piet Hein, who used them
in the winning design for the Sergels Torg roundabout in Stockholm.

See: Superellipses & Superellipsoids

<!-- PDF page 380 -->

Public PartCAD repository

See partcad.org for all the models packaged and published using PartCAD (see below). This repository contains in-
dividual parts, as well as large assemblies created using those parts. See the OpenVMP robot as an example of an
assembly

py_gearworks generator

A gear generation framework that allows easy creation of a wide range of gears and drives.

See py_gearworks

bd_vslot

A library of V-Slot linear rail components, including V-Slot rails.

See: bd_vslot

1.20.3 Tools

blendquery

CadQuery and build123d integration for Blender.

See: blendquery

nething

3D generative AI for CAD modeling. Now everyone is an engineer. Make your ideas real.

See: nething

Listen to the following podcast which discusses nething in detail: The Next Byte Podcast

ocp-freecad-cam

CAM for CadQuery and Build123d by leveraging FreeCAD library. Visualizes in CQ-Editor and ocp-cad-viewer.
Spiritual successor of cq-cam

See: ocp-freecad-cam

PartCAD

A package manager for CAD models. Build123d is the most supported Code-CAD framework, but CadQuery and
OpenSCAD are also supported. It can be used by build123d designs to import parts from PartCAD repositories, and
to publish build123d designs to be consumed by others.

MakerRepo library (mr)

The makerrepo Python package (imported as mr) is a lightweight library that provides decorators such as @artifact,
@customizable, and @cached to annotate functions that build your models. The decorators have no effect on your
existing build123d code until it is discovered and run by tools such as the makerrepo-cli or MakerRepo.com CI. The
goal is to enable a code-driven workflow locally (e.g. command-line tools) or in CI. The library does not assume how
it will be consumed, so annotated functions can be used with other tools and frameworks as well.

See MakerRepo Library Docs for more information and LaunchPlatform/makerrepo for source code.

<!-- PDF page 381 -->

makerrepo-cli

Command-line tool (available as makerrepo-cli or mr) to build artifacts, run generators, snapshot artifacts, and
manage cache locally. It scans the current directory for Python packages and modules that use the MakerRepo library
decorators.

See MakerRepo CLI for documentation and LaunchPlatform/makerrepo-cli for source code.

dl4to4ocp

Library that helps perform topology optimization on your OCP-based CAD models (CadQuery/Build123d/...) using
the dl4to library.

See: dl4to4ocp

OCP.wasm

This project ports the low-level dependencies required for build123d to run in a browser. For a fully featured frontend,
check out Yet Another CAD Viewer (see above).

See: OCP.wasm

partomatic

Partomatic provides a standardized system for building parametric models in build123d. The open nature of build123d
is its strength, but it makes it difficult to build standardized tooling to interface with your projects. It makes it easy to:

• import and export configuration files

• easily export models for projects that provide large numbers of intersectional options

• share the built-in web interface allowing end-users to change properties and see the results quickly

• generate logs for compilation and web interface events that can be consumed by an OpenTelemetry platform

See: Partomatic
