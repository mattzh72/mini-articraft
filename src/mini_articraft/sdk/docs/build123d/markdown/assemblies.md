---
title: "Assemblies"
source_html: "https://build123d.readthedocs.io/en/latest/assemblies.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "341-345"
generated_on: "2026-07-01"
---

# Assemblies

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 341 -->

1.15 Assemblies

Most CAD designs consist of more than one part which are naturally arranged in some type of assembly. Once parts
have been assembled in a Compound object they can be treated as a unit - i.e. moved() or exported.

To create an assembly in build123d, one needs to create a tree of parts by simply assigning either a Compound object’s
parent or children attributes. To illustrate the process, we’ll extend the Joint Tutorial.

1.15.1 Assigning Labels

In order keep track of objects one can assign a label to all Shape objects. Here we’ll assign labels to all of the
components that will be part of the box assembly:

```python
box.label = "box"
lid.label = "lid"
hinge_outer.label = "outer hinge"
```

<!-- PDF page 342 -->

```python
                                                                      (continued from previous page)
hinge_inner.label = "inner hinge"
m6_screw.label = "M6 screw"
```

The labels are just strings with no further limitations (they don’t have to be unique within the assembly).

1.15.2 Create the Assembly Compound

Creation of the assembly is done by simply creating a Compound object and assigning appropriate parent and
children attributes as shown here:

```python
box_assembly = Compound(label="assembly", children=[box, lid, hinge_inner, hinge_outer])
```

To display the topology of an assembly Compound, the show_topology() method can be used as follows:

```python
print(box_assembly.show_topology())
```

which results in:

```python
assembly        Compound at 0x7fc8ee235760, Location(p=(0, 0, 0), o=(-0, 0, -0))
    box         Compound at 0x7fc8ee2188b0, Location(p=(0, 0, 50), o=(-0, 0, -0))
    lid         Compound at 0x7fc8ee228460, Location(p=(-26, 0, 181), o=(-180, 30, -0))
    inner hinge Hinge    at 0x7fc9292c3f70, Location(p=(-119, 60, 122), o=(90, 0, -150))
    outer hinge Hinge    at 0x7fc9292c3f40, Location(p=(-150, 60, 50), o=(90, 0, 90))
```

To add to an assembly Compound one can change either children or parent attributes.

```python
m6_screw.parent = box_assembly
print(box_assembly.show_topology())
```

and now the screw is part of the assembly.

```python
assembly        Compound at 0x7fc8ee235760, Location(p=(0, 0, 0), o=(-0, 0, -0))
    box         Compound at 0x7fc8ee2188b0, Location(p=(0, 0, 50), o=(-0, 0, -0))
    lid         Compound at 0x7fc8ee228460, Location(p=(-26, 0, 181), o=(-180, 30, -0))
    inner hinge Hinge    at 0x7fc9292c3f70, Location(p=(-119, 60, 122), o=(90, 0, -150))
    outer hinge Hinge    at 0x7fc9292c3f40, Location(p=(-150, 60, 50), o=(90, 0, 90))
    M6 screw    Compound at 0x7fc8ee235310, Location(p=(-157, -40, 70), o=(-0, -90, -60))
```

1.15.3 Shallow vs. Deep Copies of Shapes

Build123d supports the standard python copy module which provides two different types of copy operations copy.
copy() and copy.deepcopy().

Build123d’s implementation of deepcopy() for the Shape class (e.g. Solid, Face, etc.) does just that, creates a
complete copy of the original all the way down to the CAD object. deepcopy is therefore suited to the case where the
copy will be subsequently modified to become its own unique item.

However, when building an assembly a common use case is to include many instances of an object, each one identical
but in a different location. This is where copy.copy() is very useful as it copies all of the Shape except for the actual
CAD object which instead is a reference to the original (OpenCascade refers this as a TShape). As it’s a reference any
changes to the original will be seen in all of the shallow copies.

Consider this example where 100 screws are added to an assembly:

<!-- PDF page 343 -->

```python
screw = import_step("M6-1x12-countersunk-screw.step")
locs = HexLocations(6, 10, 10).local_locations
```

```python
screw_copies = [copy.deepcopy(screw).locate(loc) for loc in locs]
copy_assembly = Compound(children=screw_copies)
export_step(copy_assembly, "copy_assembly.step")
```

which takes about 5 seconds to run (on an older computer) and produces a file of size 51938 KB. However, if a shallow
copy is used instead:

```python
screw = import_step("M6-1x12-countersunk-screw.step")
locs = HexLocations(6, 10, 10).local_locations
```

```python
screw_references = [copy.copy(screw).locate(loc) for loc in locs]
reference_assembly = Compound(children=screw_references)
export_step(reference_assembly, "reference_assembly.step")
```

this takes about ¼ second and produces a file of size 550 KB - just over 1% of the size of the deepcopy() version and
only 12% larger than the screw’s step file.

