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

## Quick reference

All four tools take a Jupyter notebook as their first argument. Use `-h` or `--help` for the full command-line options.

| Tool | Example |
| --- | --- |
| `clear_output_notebook.sh` | `clear_output_notebook.sh -b lecture.ipynb` |
| `create_student_notebook.py` | `create_student_notebook.py exercise.ipynb` |
| `embed_images.py` | `embed_images.py lecture.ipynb` |
| `extract_images.py` | `extract_images.py lecture_embedded.ipynb -r` |

Some important conventions:

- `clear_output_notebook.sh` modifies notebooks **in place**. Use `-b` to create a backup.
- `create_student_notebook.py` removes cells starting with `## SOLUTION` or `!! SOLUTION`.
- `embed_images.py` converts local Markdown images into notebook attachments and HTML images into data URIs. Image paths are resolved relative to the input notebook.
- `extract_images.py` writes embedded images to files. With `-r` or `-o`, it also creates a notebook with local image links.
- For the Python tools, `-o` specifies the output notebook. Input notebooks are not modified by default.
- `create_student_notebook.py` and `embed_images.py` support `-` for stdin/stdout, making shell pipelines possible.

Status messages and warnings are written to stderr.

## Examples

The [examples directory](examples/README.md) contains a small teaching notebook with exercises, solutions, saved outputs and local images.

Its step-by-step guide demonstrates how to:

1. Embed local images into a self-contained notebook.
2. Remove solution cells to create a student version.
3. Clear saved cell outputs.
4. Extract embedded images and restore local image links.

All generated files are kept separate from the original example notebook.


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
