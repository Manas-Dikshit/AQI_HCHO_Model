"""Small utility: render a Markdown file to a single-page PDF.

Uses markdown -> simple HTML -> WeasyPrint for PDF rendering.

Usage:
    python tools/md_to_pdf.py docs/architecture_one_page.md docs/architecture_one_page.pdf
"""
from pathlib import Path
import sys

try:
    from markdown import markdown
except Exception:
    print("Missing dependency: markdown. Install with: pip install markdown")
    raise

try:
    from weasyprint import HTML, CSS
except Exception:
    print("Missing dependency: WeasyPrint. Install with: pip install WeasyPrint")
    raise


def md_to_pdf(src_md: Path, out_pdf: Path) -> None:
    md_text = src_md.read_text(encoding="utf-8")
    html = markdown(md_text)
    # Simple styling to fit single page
    full_html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @page {{ size: A4; margin: 20mm; }}
        body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11pt; color: #111; line-height: 1.2; }}
        h1 {{ font-size: 16pt; margin-bottom: 6px; }}
        h2 {{ font-size: 12pt; margin-bottom: 6px; }}
        ul {{ margin-top: 0; margin-bottom: 6px; }}
        ol {{ margin-top: 0; margin-bottom: 6px; }}
        code {{ background: #f6f8fa; padding: 1px 4px; border-radius: 3px; }}
      </style>
    </head>
    <body>
    {html}
    </body>
    </html>
    """
    HTML(string=full_html).write_pdf(target=str(out_pdf))


def main(argv):
    if len(argv) < 3:
        print("Usage: python tools/md_to_pdf.py INPUT.md OUTPUT.pdf")
        return 2
    src = Path(argv[1])
    out = Path(argv[2])
    if not src.exists():
        print(f"Source not found: {src}")
        return 3
    out.parent.mkdir(parents=True, exist_ok=True)
    md_to_pdf(src, out)
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
