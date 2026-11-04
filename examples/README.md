# Examples

A small exercise notebook to try the four tools without preparing your own
material:

- `exercise.ipynb`: teacher version of a short exercise ("sums of squares")
  with a saved output, a code solution cell (`## SOLUTION`), a Markdown
  explanation cell (`!! SOLUTION`), a Markdown image and an HTML `<img>` with
  a `width` attribute.
- `images/squares.png`, `images/loop.svg`: the local images it refers to.

Run all commands from the repository root. All generated files are written to
`examples/generated/`, which is kept empty in the repository (except for
`.gitkeep`) and ignored by Git. You can delete its contents at any time.
`exercise.ipynb` itself is never modified.

Steps 1–3 build a self-contained student version (images embedded, no
solutions, no outputs); step 4 extracts the images again.

## 1. Embed the images

```sh
./embed_images.py examples/exercise.ipynb -o examples/generated/exercise_embedded.ipynb
```

Generated: `examples/generated/exercise_embedded.ipynb`, which no longer needs
the `images/` directory. The Markdown image becomes a cell attachment
(`![...](attachment:squares.png)`); the HTML image gets a base64 data URI as
`src`, so `width="400"` keeps working.

Embedding comes first because image paths are resolved relative to the input
notebook: a notebook already written to `examples/generated/` would not find
`images/`.

## 2. Create a student version

```sh
./create_student_notebook.py examples/generated/exercise_embedded.ipynb -o examples/generated/exercise_student.ipynb
```

Generated: `examples/generated/exercise_student.ipynb`. It has 4 cells instead
of 6: the code cell starting with `## SOLUTION` and the Markdown cell starting
with `!! SOLUTION` are removed. Introduction, task, images and the empty
exercise cell are unchanged; the saved output of the first code cell is still
there (see step 3).

## 3. Clear saved outputs

`clear_output_notebook.sh` works **in place**, so apply it to a generated
copy, not to `exercise.ipynb`:

```sh
./clear_output_notebook.sh examples/generated/exercise_student.ipynb
```

Afterwards the code cells of `examples/generated/exercise_student.ipynb` have
no outputs and no execution counts. Use `-b` to keep a `.bak` copy. The
notebook is now ready to hand out.

## 4. Extract images and restore local links

```sh
./extract_images.py examples/generated/exercise_embedded.ipynb -d examples/generated/images -o examples/generated/exercise_restored.ipynb
```

Generated: `examples/generated/images/squares.png` and
`examples/generated/images/cell_003_image.svg` (HTML images get generated
names, numbered by cell), plus `examples/generated/exercise_restored.ipynb`,
which links to these files again (`![...](images/squares.png)`,
`<img src="images/cell_003_image.svg" width="400" ...>`).
Running the command a second time adds files with a numeric suffix
(`squares_1.png`) instead of overwriting.

Without `-o` (or `-r`), only the images are extracted.
