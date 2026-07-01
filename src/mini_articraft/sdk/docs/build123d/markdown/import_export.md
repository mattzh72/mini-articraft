---
title: "Import/Export"
source_html: "https://build123d.readthedocs.io/en/latest/import_export.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "351-364"
generated_on: "2026-07-01"
---

# Import/Export

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 351 -->

1.17 Import/Export

Methods and functions specific to exporting and importing build123d objects are defined below.

For example:

```python
with BuildPart() as box_builder:
```

```python
    Box(1, 1, 1)
export_step(box_builder.part, "box.step")
```

1.17.1 File Formats

3MF

The 3MF (3D Manufacturing Format) file format is a versatile and modern standard for representing 3D models used in
additive manufacturing, 3D printing, and other applications. Developed by the 3MF Consortium, it aims to overcome
the limitations of traditional 3D file formats by providing a more efficient and feature-rich solution. The 3MF format
supports various advanced features like color information, texture mapping, multi-material definitions, and precise
geometry representation, enabling seamless communication between design software, 3D printers, and other manufac-
turing devices. Its open and extensible nature makes it an ideal choice for exchanging complex 3D data in a compact
and interoperable manner.

BREP

The BREP (Boundary Representation) file format is a widely used data format in computer-aided design (CAD) and
computer-aided engineering (CAE) applications. BREP represents 3D geometry using topological entities like vertices,
edges, and faces, along with their connectivity information. It provides a precise and comprehensive representation of
complex 3D models, making it suitable for advanced modeling and analysis tasks. BREP files are widely supported
by various CAD software, enabling seamless data exchange between different systems. Its ability to represent both
geometric shapes and their topological relationships makes it a fundamental format for storing and sharing detailed 3D
models.

DXF

The DXF (Drawing Exchange Format) file format is a widely used standard for representing 2D and 3D drawings,
primarily used in computer-aided design (CAD) applications. Developed by Autodesk, DXF files store graphical and
geometric data, such as lines, arcs, circles, and text, as well as information about layers, colors, and line weights. Due to
its popularity, DXF files can be easily exchanged and shared between different CAD software. The format’s simplicity
and human-readable structure make it a versatile choice for sharing designs, drawings, and models across various CAD
platforms, facilitating seamless collaboration in engineering and architectural projects.

<!-- PDF page 352 -->

glTF

The glTF (GL Transmission Format) is a royalty-free specification for the efficient transmission and loading of 3D
models and scenes by applications. Developed by the Khronos Group, glTF is designed as a compact, interoperable
format that enables the quick display of assets across various platforms and devices. glTF supports a rich feature set,
including detailed meshes, materials, textures, skeletal animations, and more, facilitating complex 3D visualizations. It
streamlines the process of sharing and deploying 3D content in web applications, game engines, and other visualization
tools, making it the “JPEG of 3D.” glTF’s versatility and efficiency have led to its widespread adoption in the 3D content
industry.

STL

The STL (STereoLithography) file format is a widely used file format in 3D printing and computer-aided design (CAD)
applications. It represents 3D geometry using triangular facets to approximate the surface of a 3D model. STL files
are widely supported and can store both the geometry and color information of the model. They are used for rapid
prototyping and 3D printing, as they provide a simple and efficient way to represent complex 3D objects. The format’s
popularity stems from its ease of use, platform independence, and ability to accurately describe the surface of intricate
3D models with a minimal file size.

STEP

The STEP (Standard for the Exchange of Product model data) file format is a widely used standard for representing 3D
product and manufacturing data in computer-aided design (CAD) and computer-aided engineering (CAE) applications.
It is an ISO standard (ISO 10303) and supports the representation of complex 3D geometry, product structure, and
metadata. STEP files store information in a neutral and standardized format, making them highly interoperable across
different CAD/CAM software systems. They enable seamless data exchange between various engineering disciplines,
facilitating collaboration and data integration throughout the entire product development and manufacturing process.

SVG

The SVG (Scalable Vector Graphics) file format is an XML-based standard used for describing 2D vector graphics.
It is widely supported and can be displayed in modern web browsers, making it suitable for web-based graphics and
interactive applications. SVG files define shapes, paths, text, and images using mathematical equations, allowing for
smooth scalability without loss of quality. The format is ideal for logos, icons, illustrations, and other graphics that
require resolution independence. SVG files are also easily editable in text editors or vector graphic software, making
them a popular choice for designers and developers seeking flexible and versatile graphic representation.

