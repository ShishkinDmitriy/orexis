"""What the sensing tree's SHAPE promises, and the one direction its arrows may point.

Sensing is the belief revision seam and BENEATH the mind: the planner reads the predictions
it writes and the executor the readings, both by kind, and neither imports a line of it; it
imports nothing of theirs and speaks none of their words. A layer that reached up would be no
layer. And, as in `planning/`, a module named for an act exports that act alone and every
public function has a test named for it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SENSING = ROOT / "agent" / "sensing"
FILES = sorted(p for p in SENSING.rglob("*.py") if "__pycache__" not in str(p))
VOCABULARY = sorted(SENSING.rglob("*.ttl"))

#  A MODULE NAMED FOR A THING, which may export several reads of it.
NOUNS = {"ontology"}


def test_the_layer_imports_nothing_of_the_mind():
    assert FILES, "the glob stopped matching"
    reaching = []
    for p in FILES:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            names = [a.name for a in getattr(n, "names", [])] if isinstance(n, ast.Import) else []
            if any(w in mod for w in ("planning", "execution")) or any("planning" in a or "execution" in a for a in names):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, f"sensing imports the mind at {reaching}"


@pytest.mark.parametrize("path", FILES + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_layer_speaks_the_minds_words(path):
    said = re.findall(r"\b(?:planning|execution):\w+", path.read_text())
    assert not said, f"{path.name} names the mind's words: {sorted(set(said))}"


def test_the_mind_imports_nothing_of_sensing():
    """The planner reads predictions and the executor readings, by KIND: a graph classified
    `orexis:PredictionGraph` or `orexis:StateGraph` is theirs to read whoever wrote it."""
    for path in sorted((ROOT / "agent").rglob("*.py")):
        if SENSING in path.parents or "tests" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            mod = (node.module if isinstance(node, ast.ImportFrom) else None) or ""
            assert "agent.sensing" not in mod, f"{path.relative_to(ROOT)} imports sensing"
            if isinstance(node, ast.Import):
                assert not any(a.name.startswith("agent.sensing") for a in node.names), path


def test_a_module_named_for_an_act_exports_that_act_and_nothing_else():
    for path in sorted(SENSING.glob("*.py")):
        if path.stem in NOUNS or path.stem == "__init__":
            continue
        tree = ast.parse(path.read_text())
        public = sorted(n.name for n in tree.body
                        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"))
        assert public == [path.stem], f"{path.name} exports {public}"


def test_every_module_with_a_public_function_has_a_test_named_for_it():
    for path in sorted(SENSING.glob("*.py")):
        if path.stem in ("__init__", "ontology"):
            continue
        tree = ast.parse(path.read_text())
        if not any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_") for n in tree.body):
            continue
        assert (SENSING / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"


def test_the_package_says_it_is_one():
    assert (SENSING / "__init__.py").exists()
    assert not (ROOT / "agent" / "__init__.py").exists(), "agent/ is a namespace portion"
