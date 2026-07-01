---
title: "Introduction"
source_html: "https://build123d.readthedocs.io/en/latest/introduction.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "7-13"
generated_on: "2026-07-01"
---

# Introduction

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 7 -->

1.1 Introduction

1.1.1 Key Aspects

The following sections describe some of the key aspects of build123d and illustrate why one might choose this open
source system over proprietary options like SolidWorks, OnShape, Fusion 360, or even other open source systems like
Blender, or OpenSCAD.

Boundary Representation (BREP) Modelling

Boundary representation (BREP) and mesh-based CAD systems are both used to create and manipulate 3D models,
but they differ in the way they represent and store the models.

Advantages of BREP-based CAD systems (e.g. build123d & SolidWorks):

• Precision: BREP-based CAD systems use mathematical representations to define the shape of an object, which
allows for more precise and accurate modeling of complex shapes.

• Topology: BREP-based CAD systems maintain topological information of the 3D model, such as edges, faces
and vertices. This allows for more robust and stable modeling, such as Boolean operations.

• Analytical modeling: BREP-based CAD systems can take advantage of the topological information to perform
analytical operations such as collision detection, mass properties calculations, and finite element analysis.

• Features-based modeling: BREP-based CAD systems are often feature-based, which means that the model is built
by creating and modifying individual features, such as holes, fillets, and chamfers. This allows for parametric
design and easy modification of the model.

• Efficient storage: BREP-based CAD systems use a compact representation to store the 3D model, which is more
efficient than storing a large number of triangles used in mesh-based systems.

Advantages of Mesh-based CAD systems (e.g. Blender, OpenSCAD):

• Simplicity: Mesh-based CAD systems use a large number of triangles to represent the surface of an object, which
makes them easy to use and understand.

• Real-time rendering: Mesh-based CAD systems can be rendered in real-time, which is useful for applications
such as video games and virtual reality.

• Flexibility: Mesh-based CAD systems can be easily exported to other 3D modeling and animation software,
which makes them a good choice for use in the entertainment industry.

• Handling of freeform surfaces: Mesh-based systems are better equipped to handle freeform surfaces, such as
those found in organic shapes, as they do not rely on mathematical representation.

• Handling of large datasets: Mesh-based systems are more suitable for handling large datasets such as point
clouds, as they can be easily converted into a mesh representation.

<!-- PDF page 8 -->

Parameterized Models

Parametrized CAD systems are more effective than non-parametric CAD systems in several ways:

• Reusability: Parametrized CAD models can be easily modified by changing a set of parameters, such as the length
or width of an object, rather than having to manually edit the geometry. This makes it easy to create variations
of a design without having to start from scratch.

• Design exploration: Parametrized CAD systems allow for easy exploration of different design options by chang-
ing the parameters and quickly visualizing the results. This can save a lot of time and effort during the design
process.

• Constraints and relationships: Parametrized CAD systems allow for the definition of constraints and relationships
between different parameters. This ensures that the model remains valid and functional even when parameters
are changed.

• Automation: Parametrized CAD systems can be automated to perform repetitive tasks, such as generating de-
tailed drawings or creating parts lists. This can save a lot of time and effort and reduce the risk of errors.

• Collaboration: Parametrized CAD systems allow different team members to work on different aspects of a design
simultaneously and ensure that the model remains consistent across different stages of the development process.

• Document management: Parametrized CAD systems can generate engineering drawings, BOMs, and other doc-
uments automatically, which makes it easier to manage and track the design history.

In summary, parametrized CAD systems are more effective than non-parametric CAD systems because they provide a
more efficient and flexible way to create and modify designs, and can be easily integrated into the design, manufacturing,
and documentation process.

Python Programming Language

Python is a popular, high-level programming language that has several advantages over other programming languages:

• Readability: Python code is easy to read and understand, with a clear and consistent syntax. This makes it a great
language for beginners and for teams of developers who need to collaborate on a project.

• Versatility: Python is a general-purpose language that can be used for a wide range of tasks, including web
development, scientific computing, data analysis, artificial intelligence, and more. This makes it a great choice
for developers who need to work on multiple types of projects.

• Large community: Python has a large and active community of developers who contribute to the language and
its ecosystem. This means that there are many libraries and frameworks available for developers to use, which
can save a lot of time and effort.

• Good for data science, machine learning, and CAD: Python has a number of libraries such as numpy, pandas,
scikit-learn, tensorflow, and cadquery which are popularly used in data science and machine learning and CAD.

• High-level language: Python is a high-level language, which means it abstracts away many of the low-level details
of the computer. This makes it easy to write code quickly and focus on solving the problem at hand.

• Cross-platform: Python code runs on many different platforms, including Windows, Mac, and Linux, making it
a great choice for developers who need to write code that runs on multiple operating systems.

• Open-source: Python is an open-source programming language, which means it is free to use and distribute.
This makes it accessible to developers of all levels and budgets.

• Large number of libraries and modules: Python has a vast collection of libraries and modules that make it easy
to accomplish complex tasks such as connecting to web servers, reading and modifying files, and connecting to
databases.

