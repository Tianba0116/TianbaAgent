#!/usr/bin/env python3
"""Generate a simple, polished PDF from Markdown, text, or simple HTML.

Examples:
    python generate_pdf.py --input report.md --output report.pdf --title "Quarterly Report"
    python generate_pdf.py --content "# Hello\n\nWorld" --output hello.pdf
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, LETTER, LEGAL
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        ListFlowable,
        ListItem,
        PageTemplate,
        Paragraph,
        Preformatted,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
    )
except Exception as exc:  # pragma: no cover
    print(
        "Missing dependency: reportlab. Install it with `pip install reportlab`.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc

PAGE_SIZES = {"A4": A4, "LETTER": LETTER, "LEGAL": LEGAL}

FONT_CANDIDATES = [
    ("NotoSansCJK", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ("NotoSans", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ("ArialUnicode", "/Library/Fonts/Arial Unicode.ttf"),
]

MONO_FONT_CANDIDATES = [
    ("DejaVuSansMono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ("NotoSansMono", "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf"),
]


def register_font(candidates: Sequence[Tuple[str, str]], fallback: str) -> str:
    for name, path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return fallback


def escape_inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<i>\1</i>", text)
    return text


def simple_html_to_text(source: str) -> str:
    replacements = [
        (r"<\s*br\s*/?>", "\n"),
        (r"<\s*/p\s*>", "\n\n"),
        (r"<\s*/div\s*>", "\n"),
        (r"<\s*h1[^>]*>", "# "),
        (r"<\s*/h1\s*>", "\n\n"),
        (r"<\s*h2[^>]*>", "## "),
        (r"<\s*/h2\s*>", "\n\n"),
        (r"<\s*h3[^>]*>", "### "),
        (r"<\s*/h3\s*>", "\n\n"),
        (r"<\s*li[^>]*>", "- "),
        (r"<\s*/li\s*>", "\n"),
    ]
    text = source
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def split_table_row(line: str) -> List[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def is_table_start(lines: Sequence[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and "|" in lines[index]
        and "|" in lines[index + 1]
        and is_table_separator(lines[index + 1])
    )


def flush_paragraph(buffer: List[str], story: List, style: ParagraphStyle) -> None:
    if buffer:
        story.append(Paragraph(escape_inline(" ".join(part.strip() for part in buffer)), style))
        story.append(Spacer(1, 0.10 * inch))
        buffer.clear()


def flush_list(items: List[str], story: List, bullet_style: ParagraphStyle, ordered: bool) -> None:
    if not items:
        return
    flowables = [ListItem(Paragraph(escape_inline(item), bullet_style)) for item in items]
    story.append(
        ListFlowable(
            flowables,
            bulletType="1" if ordered else "bullet",
            start="1" if ordered else None,
            leftIndent=18,
            bulletFontName=bullet_style.fontName,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    items.clear()


def parse_markdown(source: str, styles) -> List:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    story: List = []
    paragraph: List[str] = []
    list_items: List[str] = []
    list_ordered = False
    in_code = False
    code_lines: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["CodeBlock"]))
                story.append(Spacer(1, 0.12 * inch))
                code_lines = []
                in_code = False
            else:
                flush_paragraph(paragraph, story, styles["Body"])
                flush_list(list_items, story, styles["Bullet"], list_ordered)
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if not stripped:
            flush_paragraph(paragraph, story, styles["Body"])
            flush_list(list_items, story, styles["Bullet"], list_ordered)
            i += 1
            continue

        if is_table_start(lines, i):
            flush_paragraph(paragraph, story, styles["Body"])
            flush_list(list_items, story, styles["Bullet"], list_ordered)
            rows = [split_table_row(lines[i])]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(split_table_row(lines[i]))
                i += 1
            table_data = [[Paragraph(escape_inline(cell), styles["TableCell"]) for cell in row] for row in rows]
            table = Table(table_data, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.15 * inch))
            continue

        if stripped == "---":
            flush_paragraph(paragraph, story, styles["Body"])
            flush_list(list_items, story, styles["Bullet"], list_ordered)
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            story.append(Spacer(1, 0.15 * inch))
            i += 1
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph(paragraph, story, styles["Body"])
            flush_list(list_items, story, styles["Bullet"], list_ordered)
            level = len(heading.group(1))
            style_name = "Heading1" if level == 1 else "Heading2" if level == 2 else "Heading3"
            story.append(Paragraph(escape_inline(heading.group(2)), styles[style_name]))
            story.append(Spacer(1, 0.08 * inch))
            i += 1
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if bullet or ordered:
            flush_paragraph(paragraph, story, styles["Body"])
            item_text = (bullet or ordered).group(1)
            item_ordered = bool(ordered)
            if list_items and item_ordered != list_ordered:
                flush_list(list_items, story, styles["Bullet"], list_ordered)
            list_ordered = item_ordered
            list_items.append(item_text)
            i += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph(paragraph, story, styles["Body"])
            flush_list(list_items, story, styles["Bullet"], list_ordered)
            quote = stripped.lstrip(">").strip()
            story.append(Paragraph(escape_inline(quote), styles["Quote"]))
            story.append(Spacer(1, 0.08 * inch))
            i += 1
            continue

        flush_list(list_items, story, styles["Bullet"], list_ordered)
        paragraph.append(stripped)
        i += 1

    flush_paragraph(paragraph, story, styles["Body"])
    flush_list(list_items, story, styles["Bullet"], list_ordered)
    if in_code and code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["CodeBlock"]))
    return story


def build_styles(base_font: str, mono_font: str):
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCustom",
            parent=styles["Title"],
            fontName=base_font,
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading1Custom",
            parent=styles["Heading1"],
            fontName=base_font,
            fontSize=18,
            leading=23,
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading2Custom",
            parent=styles["Heading2"],
            fontName=base_font,
            fontSize=14,
            leading=18,
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading3Custom",
            parent=styles["Heading3"],
            fontName=base_font,
            fontSize=12,
            leading=16,
            spaceBefore=6,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontName=base_font,
            fontSize=10.5,
            leading=15,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletCustom",
            parent=styles["BodyCustom"],
            leftIndent=12,
            firstLineIndent=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeBlockCustom",
            parent=styles["Code"],
            fontName=mono_font,
            fontSize=8.5,
            leading=11,
            backColor=colors.whitesmoke,
            borderColor=colors.lightgrey,
            borderWidth=0.25,
            borderPadding=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="QuoteCustom",
            parent=styles["BodyCustom"],
            leftIndent=18,
            textColor=colors.dimgray,
            borderColor=colors.lightgrey,
            borderWidth=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCellCustom",
            parent=styles["BodyCustom"],
            fontSize=9,
            leading=12,
        )
    )
    return {
        "Title": styles["TitleCustom"],
        "Heading1": styles["Heading1Custom"],
        "Heading2": styles["Heading2Custom"],
        "Heading3": styles["Heading3Custom"],
        "Body": styles["BodyCustom"],
        "Bullet": styles["BulletCustom"],
        "CodeBlock": styles["CodeBlockCustom"],
        "Quote": styles["QuoteCustom"],
        "TableCell": styles["TableCellCustom"],
    }


def infer_format(input_path: Optional[str], explicit: Optional[str]) -> str:
    if explicit:
        return explicit.lower()
    if input_path:
        suffix = Path(input_path).suffix.lower()
        if suffix in {".md", ".markdown"}:
            return "md"
        if suffix in {".html", ".htm"}:
            return "html"
    return "text"


def draw_footer(canvas, doc, title: str, show_page_numbers: bool):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    width, _height = doc.pagesize
    if title:
        canvas.drawString(doc.leftMargin, 0.45 * inch, title[:90])
    if show_page_numbers:
        canvas.drawRightString(width - doc.rightMargin, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def make_pdf(
    source: str,
    output: str,
    source_format: str,
    title: Optional[str],
    author: Optional[str],
    subject: Optional[str],
    page_size_name: str,
    show_page_numbers: bool,
) -> None:
    base_font = register_font(FONT_CANDIDATES, "Helvetica")
    mono_font = register_font(MONO_FONT_CANDIDATES, "Courier")
    styles = build_styles(base_font, mono_font)

    if source_format == "html":
        source = simple_html_to_text(source)
        source_format = "md"

    page_size = PAGE_SIZES.get(page_size_name.upper(), A4)
    doc = BaseDocTemplate(
        output,
        pagesize=page_size,
        leftMargin=0.72 * inch,
        rightMargin=0.72 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.72 * inch,
        title=title or "Generated PDF",
        author=author or "",
        subject=subject or "",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(
        id="main",
        frames=[frame],
        onPage=lambda canvas, d: draw_footer(canvas, d, title or "", show_page_numbers),
    )
    doc.addPageTemplates([template])

    story: List = []
    if title:
        story.append(Paragraph(escape_inline(title), styles["Title"]))
        story.append(Spacer(1, 0.10 * inch))

    if source_format == "md":
        story.extend(parse_markdown(source, styles))
    else:
        for paragraph in re.split(r"\n\s*\n", source.strip()):
            if paragraph.strip():
                story.append(Paragraph(escape_inline(" ".join(paragraph.splitlines())), styles["Body"]))
                story.append(Spacer(1, 0.10 * inch))

    if not story:
        story.append(Paragraph(" ", styles["Body"]))

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)


def read_source(args) -> str:
    if args.content is not None:
        return args.content
    if not args.input:
        raise SystemExit("Provide --input or --content.")
    return Path(args.input).read_text(encoding=args.encoding)


def parse_args(argv: Optional[Sequence[str]] = None):
    parser = argparse.ArgumentParser(description="Generate a PDF from Markdown, text, or simple HTML.")
    parser.add_argument("--input", help="Input .md, .txt, or .html file.")
    parser.add_argument("--content", help="Inline source content. Use \n for new lines.")
    parser.add_argument("--output", required=True, help="Output PDF path.")
    parser.add_argument("--format", choices=["md", "text", "html"], help="Input format. Defaults to extension inference.")
    parser.add_argument("--title", help="Document title and PDF metadata title.")
    parser.add_argument("--author", help="PDF metadata author.")
    parser.add_argument("--subject", help="PDF metadata subject.")
    parser.add_argument("--page-size", default="A4", choices=sorted(PAGE_SIZES), help="PDF page size.")
    parser.add_argument("--encoding", default="utf-8", help="Input file encoding.")
    parser.add_argument("--no-page-numbers", action="store_true", help="Hide footer page numbers.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    source = read_source(args)
    source_format = infer_format(args.input, args.format)
    make_pdf(
        source=source,
        output=args.output,
        source_format=source_format,
        title=args.title,
        author=args.author,
        subject=args.subject,
        page_size_name=args.page_size,
        show_page_numbers=not args.no_page_numbers,
    )
    output_path = Path(args.output)
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise SystemExit("PDF generation failed: output file missing or empty.")
    print(str(output_path.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
