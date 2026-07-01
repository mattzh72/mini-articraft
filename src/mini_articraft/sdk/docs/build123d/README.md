# build123d documentation converted for LLM use

This archive contains per-page Markdown files generated from the official build123d ReadTheDocs PDF.

## Contents

- `markdown/` — one Markdown file per documentation page.
- `images/` — images extracted from the PDF and referenced by the Markdown files.
- `index.md` — table of contents linking each generated Markdown page.
- `manifest.json` and `manifest.csv` — machine-readable page metadata.
- `original/build123d.pdf` — the source PDF used for extraction.
- `build123d_all_docs_llm.md` — all generated Markdown combined into one file.

## Conversion notes

- The conversion uses the PDF outline/bookmarks to split the documentation into page-like Markdown files matching the ReadTheDocs HTML pages such as `joints.html`.
- The PDF was generated for release `0.11.1.dev21+gbbce3cdd6`.
- Images are linked locally. They are extracted from the PDF at their page positions, so filenames are generated rather than original asset names.
- Code and literal blocks are fenced when the PDF font indicates monospace text.
- Repeating PDF headers/footers and continuation markers were removed to reduce noise.
- Because the PDF source is paginated, a small amount of line wrapping and spacing reflects the PDF layout rather than the original HTML.
