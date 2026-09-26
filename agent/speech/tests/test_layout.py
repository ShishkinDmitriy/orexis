"""What the speech package's SHAPE promises.

Speech is the translation row for a peer's word, beside sensing's for an instrument's: it imports
the store and the kernel's words and nothing of the layers above, speaks none of their words, and,
as in every package here, a module named for an act exports that act alone and has a test named
for it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEECH = ROOT / "agent" / "speech"
FILES = sorted(p for p in SPEECH.glob("*.py"))
ABOVE = ("planning", "execution", "belief", "sensing", "prediction", "transport")


def test_the_package_imports_nothing_above_it():
    assert FILES, "the glob stopped matching"
    reaching = []
    for p in FILES:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            if any(w in mod for w in ABOVE):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, f"the speech package imports a layer above it at {reaching}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_file_of_this_package_speaks_a_higher_layers_words(path):
    said = re.findall(r"\b(?:planning|execution|sensing|belief|market):\w+", path.read_text())
    assert not said, f"{path.name} names another package's words: {sorted(set(said))}"


def test_a_module_named_for_an_act_exports_that_act_and_has_a_test_named_for_it():
    acts = [p for p in FILES if p.stem != "__init__"]
    assert acts, "the glob stopped matching"
    for path in acts:
        tree = ast.parse(path.read_text())
        public = sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"))
        assert public == [path.stem], f"{path.name} exports {public}"
        assert (SPEECH / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"
