"""Minimal Markdown -> one-page PDF converter without external dependencies.

This script reads a Markdown file, converts it to plain text, and writes
a single-page PDF using only Python's standard library. It is intentionally
simple and suitable for short, one-page summaries.

Usage:
    python tools/md_to_pdf_minimal.py docs/architecture_one_page.md docs/architecture_one_page.pdf
"""
from pathlib import Path
import sys
import textwrap
import unicodedata


def md_to_plain_text(md: str) -> str:
    # Very small markdown -> plain text converter: remove headings and code ticks
    lines = []
    for raw in md.splitlines():
        s = raw.strip()
        if not s:
            lines.append("")
            continue
        # Remove heading markers
        if s.startswith('#'):
            s = s.lstrip('#').strip()
        # Remove code ticks
        s = s.replace('`', '')
        # Replace long dashes with hyphen
        s = s.replace('—', '-')
        # Convert bullet lists
        if s.startswith('- '):
            s = '• ' + s[2:]
        lines.append(s)
    text = '\n'.join(lines)
    # Normalize to ASCII to avoid non-ASCII glyphs in raw PDF content
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return text


def escape_pdf_text(s: str) -> str:
    return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def build_pdf(text: str, page_width=595, page_height=842, left=40, top=800, fontsize=11, linespacing=14):
    # Wrap text into lines
    wrapped = []
    for para in text.split('\n'):
        if not para.strip():
            wrapped.append('')
            continue
        wrapped.extend(textwrap.wrap(para, width=100))

    # Build content stream
    content_lines = []
    content_lines.append('BT')
    content_lines.append(f'/F1 {fontsize} Tf')
    content_lines.append(f'{left} {top} Td')
    for i, line in enumerate(wrapped):
        esc = escape_pdf_text(line)
        content_lines.append(f'({esc}) Tj')
        # Move down unless last line
        if i != len(wrapped) - 1:
            content_lines.append(f'0 -{linespacing} Td')
    content_lines.append('ET')
    content = '\n'.join(content_lines) + '\n'
    content_bytes = content.encode('latin1', 'ignore')

    # Build PDF objects
    objs = []

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
        % (page_width, page_height)
    )
    obj4 = b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    obj5_prefix = f"5 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode('ascii')
    obj5_suffix = b"endstream\nendobj\n"

    objs = [obj1, obj2, obj3, obj4, obj5_prefix + content_bytes + b"\n" + obj5_suffix]

    # Compose PDF and compute offsets
    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for obj in objs:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    # xref table
    pdf.extend(f"xref\n0 {len(objs) + 1}\n".encode('ascii'))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets:
        pdf.extend(f"{off:010d} 00000 n \n".encode('ascii'))

    trailer = f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    pdf.extend(trailer.encode('ascii'))
    return bytes(pdf)


def main(argv):
    if len(argv) < 3:
        print("Usage: python tools/md_to_pdf_minimal.py INPUT.md OUTPUT.pdf")
        return 2
    src = Path(argv[1])
    out = Path(argv[2])
    if not src.exists():
        print(f"Source not found: {src}")
        return 3
    md = src.read_text(encoding='utf-8')
    plain = md_to_plain_text(md)
    pdf_bytes = build_pdf(plain)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pdf_bytes)
    print(f"Wrote: {out}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