1.17.2 2D Exporters

Exports to DXF (Drawing Exchange Format) and SVG (Scalable Vector Graphics) are provided by the 2D Exporters:
ExportDXF and ExportSVG classes.

DXF is a widely used file format for exchanging CAD (Computer-Aided Design) data between different software ap-
plications. SVG is a widely used vector graphics format that is supported by web browsers and various graphic editors.

The core concept to these classes is the creation of a DXF/SVG document with specific properties followed by the
addition of layers and shapes to the documents. Once all of the layers and shapes have been added, the document can
be written to a file.

3D to 2D Projection

There are a couple ways to generate a 2D drawing of a 3D part:

• Generate a section: The section() operation can be used to create a 2D cross section of a 3D part at a given
plane.

• Generate a projection: The project_to_viewport() method can be used to create a 2D projection of a 3D
scene. Similar to a camera, the viewport_origin defines the location of camera, the viewport_up defines

<!-- PDF page 353 -->

the orientation of the camera, and the look_at parameter defined where the camera is pointed. By default,
viewport_up is the positive z axis and look_up is the center of the shape. The return value is a tuple of lists
of edges, the first the visible edges and the second the hidden edges.

Each of these Edges and Faces can be assigned different line color/types and fill colors as described below (as
project_to_viewport only generates Edges, fill doesn’t apply). The shapes generated from the above steps are
to be added as shapes in one of the exporters described below and written as either a DXF or SVG file as shown in this
example:

```python
view_port_origin=(-100, -50, 30)
visible, hidden = part.project_to_viewport(view_port_origin)
max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)
exporter = ExportSVG(scale=100 / max_dimension)
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
exporter.add_shape(visible, layer="Visible")
exporter.add_shape(hidden, layer="Hidden")
exporter.write("part_projection.svg")
```

LineType

ANSI (American National Standards Institute) and ISO (International Organization for Standardization) standards both
define line types in drawings used in DXF and SVG exported drawings:

• ANSI Standards:

– ANSI/ASME Y14.2 - “Line Conventions and Lettering” is the standard that defines line types, line
weights, and line usage in engineering drawings in the United States.

• ISO Standards:

– ISO 128 - “Technical drawings – General principles of presentation” is the ISO standard that covers
the general principles of technical drawing presentation, including line types and line conventions.

– ISO 13567 - “Technical product documentation (TPD) – Organization and naming of layers for CAD”
provides guidelines for the organization and naming of layers in Computer-Aided Design (CAD) sys-
tems, which may include line type information.

These standards help ensure consistency and clarity in technical drawings, making it easier for engineers, designers,
and manufacturers to communicate and interpret the information presented in the drawings.

The line types used by the 2D Exporters are defined by the LineType Enum and are shown in the following diagram:

ExportDXF

class ExportDXF(version: str = 'AC1027', unit: ~build123d.build_enums.Unit = <Unit.MM>, color:
~exporters.ColorIndex | None = None, line_weight: float | None = None, line_type:
~exporters.LineType | None = None)

The ExportDXF class provides functionality for exporting 2D shapes to DXF (Drawing Exchange Format) format.
DXF is a widely used file format for exchanging CAD (Computer-Aided Design) data between different software
applications.

Parameters

• version (str, optional) – The DXF version to use for the output file. Defaults to
ezdxf.DXF2013.

<!-- PDF page 354 -->

• unit (Unit, optional) – The unit used for the exported DXF. It should be one of the Unit
enums: Unit.MC, Unit.MM, Unit.CM, Unit.M, Unit.IN, or Unit.FT. Defaults to Unit.MM.

• color (Optional[ColorIndex], optional) – The default color index for shapes. It can
be specified as a ColorIndex enum or None.. Defaults to None.

• line_weight (Optional[float], optional) – The default line weight (stroke width)
for shapes, in millimeters. . Defaults to None.

• line_type (Optional[LineType], optional) – e default line type for shapes. It should
be a LineType enum or None.. Defaults to None.

