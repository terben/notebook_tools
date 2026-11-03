
import argparse
import base64
import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import nbformat


# Markdown-Bilder und HTML-img-Tags erkennen
MD_IMAGE = re.compile(r'(!\[[^\]]*\]\()([^)]+)(\))')
HTML_IMAGE = re.compile(
    r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2',
    re.IGNORECASE
)


def local_image(src, notebook_dir):
    """Lokale Bilddatei bestimmen."""
    src = src.strip()
    parsed = urlsplit(src)

    if parsed.scheme or parsed.netloc or src.startswith("#"):
        return None

    path = notebook_dir / unquote(parsed.path)

    if not path.is_file():
        return None

    mime, _ = mimetypes.guess_type(path)

    if not mime or not mime.startswith("image/"):
        return None

    return path, mime


def embed_images(input_file, output_file):
    input_file = Path(input_file).resolve()
    notebook_dir = input_file.parent

    nb = nbformat.read(input_file, as_version=4)

    count_md = 0
    count_html = 0

    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue

        attachments = cell.get("attachments", {})

        # 1. Markdown-Bilder als Attachments
        def replace_md(match):
            nonlocal count_md

            src = match.group(2)
            result = local_image(src, notebook_dir)

            if result is None:
                return match.group(0)

            path, mime = result

            encoded = base64.b64encode(
                path.read_bytes()
            ).decode("ascii")

            # Eindeutiger Name innerhalb der Zelle
            name = path.name
            index = 1

            while name in attachments:
                name = f"{path.stem}_{index}{path.suffix}"
                index += 1

            attachments[name] = {mime: encoded}
            count_md += 1

            return (
                match.group(1)
                + "attachment:"
                + name
                + match.group(3)
            )

        source = MD_IMAGE.sub(replace_md, cell.source)

        # 2. HTML-Bilder als Data-URIs
        def replace_html(match):
            nonlocal count_html

            src = match.group(3)
            result = local_image(src, notebook_dir)

            if result is None:
                return match.group(0)

            path, mime = result

            encoded = base64.b64encode(
                path.read_bytes()
            ).decode("ascii")

            data_uri = f"data:{mime};base64,{encoded}"
            count_html += 1

            return (
                match.group(1)
                + match.group(2)
                + data_uri
                + match.group(2)
            )

        source = HTML_IMAGE.sub(replace_html, source)

        cell.source = source

        if attachments:
            cell.attachments = attachments

    nbformat.write(nb, output_file)

    print(f"Markdown-Bilder: {count_md}")
    print(f"HTML-Bilder:     {count_html}")
    print(f"Gespeichert:     {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("notebook")
    parser.add_argument("-o", "--output")

    args = parser.parse_args()

    input_path = Path(args.notebook)

    output_path = (
        Path(args.output)
        if args.output
        else input_path.with_name(
            input_path.stem + "_embedded.ipynb"
        )
    )

    embed_images(input_path, output_path)
