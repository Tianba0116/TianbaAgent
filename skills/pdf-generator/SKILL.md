---
name: pdf-generator
description: generate polished pdf documents from text, markdown, or simple html. use when the user asks to create, render, export, or produce a pdf report, handout, proposal, invoice-like document, printable summary, one-page brief, or other text-heavy pdf deliverable. includes a script for reliable markdown/text-to-pdf generation with headings, paragraphs, bullet lists, code blocks, simple tables, page numbers, metadata, and basic typography.
---

# PDF Generator

## Overview

Use this skill to create text-heavy PDF deliverables from Markdown, plain text, or simple HTML. Prefer Markdown as the source format because it is readable, easy to revise, and maps cleanly to PDF structure.

For complex business documents with heavy formatting, author a DOCX first and convert to PDF. For slide-like layouts, author slides first and export to PDF. Use this skill for programmatic reports, briefs, notes, handouts, proposals, checklists, simple invoices, and printable summaries.

## Default workflow

1. Clarify the document purpose only when the user has not provided enough content or format direction.
2. Draft or transform the source content as Markdown.
3. Save the source to a `.md`, `.txt`, or `.html` file.
4. Run `scripts/generate_pdf.py` to create the PDF.
5. Render or inspect the result when possible before returning the final PDF.

## Script usage

Run the bundled script from the skill directory:

```bash
python /home/oai/skills/pdf-generator/scripts/generate_pdf.py --input input.md --output output.pdf --title "Document Title"
```

Use inline content for short documents:

```bash
python /home/oai/skills/pdf-generator/scripts/generate_pdf.py --content "# Title\n\nBody text" --output output.pdf --title "Title"
```

Common options:

```bash
--format md          # md, text, or html; default is inferred from input extension
--page-size A4       # A4, LETTER, LEGAL; default A4
--title "..."        # document title and PDF metadata title
--author "..."       # optional PDF metadata author
--subject "..."      # optional PDF metadata subject
--no-page-numbers    # omit page number footer
```

## Markdown support

The script supports:

- `#`, `##`, and `###` headings
- paragraphs
- unordered lists beginning with `-`, `*`, or `+`
- ordered lists like `1. item`
- fenced code blocks with triple backticks
- block quotes beginning with `>`
- horizontal rules using `---`
- simple pipe tables
- inline bold, italic, and code in a best-effort way

Keep Markdown simple for reliable rendering. Avoid deeply nested tables, wide tables, complex HTML, floats, and pixel-perfect positioning.

## HTML support

The script accepts simple HTML and converts common tags to readable text before rendering. For complex HTML/CSS, use a browser or HTML-to-PDF engine instead of this script.

## Quality checklist

Before returning a PDF:

- Verify the PDF file exists and has nonzero size.
- Inspect the first page visually when practical.
- Ensure there is no clipped text, missing glyphs, or overlapping content.
- Check that page size and title match the user request.
- Keep only the final PDF and useful source file in the deliverable location.

## When to use other approaches

- Use DOCX first when the user needs rich editing, comments, tables of contents, tracked changes, or Microsoft Word compatibility.
- Use slides first when the user needs visual layouts, fixed-position cards, diagrams, or presentation-style pages.
- Use an existing PDF editing skill or toolkit when the task is to modify, split, merge, redact, fill, or inspect an existing PDF.
