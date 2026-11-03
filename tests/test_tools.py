"""Integration tests for the notebook utilities.

Run from the repository root:  python3 -m unittest discover tests
"""
import base64
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook, new_output

ROOT = Path(__file__).resolve().parent.parent
# 1x1 transparent PNG
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'


def run(*args, **kwargs):
    return subprocess.run(args, cwd=kwargs.pop('cwd', None), check=True,
                          capture_output=True, text=True, **kwargs)


class NotebookToolsTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)

    def write_nb(self, name, cells):
        path = self.dir / name
        nbformat.write(new_notebook(cells=cells), path)
        return path

    def test_clear_output(self):
        if shutil.which('jupyter') is None:
            self.skipTest('jupyter not installed')
        cell = new_code_cell('print(1)', execution_count=1,
                             outputs=[new_output('stream', name='stdout', text='1\n')])
        nb_path = self.write_nb('nb.ipynb', [cell, new_markdown_cell('Text')])
        run(ROOT / 'clear_output_notebook.sh', '--backup', nb_path)

        nb = nbformat.read(nb_path, as_version=4)
        self.assertEqual(nb.cells[0].outputs, [])
        self.assertIsNone(nb.cells[0].execution_count)
        self.assertEqual(nb.cells[0].source, 'print(1)')
        self.assertEqual(nb.cells[1].source, 'Text')
        backup = nbformat.read(str(nb_path) + '.bak', as_version=4)
        self.assertEqual(len(backup.cells[0].outputs), 1)

    def test_student_notebook(self):
        nb_path = self.write_nb('sheet.ipynb', [
            new_markdown_cell('# Exercise 1'),
            new_code_cell('## SOLUTION\nx = 42'),
            new_markdown_cell('!! SOLUTION\nThe answer is 42.'),
            new_code_cell('x = ...  # your code'),
            new_markdown_cell('Not a ## SOLUTION cell'),
        ])
        run(sys.executable, ROOT / 'create_student_notebook.py', nb_path)

        nb = nbformat.read(self.dir / 'sheet_student.ipynb', as_version=4)
        self.assertEqual([c.source for c in nb.cells],
                         ['# Exercise 1', 'x = ...  # your code', 'Not a ## SOLUTION cell'])
        self.assertEqual(len(nbformat.read(nb_path, as_version=4).cells), 5)

        # stdin/stdout
        out = run(sys.executable, ROOT / 'create_student_notebook.py', '-', '-o', '-',
                  input=nb_path.read_text()).stdout
        self.assertEqual(len(nbformat.reads(out, as_version=4).cells), 3)

    def test_embed_extract_restore(self):
        (self.dir / 'img').mkdir()
        (self.dir / 'img' / 'dot.png').write_bytes(PNG)
        (self.dir / 'my figure.svg').write_bytes(SVG)
        code = new_code_cell('1 + 1', execution_count=1,
                             outputs=[new_output('execute_result', {'text/plain': '2'}, execution_count=1)])
        md = ('Intro\n'
              '![dot](img/dot.png "A dot")\n'
              '![again](img/dot.png)\n'
              '![spaces](<my figure.svg>)\n'
              '<img src="img/dot.png" width="50">\n'
              '<img src=\'my%20figure.svg\'>\n'
              '![remote](https://example.org/x.png)\n'
              '![missing](nope.png)\n')
        # A second cell gets an attachment with the same name.
        nb_path = self.write_nb('lecture.ipynb', [code, new_markdown_cell(md),
                                                  new_markdown_cell('![dot](img/dot.png)')])
        original = nb_path.read_bytes()

        # embed
        result = run(sys.executable, ROOT / 'embed_images.py', nb_path)
        self.assertIn('Embedded 4 Markdown and 2 HTML image(s)', result.stderr)
        self.assertIn('nope.png', result.stderr)
        self.assertEqual(nb_path.read_bytes(), original)
        embedded_path = self.dir / 'lecture_embedded.ipynb'
        nb = nbformat.read(embedded_path, as_version=4)
        self.assertEqual(nb.cells[0], nbformat.read(nb_path, as_version=4).cells[0])
        cell = nb.cells[1]
        self.assertEqual(set(cell.attachments), {'dot.png', 'my_figure.svg'})
        self.assertIn('![dot](attachment:dot.png "A dot")', cell.source)
        self.assertIn('![again](attachment:dot.png)', cell.source)
        self.assertIn('![spaces](attachment:my_figure.svg)', cell.source)
        self.assertIn('<img src="data:image/png;base64,', cell.source)
        self.assertIn("<img src='data:image/svg+xml;base64,", cell.source)
        self.assertIn('![remote](https://example.org/x.png)', cell.source)
        self.assertIn('![missing](nope.png)', cell.source)

        # extract only: source notebook unchanged, no restored notebook
        embedded = embedded_path.read_bytes()
        run(sys.executable, ROOT / 'extract_images.py', embedded_path, '-d', self.dir / 'only')
        self.assertEqual(embedded_path.read_bytes(), embedded)
        self.assertFalse((self.dir / 'lecture_restored.ipynb').exists())
        files = sorted(p.name for p in (self.dir / 'only').iterdir())
        self.assertEqual(files, ['cell_002_image.png', 'cell_002_image.svg',
                                 'dot.png', 'dot_1.png', 'my_figure.svg'])
        self.assertEqual((self.dir / 'only' / 'dot.png').read_bytes(), PNG)
        self.assertEqual((self.dir / 'only' / 'cell_002_image.svg').read_bytes(), SVG)

        # extract and restore, with relative paths and the image directory
        # (containing a space) and the restored notebook in different directories
        restored_path = self.dir / 'out' / 'restored.ipynb'
        run(sys.executable, ROOT / 'extract_images.py', 'lecture_embedded.ipynb',
            '-d', 'my images', '-o', 'out/restored.ipynb', cwd=self.dir)
        nb = nbformat.read(restored_path, as_version=4)
        cell = nb.cells[1]
        self.assertNotIn('attachments', cell)
        self.assertNotIn('data:', cell.source)
        self.assertIn('![dot](../my%20images/dot.png "A dot")', cell.source)
        self.assertIn('![spaces](../my%20images/my_figure.svg)', cell.source)
        self.assertIn('<img src="../my%20images/cell_002_image.png" width="50">', cell.source)
        self.assertEqual(nb.cells[2].source, '![dot](../my%20images/dot_1.png)')
        self.assertEqual(nb.cells[0].outputs[0].data['text/plain'], '2')

        # re-embedding the restored notebook gives the same images again
        reembedded_path = self.dir / 'again.ipynb'
        run(sys.executable, ROOT / 'embed_images.py', restored_path, '-o', reembedded_path)
        before = nbformat.read(embedded_path, as_version=4).cells[1]
        after = nbformat.read(reembedded_path, as_version=4).cells[1]
        self.assertEqual(after.source, before.source)
        self.assertEqual(after.attachments, before.attachments)


if __name__ == '__main__':
    unittest.main()