Example

```python
     exporter = ExportDXF(unit=Unit.MM, line_weight=0.5)
     exporter.add_layer("Layer 1", color=ColorIndex.RED, line_type=LineType.DASHED)
     exporter.add_shape(shape_object, layer="Layer 1")
     exporter.write("output.dxf")
```

Raises

ValueError – unit not supported

```python
     METRIC_UNITS = {<Unit.CM>, <Unit.M>, <Unit.MM>}
```

add_layer(name: str, *, color: ColorIndex | None = None, line_weight: float | None = None, line_type:
LineType | None = None) →Self

Adds a new layer to the DXF export with the given properties.

Parameters

• name (str) – The name of the layer definition. Must be unique among all layers.

• color (Optional[ColorIndex], optional) – The color index for shapes on this layer.
It can be specified as a ColorIndex enum or None. Defaults to None.

• line_weight (Optional[float], optional) – The line weight (stroke width) for
shapes on this layer, in millimeters. Defaults to None.

• line_type (Optional[LineType], optional) – The line type for shapes on this layer.
It should be a LineType enum or None. Defaults to None.

Returns

DXF document with additional layer

Return type

Self

add_shape(shape: Shape | Iterable[Shape], layer: str = '') →Self

Adds a shape to the specified layer.

Parameters

• shape (Shape | Iterable[Shape]) – The shape or collection of shapes to be added. It
can be a single Shape object or an iterable of Shape objects.

• layer (str, optional) – The name of the layer where the shape will be added. If not
specified, the default layer will be used. Defaults to “”.

Returns

Document with additional shape

<!-- PDF page 355 -->

Return type

Self

write(file_name: PathLike | str | bytes | BytesIO, ascii_format: bool = True)

Writes the DXF data to the specified file name.

Parameters

• file_name (PathLike | str | bytes | BytesIO) – The file name (including path)
where the DXF data will be written.

• ascii_format (bool, optional) – Export the file as ASCII (True) or binary (False)
DXF format. Defaults to True.

ExportSVG

class ExportSVG(unit: ~build123d.build_enums.Unit = <Unit.MM>, scale: float = 1, margin: float = 0,
fit_to_stroke: bool = True, precision: int = 6, fill_color: ~exporters.ColorIndex |
~ezdxf.colors.RGB | ~build123d.geometry.Color | None = None, line_color:
~exporters.ColorIndex | ~ezdxf.colors.RGB | ~build123d.geometry.Color | None =
ColorIndex.BLACK, line_weight: float = 0.09, line_type: ~exporters.LineType =
LineType.CONTINUOUS, dot_length: ~exporters.DotLength | float =
DotLength.INKSCAPE_COMPAT)

SVG file export functionality.

The ExportSVG class provides functionality for exporting 2D shapes to SVG (Scalable Vector Graphics) format.
SVG is a widely used vector graphics format that is supported by web browsers and various graphic editors.

Parameters

• unit (Unit, optional) – The unit used for the exported SVG. It should be one of the Unit
enums: Unit.MM, Unit.CM, or Unit.IN. Defaults to Unit.MM.

• scale (float, optional) – The scaling factor applied to the exported SVG. Defaults to
1.

• margin (float, optional) – The margin added around the exported shapes. Defaults to
0.

• fit_to_stroke (bool, optional) – A boolean indicating whether the SVG view box
should fit the strokes of the shapes. Defaults to True.

• precision (int, optional) – The number of decimal places used for rounding coordi-
nates in the SVG. Defaults to 6.

• fill_color (ColorIndex | RGB | None, optional) – The default fill color for
shapes. It can be specified as a ColorIndex, an RGB tuple, or None. Defaults to None.

• line_color (ColorIndex | RGB | None, optional) – The default line color for
shapes. It can be specified as a ColorIndex or an RGB tuple, or None. Defaults to Ex-
port2D.DEFAULT_COLOR_INDEX.

• line_weight (float, optional) – The default line weight (stroke width) for shapes, in
millimeters. Defaults to Export2D.DEFAULT_LINE_WEIGHT.

• line_type (LineType, optional) – The default line type for shapes. It should be a Line-
Type enum. Defaults to Export2D.DEFAULT_LINE_TYPE.

