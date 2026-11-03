#!/usr/bin/env python3
"""Embed local images referenced in Markdown cells of a Jupyter notebook.

Markdown images, ![alt](path), become cell attachments, ![alt](attachment:name).
HTML images, <img src="path">, get base64 data URIs as src. Paths are relative
to the notebook directory (the current directory when reading from stdin).
Remote URLs, data URIs and existing attachments are left untouched. Use '-' as
NOTEBOOK or OUTPUT to read from stdin or write to stdout.
"""
import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import nbformat

# ![alt](src) or ![alt](<src with spaces> "title"); groups: prefix, src, suffix
MD_IMAGE = re.compile(r'(!\[[^\]]*\]\(\s*)(<[^>\n]*>|[^\s)]+)((?:\s+(?:"[^"]*"|\'[^\']*\'))?\s*\))')
# <img ... src="..."> with quoted src; groups: prefix, quote, src
HTML_IMAGE = re.compile(r'(<img\b[^>]*?\ssrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE)


def local_image(src, notebook_dir):
    """Return (path, mime type) of a local image, or None if src is not one."""
    src = src.strip().removeprefix('<').removesuffix('>')
    parsed = urlsplit(src)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = notebook_dir / unquote(parsed.path)
    mime, _ = mimetypes.guess_type(path)
    if not path.is_file() or not mime or not mime.startswith('image/'):
        print(f'warning: not a local image file, left unchanged: {src}', file=sys.stderr)
        return None
    return path, mime


def embed_images(nb, notebook_dir):
    """Embed local images in all Markdown cells of nb in place."""
    n_md = n_html = 0

    for cell in nb.cells:
        if cell.cell_type != 'markdown':
            continue
        attachments = cell.get('attachments', {})

        def replace_md(match):
            nonlocal n_md
            image = local_image(match.group(2), notebook_dir)
            if image is None:
                return match.group(0)
            path, mime = image
            bundle = {mime: base64.b64encode(path.read_bytes()).decode('ascii')}
            # Attachment names are unique per cell; spaces would break the link.
            stem, suffix = path.stem.replace(' ', '_'), path.suffix
            name, i = stem + suffix, 1
            while name in attachments and attachments[name] != bundle:
                name, i = f'{stem}_{i}{suffix}', i + 1
            attachments[name] = bundle
            n_md += 1
            return f'{match.group(1)}attachment:{name}{match.group(3)}'

        def replace_html(match):
            nonlocal n_html
            image = local_image(match.group(3), notebook_dir)
            if image is None:
                return match.group(0)
            path, mime = image
            data = base64.b64encode(path.read_bytes()).decode('ascii')
            n_html += 1
            return f'{match.group(1)}{match.group(2)}data:{mime};base64,{data}{match.group(2)}'

        cell.source = HTML_IMAGE.sub(replace_html, MD_IMAGE.sub(replace_md, cell.source))
        if attachments:
            cell.attachments = attachments

    return n_md, n_html


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('notebook', help='input notebook')
    parser.add_argument('-o', '--output',
                        help='output notebook (default: NOTEBOOK_embedded.ipynb)')
    args = parser.parse_args()

    if args.notebook == '-':
        if args.output is None:
            parser.error('-o/--output is required when reading from stdin')
        nb, notebook_dir = nbformat.read(sys.stdin, as_version=4), Path.cwd()
    else:
        nb, notebook_dir = nbformat.read(args.notebook, as_version=4), Path(args.notebook).parent
    output = args.output or Path(args.notebook).with_name(Path(args.notebook).stem + '_embedded.ipynb')

    n_md, n_html = embed_images(nb, notebook_dir)
    nbformat.write(nb, sys.stdout if output == '-' else output)
    print(f'Embedded {n_md} Markdown and {n_html} HTML image(s); wrote {"stdout" if output == "-" else output}',
          file=sys.stderr)


if __name__ == '__main__':
    main()
