"""What the transport tree's SHAPE promises, and the one direction its arrows may point.

The HTTP transport is a member of a family: it imports the family's `Transport` contract, kept at
`agent/transport/`, calls sensing's `received` and reads its `cadence_of`, the downward imports a member is allowed,
and nothing else of sensing, nor of the mind, of prediction or of the belief package; nothing
above imports it, since the container hands it a client and calls it. It declares no word of its own — every `td:` and `hctl:` word
it speaks is one the vendored Thing Description declares — and speaks no other package's words.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import rdflib

ROOT = Path(__file__).resolve().parents[4]
HTTP = ROOT / "agent" / "transport" / "http"
CODE = sorted(p for p in HTTP.glob("*.py"))
VOCABULARY = sorted(HTTP.glob("*.ttl"))
VENDORED_TD = ROOT / "tests" / "fixtures" / "vocabularies" / "wot-td.ttl"
VENDORED_HCTL = ROOT / "tests" / "fixtures" / "vocabularies" / "wot-hctl.ttl"

#  A MODULE NAMED FOR A THING, which may hold a class and several reads of it.
NOUNS = {"driver"}

ABOVE = ("planning", "prediction", "execution", "belief")


def test_the_transport_imports_only_downward():
    assert CODE, "the glob stopped matching"
    reaching = []
    for p in CODE:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            names = [a.name for a in getattr(n, "names", [])] if isinstance(n, ast.Import) else []
            if any(w in mod for w in ABOVE) or any(any(w in a for w in ABOVE) for a in names):
                reaching.append(f"{p.name}:{n.lineno}")
            if mod.startswith("agent.sensing") and mod not in ("agent.sensing.received", "agent.sensing.cadence"):
                reaching.append(f"{p.name}:{n.lineno} reaches into sensing past its callback")
    assert not reaching, reaching


@pytest.mark.parametrize("path", CODE + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_package_speaks_another_packages_words(path):
    said = re.findall(r"\b(?:planning|prediction|execution|belief|sensing):\w+", path.read_text())
    assert not said, f"{path.name} names another package's words: {sorted(set(said))}"


def test_nothing_above_imports_the_transport():
    for path in sorted((ROOT / "agent").rglob("*.py")):
        if (ROOT / "agent" / "transport") in path.parents or "tests" in path.parts or path == ROOT / "agent" / "runtime.py":
            continue                  # the family's own members, and the container, which assembles every layer
        for node in ast.walk(ast.parse(path.read_text())):
            mod = (node.module if isinstance(node, ast.ImportFrom) else None) or ""
            assert "agent.transport" not in mod, f"{path.relative_to(ROOT)} imports the transport"
            if isinstance(node, ast.Import):
                assert not any(a.name.startswith("agent.transport") for a in node.names), path


def test_a_module_named_for_an_act_exports_that_act_and_nothing_else():
    """Every module here is a noun today, so the act loop below walks nothing; the nouns are
    asserted to exist so that this test asserts something whatever the tree holds (#106)."""
    assert {p.stem for p in CODE} >= NOUNS, "a listed noun has no module"
    for path in CODE:
        if path.stem in NOUNS or path.stem == "__init__":
            continue
        tree = ast.parse(path.read_text())
        public = sorted(n.name for n in tree.body
                        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_"))
        assert public == [path.stem], f"{path.name} exports {public}"


def test_every_module_with_a_public_name_has_a_test_named_for_it():
    for path in CODE:
        if path.stem in ("__init__", "ontology"):
            continue
        tree = ast.parse(path.read_text())
        if not any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_") for n in tree.body):
            continue
        assert (HTTP / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"


def test_the_package_declares_nothing_and_every_word_it_speaks_is_the_thing_descriptions():
    """The ontology names the Thing Description's two namespaces and declares no term; every `td:`
    and `hctl:` word in the code, a test or a world is one the vendored vocabularies declare."""
    own = (HTTP / "ontology.ttl").read_text()
    assert "@prefix td: <https://www.w3.org/2019/wot/td#> ." in own
    assert "@prefix hctl: <https://www.w3.org/2019/wot/hypermedia#> ." in own
    assert not re.search(r"^:\w+ a ", own, re.M), "the transport declares a word of its own"
    undeclared = {}
    for prefix, ns, vendored in (("td", "https://www.w3.org/2019/wot/td#", VENDORED_TD),
                                 ("hctl", "https://www.w3.org/2019/wot/hypermedia#", VENDORED_HCTL)):
        vocabulary = rdflib.Graph(); vocabulary.parse(vendored, format="turtle")
        declared = {str(s)[len(ns):] for s in vocabulary.subjects() if isinstance(s, rdflib.URIRef) and str(s).startswith(ns)}
        assert declared, f"the vendored {prefix} vocabulary declares nothing"
        for path in sorted(p for p in HTTP.rglob("*") if p.suffix in (".py", ".ttl", ".trig")):
            for word in re.findall(rf"\b{prefix}:(\w+)", path.read_text()):
                if word not in declared:
                    undeclared.setdefault(f"{prefix}:{word}", set()).add(path.name)
    assert not undeclared, f"spoken and not declared by the Thing Description: {undeclared}"


def test_the_package_says_it_is_one():
    assert (HTTP / "__init__.py").exists()
    assert not (ROOT / "agent" / "__init__.py").exists() and not (ROOT / "agent" / "transport" / "__init__.py").exists(), \
        "agent/ and agent/transport/ are namespace portions"