Using copy.copy() to create references to the original CAD object for assemblies can substantially reduce the time
and resources used to create and store that assembly.

1.15.4 Shapes are Anytree Nodes

The build123d assembly constructs are built using the python anytree package by making the build123d Shape class a
sub-class of anytree’s NodeMixin class. Doing so adds the following attributes to Shape:

• parent - Parent Node. On set, the node is detached from any previous parent node and attached to the new node.

• children - Tuple of all child nodes.

• path - Path of this Node.

• iter_path_reverse - Iterate up the tree from the current node.

• ancestors - All parent nodes and their parent nodes.

• descendants - All child nodes and all their child nodes.

• root - Tree Root Node.

• siblings - Tuple of nodes with the same parent.

• leaves - Tuple of all leaf nodes.

• is_leaf - Node has no children (External Node).

• is_root - Node is tree root.

• height - Number of edges on the longest path to a leaf Node.

• depth - Number of edges to the root Node.

Note

Changing the children attribute

Any iterator can be assigned to the children attribute but subsequently the children are stored as immutable tuple
objects. To add a child to an existing Compound object, the children attribute will have to be reassigned.

<!-- PDF page 344 -->

1.15.5 Iterating Over Compounds

As Compounds are containers for shapes, build123d can iterate over these as required. Complex nested assemblies
(compounds within compounds) do not need to be looped over with recursive functions. In the example below, the
variable total_volume holds the sum of all the volumes in each solid in an assembly. Compare this to assembly3_volume
which only results in the volume of the top level part.

```python
# [import]
from build123d import *
from ocp_vscode import *
```

```python
# Each assembly has a box and the previous assembly.
assembly1 = Compound(label='Assembly1', children=[Box(1, 1, 1),])
assembly2 = Compound(label='Assembly2', children=[assembly1, Box(1, 1, 1)])
assembly3 = Compound(label='Assembly3', children=[assembly2, Box(1, 1, 1)])
total_volume = sum(part.volume for part in assembly3.solids()) # 3
assembly3_volume = assembly3.volume # 1
```

1.15.6 pack

The pack.pack() function arranges objects in a compact, non-overlapping layout within a square(ish) 2D area. It is
designed to minimize the space between objects while ensuring that no two objects overlap.

pack(objects: Collection[Shape], padding: float, align_z: bool = False) →Collection[Shape]

Pack objects in a squarish area in Plane.XY.

Parameters

• objects (Collection[Shape]) – objects to arrange

• padding (float) – space between objects

• align_z (bool, optional) – align shape bottoms to Plane.XY. Defaults to False.

Returns

rearranged objects

Return type

Collection[Shape]

Detailed Description

The pack function uses a bin-packing algorithm to efficiently place objects within a 2D plane, ensuring that there is no
overlap and that the space between objects is minimized. This is particularly useful in scenarios where spatial efficiency
is crucial, such as layout design and object arrangement in constrained spaces.

The function begins by calculating the bounding boxes for each object, including the specified padding. It then uses
a helper function _pack2d to determine the optimal positions for each object within the 2D plane. The positions are
then translated back to the original objects, ensuring that they are arranged without overlapping.

Usage Note

The align_z parameter is especially useful when creating print-plates for 3D printing. By aligning the bottoms of the
shapes to the same XY plane, you ensure that the objects are perfectly positioned for slicing software, which will no
longer need to perform this alignment for you. This can streamline the process and improve the accuracy of the print
setup.

<!-- PDF page 345 -->

Example Usage

```python
# [import]
from build123d import *
from ocp_vscode import *
```

```python
# [initial space]
b1 = Box(100, 100, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
b2 = Box(54, 54, 54, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
b3 = Box(34, 34, 34, align=(Align.MIN, Align.MIN, Align.CENTER), mode=Mode.SUBTRACT)
b4 = Box(24, 24, 24, align=(Align.MAX, Align.MAX, Align.CENTER), mode=Mode.SUBTRACT)
```

```python
# [pack 2D]
```

```python
xy_pack = pack(
    [b1, b2, b3, b4],
    padding=5,
    align_z=False
)
```

```python
# [Pack and align_z]
```

```python
z_pack = pack(
    [b1, b2, b3, b4],
    padding=5,
    align_z=True
)
```

Tip

If you place the arranged objects into a Compound, you can easily determine their bounding box and check whether the
objects fit on your print bed.

```python
# [bounding box]
print(Compound(xy_pack).bounding_box())
# bbox: 0.0 <= x <= 159.0, 0.0 <= y <= 129.0, -54.0 <= z <= 100.0
```

```python
print(Compound(z_pack).bounding_box())
# bbox: 0.0 <= x <= 159.0, 0.0 <= y <= 129.0, 0.0 <= z <= 100.0
```
