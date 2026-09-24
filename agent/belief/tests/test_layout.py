"""What the belief package's SHAPE promises.

The belief package is the kernel's: sensing, planning and execution may import it downward,
and it imports nothing of theirs and speaks none of their words — a layer that reached up
would be no layer. As in `planning/` and `sensing/`, a module named for an act exports that act
alone, every public function has a test named for it, and `agent/` stays a namespace portion.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BELIEF = ROOT / "agent" / "belief"
FILES = sorted(p for p in BELIEF.rglob("*.py") if "__pycache__" not in str(p))
VOCABULARY = sorted(BELIEF.rglob("*.ttl"))

#  A MODULE NAMED FOR A THING, which may export several reads of it.
NOUNS = {"ontology", "deliberator"}

def test_the_package_imports_nothing_above_it():
    assert FILES, "the glob stopped matching"
    reaching = []
    for p in FILES:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            names = [a.name for a in getattr(n, "names", [])] if isinstance(n, ast.Import) else []
            if any(w in mod for w in ("planning", "execution", "sensing")) \
                    or any(any(w in a for w in ("planning", "execution", "sensing")) for a in names):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, f"the belief package imports a layer above it at {reaching}"


@pytest.mark.parametrize("path", FILES + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_package_speaks_a_higher_layers_words(path):
    said = re.findall(r"\b(?:planning|execution|sensing):\w+", path.read_text())
    assert not said, f"{path.name} names a higher layer's words: {sorted(set(said))}"


def test_a_module_named_for_an_act_exports_that_act_and_nothing_else():
    for path in sorted(BELIEF.glob("*.py")):
        if path.stem in NOUNS or path.stem == "__init__":
            continue
        tree = ast.parse(path.read_text())
        public = sorted(n.name for n in tree.body
                        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"))
        assert public == [path.stem], f"{path.name} exports {public}"


def test_every_module_with_a_public_function_has_a_test_named_for_it():
    for path in sorted(BELIEF.glob("*.py")):
        if path.stem in ("__init__", "ontology"):
            continue
        tree = ast.parse(path.read_text())
        if not any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_") for n in tree.body):
            continue
        assert (BELIEF / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"


def test_the_package_says_it_is_one():
    assert (BELIEF / "__init__.py").exists()
    assert not (ROOT / "agent" / "__init__.py").exists(), "agent/ is a namespace portion"
