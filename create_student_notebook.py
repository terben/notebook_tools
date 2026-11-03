#!/usr/bin/env python3
"""Create a student version of an exercise notebook by removing solution cells.

A cell is a solution cell if its source starts with '## SOLUTION' or
'!! SOLUTION'. Both marks work in code and Markdown cells ('## SOLUTION' is a
comment in Python code; in Markdown it renders as a heading). Use '-' as
NOTEBOOK or OUTPUT to read from stdin or write to stdout.
"""
import argparse
import sys
from pathlib import Path

import nbformat

SOLUTION_MARKS = ('## SOLUTION', '!! SOLUTION')


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('notebook', help='notebook with solutions')
    parser.add_argument('-o', '--output',
                        help='output notebook (default: NOTEBOOK_student.ipynb)')
    args = parser.parse_args()

    output = args.output
    if output is None:
        if args.notebook == '-':
            parser.error('-o/--output is required when reading from stdin')
        output = Path(args.notebook).with_name(Path(args.notebook).stem + '_student.ipynb')

    nb = nbformat.read(sys.stdin if args.notebook == '-' else args.notebook, as_version=4)
    n_cells = len(nb.cells)
    nb.cells = [cell for cell in nb.cells if not cell.source.startswith(SOLUTION_MARKS)]
    nbformat.write(nb, sys.stdout if output == '-' else output)

    print(f'Removed {n_cells - len(nb.cells)} solution cell(s); wrote {"stdout" if output == "-" else output}',
          file=sys.stderr)


if __name__ == '__main__':
    main()
