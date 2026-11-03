#!/usr/bin/env python3
"""Extract images embedded in Markdown cells of a Jupyter notebook.

Writes Markdown cell attachments and HTML <img> data URIs (as created by
embed_images.py) to image files. Optionally writes a restored notebook in which
these images are replaced by links to the extracted files. The source notebook
is never modified.
"""
import argparse
import base64
import binascii
import mimetypes
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote, unquote_to_bytes

import nbformat

# Same patterns as in embed_images.py.
MD_IMAGE = re.compile(r'(!\[[^\]]*\]\(\s*)(<[^>\n]*>|[^\s)]+)((?:\s+(?:"[^"]*"|\'[^\']*\'))?\s*\))')
HTML_IMAGE = re.compile(r'(<img\b[^>]*?\ssrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE)


def decode_data_uri(uri):
    """Return (mime type, bytes) of an image data URI, or None."""
    header, sep, payload = uri.partition(',')
    if not sep or not header.lower().startswith('data:image/'):
        return None
    mime, *params = header[5:].lower().split(';')
    if 'base64' in params:
        return mime, base64.b64decode(payload)
    return mime, unquote_to_bytes(payload)


def image_extension(mime):
    """'.png' for 'image/png', '.svg' for 'image/svg+xml', etc."""
    return mimetypes.guess_extension(mime) or '.' + mime.split('/')[1].split('+')[0]


def unique_path(directory, name):
    """Return directory/name, adding _1, _2, ... to avoid overwriting files."""
    path, i = directory / name, 1
    while path.exists():
        path, i = directory / f'{Path(name).stem}_{i}{Path(name).suffix}', i + 1
    return path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('notebook', type=Path, help='notebook with embedded images')
    parser.add_argument('-d', '--image-dir', type=Path,
                        help='directory for extracted images (default: NOTEBOOK_images)')
    parser.add_argument('-r', '--restore', action='store_true',
                        help='also write a notebook linking to the extracted images')
    parser.add_argument('-o', '--output', type=Path,
                        help='restored notebook (implies -r; default: NOTEBOOK_restored.ipynb, '
                             'with a trailing _embedded removed from the name)')
    args = parser.parse_args()

    source = args.notebook
    image_dir = args.image_dir or source.with_name(source.stem + '_images')
    output = args.output or source.with_name(source.stem.removesuffix('_embedded') + '_restored.ipynb')
    restore = args.restore or args.output is not None
    if restore and output.resolve() == source.resolve():
        parser.error('the restored notebook must not overwrite the source notebook')

    nb = nbformat.read(source, as_version=4)
    n_attach = n_html = 0

    def save(data, name):
        image_dir.mkdir(parents=True, exist_ok=True)
        path = unique_path(image_dir, name)
        path.write_bytes(data)
        print(f'wrote {path}', file=sys.stderr)
        return path

    def link(path):
        """URL of an extracted image relative to the restored notebook."""
        return quote(Path(os.path.relpath(path, output.parent)).as_posix(), safe='/')

    for cell_no, cell in enumerate(nb.cells, 1):
        if cell.cell_type != 'markdown':
            continue
        attachments = cell.get('attachments', {})
        attachment_files = {}  # attachment name -> extracted file
        uri_files = {}         # data URI -> extracted file

        # 1. Extract images; the notebook is not modified here.
        for name, bundle in attachments.items():
            mime = next((m for m in bundle if m.startswith('image/')), None)
            if mime is None:
                continue
            try:
                data = base64.b64decode(bundle[mime])
            except binascii.Error as exc:
                print(f'warning: cell {cell_no}: invalid attachment {name}: {exc}', file=sys.stderr)
                continue
            filename = Path(name).name or 'image'
            if not Path(filename).suffix:
                filename += image_extension(mime)
            attachment_files[name] = save(data, filename)
            n_attach += 1

        for match in HTML_IMAGE.finditer(cell.source):
            uri = match.group(3)
            if uri in uri_files:
                continue
            try:
                image = decode_data_uri(uri)
            except binascii.Error as exc:
                print(f'warning: cell {cell_no}: invalid data URI: {exc}', file=sys.stderr)
                continue
            if image is not None:
                mime, data = image
                uri_files[uri] = save(data, f'cell_{cell_no:03d}_image{image_extension(mime)}')
                n_html += 1

        if not restore:
            continue

        # 2. Replace embedded images by links to the extracted files.
        restored = set()

        def relink_md(match):
            src = match.group(2).strip('<>')
            name = unquote(src.removeprefix('attachment:'))
            if not src.startswith('attachment:') or name not in attachment_files:
                return match.group(0)
            restored.add(name)
            return match.group(1) + link(attachment_files[name]) + match.group(3)

        def relink_html(match):
            path = uri_files.get(match.group(3))
            if path is None:
                return match.group(0)
            return match.group(1) + match.group(2) + link(path) + match.group(2)

        cell.source = HTML_IMAGE.sub(relink_html, MD_IMAGE.sub(relink_md, cell.source))
        # Keep attachments that are not referenced in the Markdown source.
        for name in restored:
            del attachments[name]
        if 'attachments' in cell and not attachments:
            del cell['attachments']

    if restore:
        output.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(nb, output)
    print(f'Extracted {n_attach} attachment(s) and {n_html} HTML image(s) to {image_dir}'
          + (f'; wrote {output}' if restore else ''), file=sys.stderr)


if __name__ == '__main__':
    main()
