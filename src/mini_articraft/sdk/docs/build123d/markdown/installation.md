---
title: "Installation"
source_html: "https://build123d.readthedocs.io/en/latest/installation.html"
extracted_from: "official ReadTheDocs PDF"
pdf_release: "0.11.1.dev21+gbbce3cdd6"
pdf_pages: "13-14"
generated_on: "2026-07-01"
---

# Installation

> Converted to Markdown from the official build123d ReadTheDocs PDF. PDF page markers and local extracted-image links are included for traceability. Some line wrapping reflects the PDF layout.
<!-- PDF page 13 -->

1.2 Installation

The recommended method for most users to install build123d is:

```python
>>> pip install build123d
```

Note

The ocp-vscode viewer has the ability to install build123d.

1.2.1 Install build123d from GitHub:

To get the latest non-released version of build123d one can install from GitHub using one of the following two com-
mands:

In Linux/MacOS, use the following command:

```python
>>> python3 -m pip install git+https://github.com/gumyr/build123d
```

In Windows, use the following command:

```python
>>> python -m pip install git+https://github.com/gumyr/build123d
```

If you receive errors about conflicting dependencies, you can retry the installation after having upgraded pip to the
latest version with the following command:

```python
>>> python3 -m pip install --upgrade pip
```

If you use poetry to install build123d, you can simply use:

```python
>>> poetry add build123d
```

However, if you want the latest commit from GitHub you might need to specify the branch that is used for git-based
installs; until quite recently, poetry used to checkout the master branch when none was specified, and this fails on
build123d that uses a dev branch.

Pip does not suffer from this issue because it correctly fetches the repository default branch.

If you are a poetry user, you can work around this issue by installing build123d in the following way:

```python
>>> poetry add git+https://github.com/gumyr/build123d.git@dev
```

Please note that always suffixing the URL with @dev is safe and will work with both older and recent versions of poetry.

<!-- PDF page 14 -->

1.2.2 Development install of build123d:

Warning: it is highly recommended to upgrade pip to the latest version before installing build123d, especially in
development mode. This can be done with the following command:

```python
>>> python3 -m pip install --upgrade pip
```

Once pip is up-to-date, you can install build123d in development mode with the following commands:

```python
>>> git clone https://github.com/gumyr/build123d.git
>>> cd build123d
>>> python3 -m pip install -e .
```

Please substitute python3 with python in the lines above if you are using Windows.

If you’re working directly with the OpenCascade OCP layer you will likely want to install the OCP stubs as follows:

```python
>>> python3 -m pip install git+https://github.com/CadQuery/OCP-stubs@7.7.0
```

1.2.3 Test your build123d installation:

If all has gone well, you can open a command line/prompt, and type:

```python
>>> python
>>> from build123d import *
>>> print(Solid.make_box(1,2,3).show_topology(limit_class="Face"))
```

Which should return something similar to:

```python
Solid        at 0x165e75379f0, Center(0.5, 1.0, 1.5)
    Shell    at 0x165eab056f0, Center(0.5, 1.0, 1.5)
            Face at 0x165b35a3570, Center(0.0, 1.0, 1.5)
            Face at 0x165e77957f0, Center(1.0, 1.0, 1.5)
            Face at 0x165b3e730f0, Center(0.5, 0.0, 1.5)
            Face at 0x165e8821570, Center(0.5, 2.0, 1.5)
            Face at 0x165e88218f0, Center(0.5, 1.0, 0.0)
            Face at 0x165eb21ee70, Center(0.5, 1.0, 3.0)
```

1.2.4 Adding a nicer GUI

If you prefer to have a GUI available, your best option is to choose one from here: External Tools and Libraries
