"""What the coordination package's SHAPE promises.

Coordination sits above planning, execution and speech and meets them at the store: it imports none of their
code — what it says goes through speech's part, linked at start — speaks no domain's words, since a resource is
a value of any constraint's key and the draw is a domain a world imports, and, as in every package here, a
module named for an act exports that act alone and has a test named for it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
COORDINATION = ROOT / "agent" / "coordination"
FILES = sorted(COORDINATION.glob("*.py"))
VOCABULARY = sorted(COORDINATION.glob("*.ttl"))
PACKAGES = ("planning", "execution", "speech", "belief", "sensing", "prediction", "transport")


def test_the_package_imports_no_other_packages_code():
    assert FILES, "the glob stopped matching"
    reaching = []
    for p in FILES:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            if any(mod.startswith(f"agent.{w}") for w in PACKAGES):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, f"the coordination package imports another package's code at {reaching}"


@pytest.mark.parametrize("path", FILES + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_package_speaks_a_domains_words(path):
    said = re.findall(r"\b(?:courier|draw|market|climate|actuation|road):\w+", path.read_text())
    assert not said, f"{path.name} names a domain's words: {sorted(set(said))}"


def test_a_module_named_for_an_act_exports_that_act_and_has_a_test_named_for_it():
    acts = [p for p in FILES if p.stem not in ("__init__", "events", "ontology")]  # things, not acts: what coordination says, its words
    assert acts, "the glob stopped matching"
    for path in acts:
        tree = ast.parse(path.read_text())
        public = sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"))
        assert public == [path.stem], f"{path.name} exports {public}"
        assert (COORDINATION / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"