• dot_length (DotLength | float, optional) – The width of rendered dots in a
Can be either a DotLength enum or a float value in tenths of an inch. Defaults to
DotLength.INKSCAPE_COMPAT.

<!-- PDF page 356 -->

Example

```python
     exporter = ExportSVG(unit=Unit.MM, line_weight=0.5)
     exporter.add_layer("Layer 1", fill_color=(255, 0, 0), line_color=(0, 0, 255))
     exporter.add_shape(shape_object, layer="Layer 1")
     exporter.write("output.svg")
```

Raises

ValueError – Invalid unit.

add_layer(name: str, *, fill_color: ColorIndex | RGB | Color | None = None, line_color: ColorIndex | RGB |
Color | None = ColorIndex.BLACK, line_weight: float = 0.09, line_type: LineType =
LineType.CONTINUOUS) →Self

Adds a new layer to the SVG export with the given properties.

Parameters

• name (str) – The name of the layer. Must be unique among all layers.

• fill_color (ColorIndex | RGB | Color | None, optional) – The fill color for
shapes on this layer. It can be specified as a ColorIndex, an RGB tuple, a Color, or None.
Defaults to None.

• line_color (ColorIndex | RGB | Color | None, optional) – The line color for
shapes on this layer. It can be specified as a ColorIndex or an RGB tuple, a Color, or None.
Defaults to Export2D.DEFAULT_COLOR_INDEX.

• line_weight (float, optional) – The line weight (stroke width) for shapes on this
layer, in millimeters. Defaults to Export2D.DEFAULT_LINE_WEIGHT.

• line_type (LineType, optional) – The line type for shapes on this layer. It should be
a LineType enum. Defaults to Export2D.DEFAULT_LINE_TYPE.

Raises

• ValueError – Duplicate layer name

• ValueError – Unknown linetype

Returns

Drawing with an additional layer

Return type

Self

add_shape(shape: Shape | Iterable[Shape], layer: str = '', reverse_wires: bool = False)

Adds a shape or a collection of shapes to the specified layer.

Parameters

• shape (Shape | Iterable[Shape]) – The shape or collection of shapes to be added. It
can be a single Shape object or an iterable of Shape objects.

• layer (str, optional) – The name of the layer where the shape(s) will be added. De-
faults to “”.

• reverse_wires (bool, optional) – A boolean indicating whether the wires of the
shape(s) should be in reversed direction. Defaults to False.

Raises

ValueError – Undefined layer

<!-- PDF page 357 -->

```python
     write(path: PathLike | str | bytes | BytesIO)
```

Writes the SVG data to the specified file path.

Parameters

path (PathLike | str | bytes | BytesIO) – The file path where the SVG data will be
written.

1.17.3 3D Exporters

export_brep(to_export: Shape, file_path: PathLike | str | bytes | BytesIO | BinaryIO) →bool

Export this shape to a BREP file

Parameters

• to_export (Shape) – object or assembly

• file_path – Union[PathLike, str, bytes, BytesIO]: brep file path or memory buffer

Returns

write status

Return type

bool

export_gltf(to_export: ~build123d.topology.shape_core.Shape, file_path: ~os.PathLike | str | bytes, unit:
~build123d.build_enums.Unit = <Unit.MM>, binary: bool = False, linear_deflection: float = 0.001,
angular_deflection: float = 0.1) →bool

The glTF (GL Transmission Format) specification primarily focuses on the efficient transmission and loading
of 3D models as a compact, binary format that is directly renderable by graphics APIs like WebGL, OpenGL,
and Vulkan. It’s designed to store detailed 3D model data, including meshes (vertices, normals, textures, etc.),
animations, materials, and scene hierarchy, among other aspects.

Parameters

• to_export (Shape) – object or assembly

• file_path (Union[PathLike, str, bytes]) – glTF file path

• unit (Unit, optional) – shape units. Defaults to Unit.MM.

• binary (bool, optional) – output format. Defaults to False.

• linear_deflection (float, optional) – A linear deflection setting which limits the
distance between a curve and its tessellation. Setting this value too low will result in large
meshes that can consume computing resources. Setting the value too high can result in
meshes with a level of detail that is too low. The default is a good starting point for a range
of cases. Defaults to 1e-3.

