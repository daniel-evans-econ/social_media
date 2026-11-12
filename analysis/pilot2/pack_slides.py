"""Package a pilot Beamer deck with its preamble and referenced figures."""

import argparse
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def pack(tex_path, output):
    root = tex_path.parent
    source = tex_path.read_text(encoding="utf-8-sig")
    assets = {tex_path, root / "preamble/header_slides.tex"}
    for name in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+\.png)\}", source):
        assets.add(root / "figures" / name)
    if len(assets) == 2:
        raise ValueError("No slide figures found")
    generator = root / "rebuild_figures.py"
    if generator.exists():
        assets.add(generator)
    for path in assets:
        if not path.is_file():
            raise FileNotFoundError(path)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(assets):
            archive.write(path, path.relative_to(root))
        archive.writestr("README.txt", f"To edit the presentation, open {tex_path.name}.\n"
                         f"To build the PDF, run pdflatex {tex_path.name} twice.\n"
                         "All figures are included. The confidential survey export is unnecessary for compiling.\n")
    with ZipFile(output) as archive:
        if archive.testzip() or not all(p.relative_to(root).as_posix() in archive.namelist() for p in assets):
            raise ValueError("The slide archive failed verification")
    print(f"Packaged and verified {len(assets)} source files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tex", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    pack(args.tex, args.output)
