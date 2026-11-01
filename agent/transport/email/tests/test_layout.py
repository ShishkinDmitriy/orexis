"""What the email transport's SHAPE promises: a member of the family, importing the family's `Transport` contract and
the store and nothing of the mind, of sensing, of speech or of translation, whom it meets only by the `prose` it says
and the `say_to` it answers; speaking no other package's words; and every module with a test named for it."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
HERE = ROOT / "agent" / "transport" / "email"
CODE = sorted(HERE.glob("*.py"))
VOCABULARY = sorted(HERE.glob("*.ttl"))
ABOVE = ("planning", "prediction", "execution", "belief", "sensing", "speech", "translation", "coordination", "mqtt", "http")


def test_the_transport_imports_only_downward():
    assert CODE, "the glob stopped matching"
    reaching = []
    for p in CODE:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            if any(w in mod.split(".") for w in ABOVE):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, reaching


@pytest.mark.parametrize("path", CODE, ids=lambda p: p.name)
def test_no_code_of_this_package_speaks_another_packages_words(path):
    said = re.findall(r"\b(?:planning|prediction|execution|belief|sensing|translation|mqtt4ssn):\w+", path.read_text())
    assert not said, f"{path.name} names another package's words: {sorted(set(said))}"


def test_every_module_has_a_test_named_for_it():
    for path in CODE:
        if path.stem != "__init__":
            assert (HERE / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"
