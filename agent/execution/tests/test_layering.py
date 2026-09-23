"""The arrow between the two layers, held in the only direction it may point.

Execution is BENEATH planning: a plan is found above and carried out below. So planning may
import execution's contract — one ordinary downward import — and execution may import nothing
of planning's, because a layer that reaches up is not a layer.

**AND THE VOCABULARY IS THE OTHER HALF OF IT**, which an import scan cannot see. A prefix
resolves through `store.NAMESPACES`, built by reading every `*.ttl` in the tree, so a file can
speak `planning:` without importing a line of planning and nothing would notice. Naming a
higher layer's words is the same dependency as importing them: it is a claim about what that
layer calls things, and it rots the day that layer renames one.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

EXECUTION = Path(__file__).resolve().parents[1]
FILES = sorted(p for p in EXECUTION.rglob("*.py") if "__pycache__" not in str(p))
VOCABULARY = sorted(EXECUTION.rglob("*.ttl"))


def test_the_execution_layer_imports_nothing_of_planning():
    """Upward is not a direction. `publish_plan` handing a plan DOWN to the executor is the one
    arrow between them, and it points the other way."""
    assert FILES, "the glob stopped matching, which would pass this by running it on nothing"
    reaching = []
    for p in FILES:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            names = [a.name for a in getattr(n, "names", [])] if isinstance(n, ast.Import) else []
            if "planning" in mod or any("planning" in a for a in names):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, f"execution imports planning at {reaching}"


@pytest.mark.parametrize("path", FILES + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_layer_speaks_a_higher_layers_words(path):
    """A prefix costs no import, which is exactly why it needs saying out loud. `planning:` in
    a docstring here was the one instance when this was written — a sentence explaining what
    this layer deliberately does NOT read, which is still a spelling that rots when the layer
    above renames a term."""
    said = re.findall(r"\bplanning:\w+", path.read_text())
    assert not said, f"{path.name} names planning's words: {sorted(set(said))}"