• angular_deflection (float, optional) – Angular deflection setting which limits the
angle between subsequent segments in a polyline. Defaults to 0.1.

Raises

RuntimeError – Failed to write glTF file

Returns

write status

Return type

bool

<!-- PDF page 358 -->

export_step(to_export: ~build123d.topology.shape_core.Shape, file_path: ~os.PathLike | str | bytes |
~_io.BytesIO | ~typing.BinaryIO, unit: ~build123d.build_enums.Unit = <Unit.MM>, write_pcurves:
bool = True, precision_mode: ~build123d.build_enums.PrecisionMode =
<PrecisionMode.AVERAGE>, *, timestamp: str | ~datetime.datetime | None = None) →bool

Export a build123d Shape or assembly with color and label attributes. Note that if the color of a node in an
assembly isn’t set, it will be assigned the color of its nearest ancestor.

Parameters

• to_export (Shape) – object or assembly

• file_path (Union[PathLike, str, bytes, BytesIO]) – step file path

• unit (Unit, optional) – shape units. Defaults to Unit.MM.

• write_pcurves (bool, optional) – write parametric curves to the STEP file. Defaults
to True.

• precision_mode (PrecisionMode, optional) – geometric data precision. Defaults to
PrecisionMode.AVERAGE.

Raises

RuntimeError – Unknown Compound type

Returns

success

Return type

bool

export_stl(to_export: Shape, file_path: PathLike | str | bytes, tolerance: float = 0.001, angular_tolerance: float =
0.1, ascii_format: bool = False) →bool

Export STL

Exports a shape to a specified STL file.

Parameters

• to_export (Shape) – object or assembly

• file_path (Union[PathLike, str, bytes]) – The path and file name to write the STL
output to.

• tolerance (float, optional) – A linear deflection setting which limits the distance be-
tween a curve and its tessellation. Setting this value too low will result in large meshes that
can consume computing resources. Setting the value too high can result in meshes with a
level of detail that is too low. The default is a good starting point for a range of cases. Defaults
to 1e-3.

• angular_tolerance (float, optional) – Angular deflection setting which limits the
angle between subsequent segments in a polyline. Defaults to 0.1.

• ascii_format (bool, optional) – Export the file as ASCII (True) or binary (False) STL
format. Defaults to False (binary).

Returns

Success

Return type

bool

<!-- PDF page 359 -->

3D Mesh Export

Both 3MF and STL export (and import) are provided with the Mesher class. As mentioned above, the 3MF format it
provides is feature-rich and therefore has a slightly more complex API than the simple Shape exporters.

For example:

```python
# Create the shapes and assign attributes
blue_shape = Solid.make_cone(20, 0, 50)
blue_shape.color = Color("blue")
blue_shape.label = "blue"
blue_uuid = uuid.uuid1()
red_shape = Solid.make_cylinder(5, 50).move(Location((0, -30, 0)))
red_shape.color = Color("red")
red_shape.label = "red"
```

```python
# Create a Mesher instance as an exporter, add shapes and write
exporter = Mesher()
exporter.add_shape(blue_shape, part_number="blue-1234-5", uuid_value=blue_uuid)
exporter.add_shape(red_shape)
exporter.add_meta_data(
    name_space="custom",
    name="test_meta_data",
    value="hello world",
    metadata_type="str",
    must_preserve=False,
)
exporter.add_code_to_metadata()
exporter.write("example.3mf")
exporter.write("example.stl")
```

```python
class Mesher(unit: ~build123d.build_enums.Unit = <Unit.MM>)
```

Tool for exporting and importing meshed objects stored in 3MF or STL files.

Parameters

unit (Unit, optional) – model units. Defaults to Unit.MM.

```python
     add_code_to_metadata()
```

Add the code calling this method to the 3MF metadata with the custom name space build123d, name equal
to the base file name and the type as python

add_meta_data(name_space: str, name: str, value: str, metadata_type: str, must_preserve: bool)

Add meta data to the models

Parameters

• name_space (str) – categorizer of different metadata entries

• name (str) – metadata label

• value (str) – metadata content

• metadata_type (str) – metadata type

