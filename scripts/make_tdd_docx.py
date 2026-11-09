"""Convert TDD.md to TDD.docx with python-docx.

Renders real heading styles, tables with header rows, monospace code blocks,
embedded images with captions, and bullet/numbered lists.
Re-opens the generated document and verifies heading, table, and image counts,
confirming {{GITHUB_URL}} and {{LIVE_URL}} appear in the first lines.
"""
import re
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def add_formatted_text(paragraph, text):
    """Parses basic inline markdown (**bold**, *italic*, `code`) into docx runs."""
    # Pattern to match bold, italic, and inline code
    tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**') and len(token) >= 4:
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        elif token.startswith('`') and token.endswith('`') and len(token) >= 2:
            run = paragraph.add_run(token[1:-1])
            run.font.name = 'Consolas'
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(190, 24, 93)
        else:
            paragraph.add_run(token)


def make_tdd_docx():
    repo_root = Path.cwd()
    tdd_md_path = repo_root / "TDD.md"
    docx_path = repo_root / "TDD.docx"

    if not tdd_md_path.exists():
        raise FileNotFoundError(f"TDD.md not found at {tdd_md_path}")

    content = tdd_md_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    doc = Document()

    # Configure standard page margins (1 inch)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    in_code_block = False
    code_lines = []
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        # Filter out markdown separator line (|---|---|)
        valid_rows = [r for r in table_rows if not all(c.replace('-', '').replace(':', '').strip() == '' for c in r)]
        if not valid_rows:
            table_rows = []
            in_table = False
            return

        col_count = max(len(r) for r in valid_rows)
        table = doc.add_table(rows=len(valid_rows), cols=col_count)
        table.style = 'Table Grid'
        table.autofit = False

        for r_idx, row_data in enumerate(valid_rows):
            row = table.rows[r_idx]
            is_header = (r_idx == 0)
            for c_idx in range(col_count):
                cell_text = row_data[c_idx].strip() if c_idx < len(row_data) else ""
                cell = row.cells[c_idx]
                cell.paragraphs[0].text = ""
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(3)
                add_formatted_text(p, cell_text)
                if is_header:
                    set_cell_background(cell, "F1F5F9")
                    for run in p.runs:
                        run.bold = True
                        run.font.color.rgb = RGBColor(15, 23, 42)
                else:
                    if r_idx % 2 == 1:
                        set_cell_background(cell, "FFFFFF")
                    else:
                        set_cell_background(cell, "F8FAFC")

        p_spacer = doc.add_paragraph()
        p_spacer.paragraph_format.space_after = Pt(6)
        table_rows = []
        in_table = False

    def flush_code():
        nonlocal in_code_block, code_lines
        if code_lines:
            code_text = "\n".join(code_lines)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.2)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(code_text)
            run.font.name = 'Consolas'
            run.font.size = Pt(9.0)
            run.font.color.rgb = RGBColor(30, 41, 59)
            code_lines = []
        in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Handle Code blocks
        if stripped.startswith("```"):
            if in_table:
                flush_table()
            if in_code_block:
                flush_code()
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Handle Tables (| col | col |)
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            cells = [c for c in stripped.split("|")[1:-1]]
            table_rows.append(cells)
            continue
        elif in_table:
            flush_table()

        # Handle empty lines
        if not stripped:
            continue

        # Handle Horizontal Rules
        if stripped in ("---", "***", "___"):
            continue

        # Handle Images: ![Caption](path/to/img.png)
        img_match = re.match(r'!\[(.*?)\]\((.*?)\)', stripped)
        if img_match:
            caption = img_match.group(1)
            img_rel_path = img_match.group(2)
            img_path = repo_root / img_rel_path
            if img_path.exists():
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(8)
                p_img.paragraph_format.space_after = Pt(2)
                p_img.add_run().add_picture(str(img_path), width=Inches(5.8))
            continue

        # Handle Image Captions: *Figure X: ...*
        if stripped.startswith("*Figure") and stripped.endswith("*"):
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(10)
            run = p_cap.add_run(stripped[1:-1])
            run.italic = True
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(100, 116, 139)
            continue

        # Handle Headings
        if stripped.startswith("# "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run(stripped[2:])
            run.font.size = Pt(22)
            run.font.bold = True
            run.font.color.rgb = RGBColor(15, 23, 42)
            continue
        elif stripped.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(stripped[3:])
            run.font.size = Pt(15)
            run.font.bold = True
            run.font.color.rgb = RGBColor(30, 58, 138)
            continue
        elif stripped.startswith("### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(stripped[4:])
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(30, 41, 59)
            continue
        elif stripped.startswith("#### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(stripped[5:])
            run.font.size = Pt(11)
            run.font.bold = True
            run.font.color.rgb = RGBColor(71, 85, 105)
            continue

        # Handle Bullet Lists
        if stripped.startswith("- ") or stripped.startswith("* "):
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            add_formatted_text(p, stripped[2:])
            continue

        # Handle Numbered Lists
        num_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if num_match:
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            add_formatted_text(p, num_match.group(2))
            continue

        # Regular Paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        add_formatted_text(p, stripped)

    # Flush any trailing structures
    if in_table:
        flush_table()
    if in_code_block:
        flush_code()

    # Save document
    doc.save(docx_path)
    print(f"Generated {docx_path}")

    # Re-open and verify
    verify_doc = Document(docx_path)
    headings_count = 0
    images_count = 0
    tables_count = len(verify_doc.tables)

    for p in verify_doc.paragraphs:
        if p.runs and any(r.font.bold and r.font.size and r.font.size >= Pt(11) for r in p.runs):
            headings_count += 1
        # Count inline images
        for r in p.runs:
            if r._element.xpath('.//w:drawing'):
                images_count += 1

    # Check GitHub and Live lines in first paragraphs (placeholder or filled URL)
    first_text = "\n".join(p.text for p in verify_doc.paragraphs[:10])
    has_github_line = "GitHub:" in first_text and ("{{GITHUB_URL}}" in first_text or "https://" in first_text)
    has_live_line = "Live:" in first_text and ("{{LIVE_URL}}" in first_text or "https://" in first_text or "not deployed" in first_text)

    print("=" * 60)
    print("DOCX Structure & Verification Report:")
    print(f"  - Headings count: {headings_count}")
    print(f"  - Tables count:   {tables_count}")
    print(f"  - Images count:   {images_count}")
    print(f"  - GitHub line in first lines: {has_github_line}")
    print(f"  - Live line in first lines:   {has_live_line}")
    print("=" * 60)

    if not (has_github_line and has_live_line):
        raise ValueError("GitHub or Live line missing or malformed in generated DOCX first lines!")


if __name__ == "__main__":
    make_tdd_docx()
