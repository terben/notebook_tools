import sys
import nbformat

# script to remove solutions from an exercise-sheet
# notebook and to vreate a student version

CODE_SOLUTION_MARK = '## SOLUTION'
MARKDOWN_SOLUTION_MARK = '!! SOLUTION'

is_solution = lambda cell: cell.source.startswith(CODE_SOLUTION_MARK) or \
                           cell.source.startswith(MARKDOWN_SOLUTION_MARK)

nb_file = sys.argv[1]
student_nb_file = sys.argv[2]

nb = nbformat.read(nb_file, as_version=4)

# delete all cells that do not belong to the solution
nb.cells = [ cell for cell in nb.cells if not is_solution(cell) ]

nbformat.write(nb, student_nb_file)