• must_preserve (bool) – metadata must not be removed if unused

<!-- PDF page 360 -->

add_shape(shape: ~build123d.topology.shape_core.Shape |
~collections.abc.Iterable[~build123d.topology.shape_core.Shape], linear_deflection: float =
0.001, angular_deflection: float = 0.1, mesh_type: ~build123d.build_enums.MeshType =
<MeshType.MODEL>, part_number: str | None = None, uuid_value: ~uuid.UUID | None =
None)

Add a shape to the 3MF/STL file.

Parameters

```python
                • shape (Union[Shape, Iterable[Shape]]) – build123d object
```

• linear_deflection (float, optional) – mesh control for edges. Defaults to 0.001.

• angular_deflection (float, optional) – mesh control for non-planar surfaces. De-
faults to 0.1.

• mesh_type (MeshType, optional) – 3D printing use of mesh. Defaults to
MeshType.MODEL.

• part_number (str, optional) – part #. Defaults to None.

• uuid_value (uuid, optional) – value from uuid package. Defaults to None.

Raises

• RuntimeError – 3mf mesh is invalid

• Warning – Degenerate shape skipped

• Warning – 3mf mesh is not manifold

get_mesh_properties() →list[dict]

Retrieve the properties from all the meshes

get_meta_data() →list[dict]

Retrieve all of the metadata

get_meta_data_by_key(name_space: str, name: str) →dict

Retrieve the metadata value and type for the provided name space and name

```python
     property library_version:  str
```

3MF Consortium Lib#MF version

```python
     property mesh_count:  int
```

Number of meshes in the model

```python
     property model_unit:  Unit
```

Unit used in the model

read(file_name: PathLike | str | bytes) →list[Shape]

Parameters

• Union[PathLike (file_name) – file path

• str – file path

• bytes] – file path

Raises

ValueError – Unknown file format - must be 3mf or stl

Returns

build123d shapes extracted from mesh file

<!-- PDF page 361 -->

Return type

list[Shape]

```python
     property triangle_counts:  list[int]
```

Number of triangles in each of the model’s meshes

```python
     property vertex_counts:  list[int]
```

Number of vertices in each of the models’s meshes

```python
     write(file_name: PathLike | str | bytes)
```

Parameters

• Union[Pathlike (file_name) – file path

• str – file path

• bytes] – file path

Raises

ValueError – Unknown file format - must be 3mf or stl

write_stream(stream: BytesIO, file_type: Literal['3mf', 'stl'])

Parameters

• stream (BytesIO) – byte stream

• file_type – output mesh format, either “3mf” or “stl”

Raises

ValueError – Unknown file format - must be 3mf or stl

Note

If you need to align multiple components for 3D printing, you can use the pack() function to arrange the objects
side by side and align them on the same plane. This ensures that your components are well-organized and ready for
the printing process.

1.17.4 2D Importers

import_dxf(dxf_file: str | PathLike | TextIO | BinaryIO) →ShapeList

Import shapes from a DXF file

Parameters

dxf_file (str | PathLike | TextIO | BinaryIO) – dxf file path or readable stream

Raises

DXFStructureError – file not found

Returns

build123d objects

Return type

ShapeList

import_svg(svg_file: str | Path | TextIO, *, flip_y: bool = True, align: Align | tuple[Align, Align] | None =
Align.MIN, ignore_visibility: bool = False, label_by: Literal['id', 'class', 'inkscape:label'] | str = 'id')
→ShapeList[Wire | Face]

<!-- PDF page 362 -->

import_svg(svg_file: str | Path | TextIO, *, flip_y: bool = True, align: Align | tuple[Align, Align] | None =
Align.MIN, ignore_visibility: bool = False, label_by: Literal['id', 'class', 'inkscape:label'] | str = 'id',
is_inkscape_label: bool | None = None) →ShapeList[Wire | Face]

import_svg

Parameters

• svg_file (Union[str, Path, TextIO]) – svg file

• flip_y (bool, optional) – flip objects to compensate for svg orientation. Defaults to
True.

• align (Align | tuple[Align, Align] | None, optional) – alignment of the
SVG’s viewbox, if None, the viewbox’s origin will be at (0,0,0). Defaults to Align.MIN.

