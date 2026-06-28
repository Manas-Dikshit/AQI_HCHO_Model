import subprocess, sys, os

svg_path = os.path.join(os.path.dirname(__file__), "architecture_diagram.svg")
png_path = svg_path.replace(".svg", ".png")

# Try cairosvg first
try:
    import cairosvg
    with open(svg_path, "rb") as f:
        cairosvg.svg2png(file_obj=f, write_to=png_path, output_width=1920, output_height=1080)
    print(f"PNG saved to {png_path} (via cairosvg)")
    sys.exit(0)
except ImportError:
    pass

# Try Inkscape
try:
    subprocess.run([
        "inkscape", svg_path,
        "--export-type=png",
        "--export-filename=" + png_path,
        "--export-width=1920", "--export-height=1080"
    ], check=True, capture_output=True)
    print(f"PNG saved to {png_path} (via Inkscape)")
    sys.exit(0)
except (subprocess.CalledProcessError, FileNotFoundError):
    pass

# Try rsvg-convert (librsvg)
try:
    subprocess.run([
        "rsvg-convert", svg_path,
        "-w", "1920", "-h", "1080",
        "-o", png_path
    ], check=True, capture_output=True)
    print(f"PNG saved to {png_path} (via rsvg-convert)")
    sys.exit(0)
except (subprocess.CalledProcessError, FileNotFoundError):
    pass

print("Could not convert to PNG. Install cairosvg (`pip install cairosvg`) or Inkscape.")
print(f"SVG file ready at: {svg_path}")
print("SVG can be inserted directly into PowerPoint.")
