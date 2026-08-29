#!/usr/bin/env bash
# Render every diagram source to SVG and stamp it with the source's hash.
#
# The stamp is what makes a committed image safe: `tests/test_knowledge.py` compares it to the
# hash of the `.puml` beside it, so an edited source with a stale picture FAILS — and the check
# needs no renderer, which is why it runs on a fresh clone. Rendering needs plantuml; checking
# does not.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v plantuml >/dev/null || { echo "plantuml not found — see knowledge/diagrams/index.md"; exit 1; }
for src in knowledge/diagrams/*.puml; do
  plantuml -tsvg -o . "$src"
  svg="${src%.puml}.svg"
  printf '<!-- source-sha256: %s -->\n' "$(sha256sum "$src" | cut -c1-64)" >> "$svg"
  echo "rendered $svg"
done
