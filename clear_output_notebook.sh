#!/bin/bash

# The script clears all output (from running cells) from a Notebook.
# The original notebook is replaced by the cleaned version.

# $1: Notebook to be cleaned
# $2: COPYFLAG (optional), If a second argument 'COPY'
#     is given, a copy of the notebook (appending .copy to
#     the name is created before cleaning the original is replaced.

if [ ${#} -gt 1 ] && [ ${2} = "COPY" ]
then
  cp "${1}" "${1}".copy
fi

jupyter nbconvert --clear-output --inplace "${1}"
