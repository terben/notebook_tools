# Jupyter Notebook Tools

## Motivation

When preparing Jupyter notebooks for teaching, I often need to create student-facing versions of my teaching materials. In particular, I want to:

- **Remove cell outputs** before distributing notebooks, so students receive clean notebooks without results from previous executions.
- **Remove solutions** from exercise notebooks while keeping them in the original notebooks used to prepare the course.
- **Embed images directly into notebooks** so students can open them without having to manage additional image files.

I originally wrote a few small scripts to automate these recurring tasks. Over time, they evolved into a collection of four command-line utilities.

The tools are intentionally simple, independent, and designed to be combined in different workflows.

## The Tools

The collection currently consists of four small command-line utilities:

| Tool | Purpose |
| --- | --- |
| `clear_output_notebook.sh` | Clear all cell outputs, **in place** |
| `create_student_notebook.py` | Remove solution cells from an exercise notebook |
| `embed_images.py` | Embed local images referenced in Markdown cells |
| `extract_images.py` | Extract embedded images to files, optionally restoring local image links |

Each tool is a standalone script with no dependencies on the other tools. You can use them individually, combine them in shell pipelines, or adapt them to your own teaching workflow.

## Prerequisites

- Python 3.9 or later
- [`nbformat`](https://pypi.org/project/nbformat/) for the Python tools
- `jupyter nbconvert` and Bash for `clear_output_notebook.sh`

```sh
pip install nbformat nbconvert
```

## Installation

Clone the repository and put the scripts on your `PATH`, or call them by path:

```sh
git clone <repository-url> notebook_tools
export PATH="$PWD/notebook_tools:$PATH"
```

## Conventions

- The input notebook is a positional argument; `-h`/`--help` shows usage.
- `-o`/`--output` names the output notebook. Without it, the Python tools
  write a new file next to the input (`NAME_student.ipynb`,
  `NAME_embedded.ipynb`, `NAME_restored.ipynb`).
- Source notebooks are never modified, except by `clear_output_notebook.sh`,
  which works in place by design.
- `create_student_notebook.py` and `embed_images.py` accept `-` as input or
  output to read from stdin or write to stdout.
- Status messages and warnings go to stderr.

## Usage

### clear_output_notebook.sh

```sh
clear_output_notebook.sh lecture.ipynb               # clear in place
clear_output_notebook.sh -b lecture.ipynb            # keep lecture.ipynb.bak
clear_output_notebook.sh exercises/*.ipynb           # several notebooks
```

### create_student_notebook.py

Removes every cell (code or Markdown) whose source starts with `## SOLUTION`
or `!! SOLUTION`. The mark must be at the very beginning of the cell.

```sh
create_student_notebook.py sheet01.ipynb                     # -> sheet01_student.ipynb
create_student_notebook.py sheet01.ipynb -o student/sheet01.ipynb
```

### embed_images.py

Embeds local images so that the notebook is self-contained:

- Markdown images `![alt](figures/plot.png)` become cell attachments,
  `![alt](attachment:plot.png)`.
- HTML images `<img src="figures/plot.png" width="300">` get a base64 data
  URI as `src`, so that HTML attributes such as `width` keep working.

Paths are resolved relative to the notebook's directory. Both
`![alt](<my plot.png>)` and `![alt](my%20plot.png)` work, as do titles in
double or single quotes (`![alt](plot.png "Title")`). Remote URLs, data URIs and existing attachments are left untouched.
References to missing local files produce a warning and are left unchanged.

```sh
embed_images.py lecture.ipynb                        # -> lecture_embedded.ipynb
embed_images.py lecture.ipynb -o handout.ipynb
```

### extract_images.py

Writes attachments and HTML data-URI images of Markdown cells to image files.
With `-r` or `-o`, it also writes a restored notebook in which the extracted
images are referenced by links relative to the restored notebook (URL-encoded,
e.g. `my%20images/plot.png`), so the image directory and the restored notebook
may be in different directories. Without `-r` or `-o`, no notebook is written.

```sh
extract_images.py lecture_embedded.ipynb             # images -> lecture_embedded_images/
extract_images.py lecture_embedded.ipynb -d figures  # images -> figures/
extract_images.py lecture_embedded.ipynb -r          # also lecture_restored.ipynb
extract_images.py lecture_embedded.ipynb -d figures -o lecture.ipynb
```

Attachments keep their names; HTML images are named `cell_NNN_image.EXT`.
Attachments that are not referenced in their cell's Markdown are extracted
but kept in the restored notebook. Existing files are never overwritten: name clashes get a
numeric suffix (`image_1.png`), which also happens when you run the tool twice
on the same image directory.

## Examples

[`examples/README.md`](examples/README.md) walks through all four tools with
a small exercise notebook included in the repository.

## Example workflows

Publish a self-contained student version of an exercise sheet. When reading
from stdin, `embed_images.py` resolves image paths relative to the current
directory, so run the pipeline from the notebook's directory:

```sh
create_student_notebook.py sheet01.ipynb -o - | embed_images.py - -o sheet01_student.ipynb
clear_output_notebook.sh sheet01_student.ipynb
```

Edit the images of a notebook you received with embedded images, then
re-embed them:

```sh
extract_images.py received.ipynb -d figures -o work.ipynb
# ... edit figures/*.png, work on work.ipynb ...
embed_images.py work.ipynb -o final.ipynb
```

## Limitations

- Only images in Markdown cells are handled; images in code cell outputs are
  neither embedded nor extracted.
- Image references are found with simple regular expressions, not a full
  Markdown or HTML parser. Not supported: reference-style Markdown images
  (`![alt][ref]`), titles in parentheses (`![alt](x.png (Title))`), alt text
  containing `]`, paths containing `)` unless written as `<path>`, unquoted
  HTML `src` attributes, and data URIs containing line breaks.
- Image references inside Markdown code blocks are treated like any others.
- Markdown images with data URIs (`![alt](data:...)`) are not extracted.
- Images are recognized by file extension (`mimetypes`), not by content.
- Spaces in attachment names are replaced by underscores, because a Markdown
  link target must not contain unescaped spaces.
- Embedding and extracting is not a byte-for-byte round trip: attachment and
  file names may change (the same image used in two cells is extracted twice,
  e.g. as `plot.png` and `plot_1.png`), and the notebook JSON is rewritten by
  `nbformat`.
- `create_student_notebook.py` only removes whole cells; it does not parse
  partial solutions inside cells.

## Tests

```sh
python3 -m unittest discover tests
```

The output-clearing test is skipped if `jupyter` is not installed.

## License

MIT, see [LICENSE](LICENSE).

## Development note

### AI assistance

The original versions of these scripts were written by the
author. ChatGPT (OpenAI) and Claude Code (Anthropic) were subsequently
used to review and refactor the code, improve robustness and
consistency, and assist with documentation and testing.

The author reviewed the resulting changes and remains responsible for
the published code.
