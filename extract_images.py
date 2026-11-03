#!/usr/bin/env python3
"""Extract notebook markdown attachments and HTML data-URI images.

Optionally create a copy of the notebook referring to extracted local files.
"""
import argparse
import base64
import binascii
import json
import mimetypes
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote_to_bytes

EXTENSIONS = {
    'image/png': '.png', 'image/jpeg': '.jpg', 'image/gif': '.gif',
    'image/svg+xml': '.svg', 'image/webp': '.webp', 'image/bmp': '.bmp',
    'image/tiff': '.tiff', 'image/avif': '.avif',
}
MD_ATTACHMENT = re.compile(r'(!\[[^\]]*\]\(\s*)attachment:([^\s)]+)(\s*(?:["\'][^"\']*["\'])?\s*\))')


def decode_data_uri(uri):
    header, sep, payload = uri.partition(',')
    if not sep or not header.lower().startswith('data:'):
        return None
    parts = header[5:].split(';')
    mime = (parts[0] or 'text/plain').lower()
    if not mime.startswith('image/'):
        return None
    if any(p.lower() == 'base64' for p in parts[1:]):
        data = base64.b64decode(re.sub(r'\s+', '', payload), validate=True)
    else:
        data = unquote_to_bytes(payload)
    return mime, data


class ImgLocator(HTMLParser):
    """Find original source spans of quoted/unquoted HTML img src values."""
    SRC = re.compile(r'\bsrc\s*=\s*(?:(["\'])(.*?)\1|([^\s>]+))', re.I | re.S)

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.spans = []
        self.lines = source.splitlines(keepends=True)
        self.offsets = [0]
        for line in self.lines:
            self.offsets.append(self.offsets[-1] + len(line))

    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'img':
            return
        raw = self.get_starttag_text()
        match = self.SRC.search(raw)
        if not match:
            return
        group = 2 if match.group(1) else 3
        line, col = self.getpos()
        offset = self.offsets[line - 1] + col
        start, end = match.span(group)
        self.spans.append((offset + start, offset + end, match.group(group)))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def safe_name(name):
    name = Path(name.replace('\\', '/')).name
    return name if name not in ('', '.', '..') else 'image'


def unique_path(directory, name):
    base = safe_name(name)
    path = directory / base
    n = 1
    while path.exists():
        path = directory / f'{Path(base).stem}_{n}{Path(base).suffix}'
        n += 1
    return path


def image_extension(mime):
    return EXTENSIONS.get(mime) or mimetypes.guess_extension(mime)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('notebook', type=Path)
    parser.add_argument('-o', '--output', type=Path, help='Folder for extracted images')
    parser.add_argument('--restore-links', action='store_true', help='Also create a notebook with local image links')
    parser.add_argument('--notebook-output', type=Path, help='Path for restored notebook (implies --restore-links)')
    args = parser.parse_args()

    source_path = args.notebook.resolve()
    image_dir = (args.output or source_path.with_name(source_path.stem + '_images')).resolve()
    restored_path = (args.notebook_output or source_path.with_name(source_path.stem.removesuffix('_embedded') + '_restored.ipynb')).resolve()
    restore = args.restore_links or args.notebook_output is not None
    if restore and restored_path == source_path:
        parser.error('Restored notebook must not overwrite the source notebook')
    if restore and restored_path.suffix != '.ipynb':
        parser.error('Restored notebook must have .ipynb extension')

    nb = json.loads(source_path.read_text(encoding='utf-8'))
    image_dir.mkdir(parents=True, exist_ok=True)
    n_attach = n_html = 0
    warnings = []

    def relative_url(path):
        return quote(path.relative_to(restored_path.parent).as_posix(), safe='/') if path.is_relative_to(restored_path.parent) else quote(__import__('os').path.relpath(path, restored_path.parent).replace('\\', '/'), safe='/')

    for cell_no, cell in enumerate(nb.get('cells', []), 1):
        if cell.get('cell_type') != 'markdown':
            continue
        source = cell.get('source', '')
        was_list = isinstance(source, list)
        content = ''.join(source) if was_list else source
        attachments = cell.get('attachments', {})
        links = {}
        successfully_restored = set()

        for attachment_name, representations in attachments.items():
            candidates = [(mime, value) for mime, value in representations.items() if mime.startswith('image/')]
            for mime, encoded in candidates:
                ext = image_extension(mime)
                if not ext:
                    warnings.append(f'Cell {cell_no}: unknown image format {mime}')
                    continue
                try:
                    data = base64.b64decode(''.join(encoded) if isinstance(encoded, list) else encoded, validate=True)
                except (ValueError, binascii.Error) as exc:
                    warnings.append(f'Cell {cell_no}: invalid attachment {attachment_name}: {exc}')
                    continue
                name = safe_name(attachment_name)
                if Path(name).suffix.lower() != ext.lower() and (not Path(name).suffix or len(candidates) > 1):
                    name += ext
                destination = unique_path(image_dir, name)
                destination.write_bytes(data)
                n_attach += 1
                print(f'[Attachment] {destination.name}')
                if attachment_name not in links:
                    links[attachment_name] = relative_url(destination)

        if restore:
            def replace_attachment(match):
                attachment_name = __import__('urllib.parse', fromlist=['unquote']).unquote(match.group(2))
                if attachment_name in links:
                    successfully_restored.add(attachment_name)
                    return match.group(1) + links[attachment_name] + match.group(3)
                return match.group(0)
            content = MD_ATTACHMENT.sub(replace_attachment, content)

        locator = ImgLocator(content)
        locator.feed(content)
        for start, end, uri in reversed(locator.spans):
            try:
                result = decode_data_uri(uri)
            except (ValueError, binascii.Error) as exc:
                warnings.append(f'Cell {cell_no}: invalid HTML data URI: {exc}')
                continue
            if result is None:
                continue
            mime, data = result
            ext = image_extension(mime)
            if not ext:
                warnings.append(f'Cell {cell_no}: unknown HTML image format {mime}')
                continue
            destination = unique_path(image_dir, f'cell_{cell_no:03d}_image{ext}')
            destination.write_bytes(data)
            n_html += 1
            print(f'[HTML]       {destination.name}')
            if restore:
                content = content[:start] + relative_url(destination) + content[end:]

        if restore:
            cell['source'] = content.splitlines(keepends=True) if was_list else content
            # Remove only attachments that were replaced in Markdown source.
            for name in successfully_restored:
                attachments.pop(name, None)
            if not attachments:
                cell.pop('attachments', None)

    if restore:
        restored_path.parent.mkdir(parents=True, exist_ok=True)
        restored_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'Restored notebook: {restored_path}')

    print(f'Attachments: {n_attach}; HTML images: {n_html}; folder: {image_dir}')
    for warning in warnings:
        print('WARNING:', warning)


if __name__ == '__main__':
    main()
