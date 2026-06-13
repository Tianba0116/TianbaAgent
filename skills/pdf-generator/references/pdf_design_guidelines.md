# PDF Design Guidelines

## Reliable source format

Use Markdown for most generated PDFs. It keeps the content editable and avoids fragile absolute positioning.

## Layout defaults

- Use A4 unless the user asks for Letter or another size.
- Use clear hierarchy: title, sections, subsections, body.
- Use tables only when they are short and narrow.
- Use page numbers for multi-page documents unless the user asks otherwise.
- Avoid manually inserting line breaks to force layout.

## Content patterns

### Report

1. Title
2. Executive summary
3. Key findings
4. Details
5. Recommendations
6. Appendix, if needed

### Proposal

1. Title
2. Context
3. Objectives
4. Scope
5. Timeline
6. Budget or resourcing
7. Next steps

### One-page brief

1. Title
2. Summary
3. Three to five key points
4. Risks or open questions
5. Recommended action

## Verification

After generation, check that the PDF opens and all important text is visible. If CJK or emoji glyphs are missing, use an installed Unicode font such as Noto Sans CJK or DejaVu Sans when available; do not bundle or expose system font files.
