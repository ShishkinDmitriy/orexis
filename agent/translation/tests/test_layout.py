"""What the translation package's SHAPE promises.

Translation is the row for a person's prose, beside sensing's for an instrument's bytes and speech's for a peer's
document: it imports the store, the kernel's words and speech — the speaker it is beneath, whose `heard` keeps what a
person stated and whose `told` it renders — and nothing of the layers above, nor of any transport, which it meets
only by the `prose` a member says and the `say_to` it answers; it speaks none of their words, the account being the
selects each package ships beside its own ontology; and a module named for an act exports that act alone, and every
module has a test named for it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TRANSLATION = ROOT / "agent" / "translation"
FILES = sorted(TRANSLATION.glob("*.py"))
VOCABULARY = sorted(TRANSLATION.glob("*.ttl"))
ABOVE = ("planning", "execution", "belief", "sensing", "prediction", "coordination", "transport")
#  THINGS, NOT ACTS: the chats, the model, a sayable, and the part.
NOUNS = {"chat", "model", "sayable", "create"}


def test_the_package_imports_nothing_above_it_and_no_transport():
    assert FILES, "the glob stopped matching"
    reaching = []
    for p in FILES:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else []
            if any(w in mod for w in ABOVE) or any(any(w in a for w in ABOVE) for a in names):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, f"translation imports a layer above it or a transport at {reaching}"


@pytest.mark.parametrize("path", FILES + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_package_speaks_a_higher_layers_or_a_transports_words(path):
    said = re.findall(r"\b(?:planning|execution|sensing|belief|prediction|market|mqtt4ssn|telegram):\w+", path.read_text())
    assert not said, f"{path.name} names another package's words: {sorted(set(said))}"


def test_a_module_named_for_an_act_exports_that_act_and_every_module_has_a_test_named_for_it():
    modules = [p for p in FILES if p.stem not in ("__init__",)]
    assert {p.stem for p in modules} >= NOUNS | {"account"}, "a listed module is gone"
    for path in modules:
        if path.stem not in NOUNS:
            tree = ast.parse(path.read_text())
            public = sorted(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_"))
            assert public == [path.stem], f"{path.name} exports {public}"
        assert (TRANSLATION / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"


def test_every_package_that_gives_an_account_ships_one_select_titled_and_reading_kinds_it_declares():
    """An `account.rq` is beside the ontology of the package whose words it speaks, says its title and the kinds it
    reads, and speaks only that package's words and the vocabularies everyone shares."""
    from agent.store import NAMESPACES

    found = sorted((ROOT / "agent").glob("*/account.rq"))
    assert {p.parent.name for p in found} >= {"sensing", "execution"}, found
    for path in found:
        text, package = path.read_text(), path.parent.name
        lines = text.splitlines()
        assert lines[0].startswith("# ") and lines[1].startswith("# reads: "), f"{path}: a title, then the kinds it reads"
        for kind in lines[1].removeprefix("# reads: ").split(","):
            prefix, _, name = kind.strip().partition(":")
            ontology = (path.parent / "ontology.ttl").read_text()
            assert prefix == package and re.search(rf"^(?:{prefix})?:{name} a owl:Class", ontology, re.M), kind
        spoken = set(re.findall(r"\b([a-z][\w-]*):\w", re.sub(r"^#.*$", "", text, flags=re.M)))
        assert spoken <= {package, "sosa", "ssn", "orexis", "rdf", "rdfs", "xsd"} and spoken <= set(NAMESPACES), (path, spoken)