<!-- PDF page 9 -->

Open Source Software

Open source and proprietary software systems are different in several ways: B Licensing: Open source software is
licensed in a way that allows users to view, modify, and distribute the source code, while proprietary software is closed
source and the source code is not available to the public.

• Ownership: Open source software is usually developed and maintained by a community of developers, while
proprietary software is owned by a company or individual.

• Cost: Open source software is typically free to use, while proprietary software may require payment for a license
or subscription. Customization: Open source software can be modified and customized by users and developers,
while proprietary software is typically not modifiable by users.

• Support: Open source software may have a larger community of users who can provide support, while proprietary
software may have a smaller community and relies on the company for support. Security: Open source software
can be audited by a large community of developers, which can make it more secure, while proprietary software
may have fewer eyes on the code and may be more vulnerable to security issues.

• Interoperability: Open source software may have better interoperability with other software and platforms, while
proprietary software may have more limited compatibility.

• Reliability: Open source software can be considered as reliable as proprietary software. It is usually used by
large companies, governments, and organizations and has been tested by a large number of users.

In summary, open source and proprietary software systems are different in terms of licensing, ownership, cost, cus-
tomization, support, security, interoperability, and reliability. Open source software is typically free to use and can be
modified by users and developers, while proprietary software is closed-source and may require payment for a license or
subscription. Open source software may have a larger community of users who can provide support, while proprietary
software may have a smaller community and relies on the company for support.

Source Code Control Systems

Most GUI based CAD systems provide version control systems which represent the CAD design and its history. They
allows developers to see changes made to the design over time, in a format that is easy to understand.

On the other hand, a source code control system like Git, is a command-line tool and it provides more granular control
over the code. This makes it suitable for more advanced users and developers who are comfortable working with
command-line interfaces. A source code control system like Git is more flexible and allows developers to perform
tasks like branching and merging, which are not easily done with a GUI version control system. Systems like Git have
several advantages, including:

• Version control: Git allows developers to keep track of changes made to the code over time, making it easy to
revert to a previous version if necessary.

• Collaboration: Git makes it easy for multiple developers to work on the same codebase simultaneously, with the
ability to merge changes from different branches of development.

• Backup: Git provides a way to backup and store the codebase in a remote repository, like GitHub. This can serve
as a disaster recovery mechanism, in case of data loss.

• Branching: Git allows developers to create multiple branches of a project for different features or bug fixes, which
can be easily merged into the main codebase once they are complete.

• Auditing: Git allows you to see who made changes to the code, when and what changes were made, which is
useful for auditing and debugging.

• Open-source development: Git makes it easy for open-source developers to contribute to a project and share their
work with the community.

• Flexibility: Git is a distributed version control system, which means that developers can work independently and
offline. They can then push their changes to a remote repository when they are ready to share them with others.

<!-- PDF page 10 -->

In summary, GUI version control systems are generally more user-friendly and easier to use, while source code control
systems like Git offer more flexibility and control over the code. Both can be used to achieve the same goal, but they
cater to different types of users and use cases.

Automated Testing

Users of source based CAD systems can benefit from automated testing which improves their source code by:

• Finding bugs: Automated tests can detect bugs in the code, which can then be fixed before the code is released.
This helps to ensure that the code is of higher quality and less likely to cause issues when used.

• Regression testing: Automated tests can be used to detect regressions, which are bugs that are introduced by
changes to the codebase. This helps to ensure that changes to the code do not break existing functionality.

• Documenting code behavior: Automated tests can serve as documentation for how the code is supposed to behave.
This makes it easier for developers to understand the code and make changes without breaking it.

• Improving code design: Writing automated tests often requires a good understanding of the code and how it is
supposed to behave. This can lead to a better design of the code, as developers will have a better understanding
of the requirements and constraints.

• Saving time and cost: Automated testing can save time and cost by reducing the need for manual testing. Auto-
mated tests can be run quickly and often, which means that bugs can be found and fixed early in the development
process, which is less expensive than finding them later.

• Continuous integration and delivery: Automated testing can be integrated into a continuous integration and
delivery (CI/CD) pipeline. This means that tests are run automatically every time code is committed and can be
integrated with other tools such as code coverage, static analysis and more.

• Improving maintainability: Automated tests can improve the maintainability of the code by making it easier to
refactor and change the codebase. This is because automated tests provide a safety net that ensures that changes
to the code do not introduce new bugs.

Overall, automated testing is an essential part of the software development process, it helps to improve the quality of
the code by detecting bugs early, documenting code behavior, and reducing the cost of maintaining and updating the
code.

Automated Documentation

The Sphinx automated documentation system was used to create the page you are reading now and can be used for user
design documentation as well. Such systems are used for several reasons:

• Consistency: Sphinx and other automated documentation systems can generate documentation in a consistent
format and style, which makes it easier to understand and use.

• Automation: Sphinx can automatically generate documentation from source code and comments, which saves
time and effort compared to manually writing documentation.

