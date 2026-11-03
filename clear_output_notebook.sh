#!/usr/bin/env bash
# Clear all cell outputs of Jupyter notebooks in place using jupyter nbconvert.

set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") [-b] NOTEBOOK...

Clear all cell outputs of the given notebooks in place.

Options:
  -b, --backup  copy each notebook to NOTEBOOK.bak before clearing it
  -h, --help    show this help message and exit
EOF
}

backup=false
while [ $# -gt 0 ]; do
  case "$1" in
    -b|--backup) backup=true; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) echo "error: unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) break ;;
  esac
done

if [ $# -eq 0 ]; then
  usage >&2
  exit 2
fi

if [ "$backup" = true ]; then
  for nb in "$@"; do
    cp -- "$nb" "$nb.bak"
  done
fi

jupyter nbconvert --clear-output --inplace -- "$@"