• ignore_visibility (bool, optional) – Defaults to False.

• label_by (str, optional) – XML attribute to use for imported shapes’ label property.
Defaults to “id”. Use inkscape:label to read labels set from Inkscape’s “Layers and Objects”
panel.

Raises

ValueError – unexpected shape type

Returns

objects contained in svg

Return type

ShapeList[Union[Wire, Face]]

import_svg_as_buildline_code(file_name: PathLike | str | bytes, precision: int = 6) →tuple[str, str]

translate_to_buildline_code

Translate the contents of the given svg file into executable build123d/BuildLine code.

Parameters

• file_name (PathLike | str | bytes]) – svg file name

• precision (int) – # digits to round values to. Defaults to # digits in TOLERANCE

Returns

code, builder instance name

Return type

tuple[str, str]

1.17.5 3D Importers

import_brep(file_name: PathLike | str | bytes) →Shape

Import shape from a BREP file

Parameters

file_name (Union[PathLike, str, bytes]) – brep file

Raises

ValueError – file not found

Returns

build123d object

Return type

Shape

<!-- PDF page 363 -->

import_step(filename: PathLike | str | bytes) →Compound

Extract shapes from a STEP file and return them as a Compound object.

Parameters

file_name (Union[PathLike, str, bytes]) – file path of STEP file to import

Raises

ValueError – can’t open file

Returns

contents of STEP file

Return type

Compound

import_stl(file_name: ~os.PathLike | str | bytes, model_unit: ~build123d.build_enums.Unit = <Unit.MM>) →
Face

Extract shape from an STL file and return it as a Face reference object.

Note that importing with this method and creating a reference is very fast while creating an editable model (with
Mesher) may take minutes depending on the size of the STL file.

Parameters

• file_name (Union[PathLike, str, bytes]) – file path of STL file to import

• model_unit (Unit, optional) – the default unit used when creating the model. For ex-
ample, Blender defaults to Unit.M. Defaults to Unit.MM.

Raises

• ValueError – Could not import file

• ValueError – Invalid model_unit

Returns

STL model

Return type

Face

STL Reconstruction

The detect_primitives() helper can be used during STL reconstruction to detect analytic planes, cylinders, and
spheres in a mesh-like shape and generate algebra-mode code fragments to aid manual redesign.

See Tutorial: Reconstructing a Design from an STL for the full workflow and limitations.

detect_primitives(mesh: Shape) →tuple[ShapeList[Face], ShapeList[Face], list[str]]

Detect analytic primitives in a mesh and return faces, leftovers, and code.

This is the user-facing entry point for STL-to-BREP reconstruction. The mesh is indexed first so face geometry
and adjacency can be reused throughout the pipeline.

Detection proceeds in stages:

1. High-confidence planes are found first from cleaned proxy faces.

2. Spheres are found next from broad radius-signature classification, connected or sewn regions, local sphere
fitting, and region growth.

3. Cylinders are detected from area-grouped sewn regions and local cylinder seeds, then grown, refit, and
validated.

<!-- PDF page 364 -->

4. Remaining coplanar connected components are detected as fallback planes.

Each accepted patch is converted into a build123d Face, unmatched mesh faces are returned as leftovers, and the
generated code strings are sorted in the same order as the returned primitives.

3D Mesh Import

Both 3MF and STL import (and export) are provided with the Mesher class.

For example:

```python
importer = Mesher()
cone, cyl = importer.read("example.3mf")
print(
```

```python
    f"{importer.mesh_count=}, {importer.vertex_counts=}, {importer.triangle_counts=}"
)
print(f"Imported model unit: {importer.model_unit}")
print(f"{cone.label=}")
print(f"{cone.color.to_tuple()=}")
print(f"{cyl.label=}")
print(f"{cyl.color.to_tuple()=}")
```

```python
importer.mesh_count=2, importer.vertex_counts=[66, 52], importer.triangle_counts=[128,␣
```

```python
˓→100]
Imported model unit: Unit.MM
cone.label='blue'
cone.color.to_tuple()=(0.0, 0.0, 1.0, 1.0)
cyl.label='red'
cyl.color.to_tuple()=(1.0, 0.0, 0.0, 1.0)
```