• Up-to-date documentation: Automated documentation systems like Sphinx can update the documentation auto-
matically when the code changes, ensuring that the documentation stays up-to-date with the code.

• Searchability: Sphinx and other automated documentation systems can include search functionality, which makes
it easy to find the information you need.

• Cross-referencing: Sphinx can automatically create links between different parts of the documentation, making
it easy to navigate and understand the relationships between different parts of the code.

• Customizable: Sphinx and other automated documentation systems can be customized to match the look and
feel of your company’s documentation.

• Multiple output formats: Sphinx can generate documentation in multiple formats such as HTML, PDF, ePub,
and more.

<!-- PDF page 11 -->

• Support for multiple languages: Sphinx can generate documentation in multiple languages, which can make it
easier to support international users.

• Integration with code management: Sphinx can be integrated with code management tools like Git, which allows
documentation to be versioned along with the code.

In summary, automated documentation systems like Sphinx are used to generate consistent, up-to-date, and searchable
documentation from source code and comments. They save time and effort compared to manual documentation, and
can be customized to match the look and feel of your company’s documentation. They also provide multiple output
formats, support for multiple languages and can be integrated with code management tools.

1.1.2 Advantages Over CadQuery

As mentioned previously, the most significant advantage is that build123d is more pythonic. Specifically:

Standard Python Context Manager

The creation of standard instance variables, looping and other normal python operations is enabled by the replacement
of method chaining (fluent programming) with a standard python context manager.

```python
# CadQuery Fluent API
pillow_block = (cq.Workplane("XY")
```

```python
    .box(height, width, thickness)
    .edges("|Z")
    .fillet(fillet)
    .faces(">Z")
    .workplane()
    ...
)
```

```python
# build123d API
with BuildPart() as pillow_block:
```

```python
    with BuildSketch() as plan:
```

```python
        Rectangle(width, height)
        fillet(plan.vertices(), radius=fillet)
    extrude(thickness)
    ...
```

The use of the standard with block allows standard python instructions to be inserted anyway in the code flow. One can
insert a CQ-editor debug or standard print statement anywhere in the code without impacting functionality. Simple
python for loops can be used to repetitively create objects instead of forcing users into using more complex lambda
and iter operations.

Instantiated Objects

Each object and operation is now a class instantiation that interacts with the active context implicitly for the user. These
instantiations can be assigned to an instance variable as with standard python programming for direct use.

```python
with BuildSketch() as plan:
    r = Rectangle(width, height)
    print(r.area)
    ...
```

<!-- PDF page 12 -->

Operators

New operators have been created to extract information from objects created previously in the code. The @ operator
extracts the position along an Edge or Wire while the % operator extracts the tangent along an Edge or Wire. The
position parameter are float values between 0.0 and 1.0 which represent the beginning and end of the line. In the
following example, a spline is created from the end of l5 (l5 @ 1) to the beginning of l6 (l6 @ 0) with tangents equal
to the tangents of l5 and l6 at their end and beginning respectively. Being able to extract information from existing
features allows the user to “snap” new features to these points without knowing their numeric values.

```python
with BuildLine() as outline:
```

```python
    ...
    l5 = Polyline(...)
    l6 = Polyline(...)
    Spline(l5 @ 1, l6 @ 0, tangents=(l5 % 1, l6 % 0))
```

Last Operation Objects

All of the vertices(), edges(), faces(), and solids() methods of the builders can either return all of the objects requested
or just the objects changed during the last operation. This allows the user to easily access features for further refinement,
as shown in the following code where the final line selects the edges that were added by the last operation and fillets
them. Such a selection would be quite difficult otherwise.

```python
from build123d import *
```

```python
with BuildPart() as pipes:
    box = Box(10, 10, 10, rotation=(10, 20, 30))
    with BuildSketch(*box.faces()) as pipe:
```

```python
        Circle(4)
    extrude(amount=-5, mode=Mode.SUBTRACT)
    with BuildSketch(*box.faces()) as pipe:
```

```python
        Circle(4.5)
        Circle(4, mode=Mode.SUBTRACT)
    extrude(amount=10)
    fillet(pipes.edges(Select.LAST), 0.2)
```

Extensions

Extending build123d is relatively simple in that custom objects or operations can be created as new classes without the
need to monkey patch any of the core functionality. These new classes will be seen in IDEs which is not possible with
monkey patching the core CadQuery classes.

Enums

All Literal strings have been replaced with Enum which allows IDEs to prompt users for valid options without having
to refer to documentation.

Selectors replaced by Lists

String based selectors have been replaced with standard python filters and sorting which opens up the full functionality
of python lists. To aid the user, common operations have been optimized as shown here along with a fully custom
selection:

```python
top = rail.faces().filter_by(Axis.Z)[-1]
...
```

<!-- PDF page 13 -->

```python
                                                                      (continued from previous page)
outside_vertices = filter(
```

```python
    lambda v: (v.Y == 0.0 or v.Y == height) and -width / 2 < v.X < width / 2,
    din.vertices(),
)
```
