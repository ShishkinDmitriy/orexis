"""What the transport tree's SHAPE promises, and the one direction its arrows may point.

The transport is a member of a family: it imports the family's `Transport` contract, kept at
`agent/transport/`, and calls sensing's `received`, the two downward imports a member is allowed,
and nothing else of sensing, nor of the mind, of prediction or of the belief package; nothing
above imports it, since the container hands it a client and calls it. It declares no word of its own — every `mqtt4ssn:` word
it speaks is one the vendored MQTT4SSN declares — and speaks no other package's words.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import rdflib

ROOT = Path(__file__).resolve().parents[4]
MQTT = ROOT / "agent" / "transport" / "mqtt"
CODE = sorted(p for p in MQTT.glob("*.py"))
VOCABULARY = sorted(MQTT.glob("*.ttl"))
VENDORED = ROOT / "tests" / "fixtures" / "vocabularies" / "mqtt4ssn.ttl"

#  A MODULE NAMED FOR A THING, which may hold a class and several reads of it.
NOUNS = {"ontology", "driver"}

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
            if mod.startswith("agent.sensing") and mod != "agent.sensing.received":
                reaching.append(f"{p.name}:{n.lineno} reaches into sensing past its callback")
    assert not reaching, reaching


@pytest.mark.parametrize("path", CODE + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_package_speaks_another_packages_words(path):
    said = re.findall(r"\b(?:planning|prediction|execution|belief|sensing):\w+", path.read_text())
    assert not said, f"{path.name} names another package's words: {sorted(set(said))}"


def test_nothing_above_imports_the_transport():
    for path in sorted((ROOT / "agent").rglob("*.py")):
        if MQTT in path.parents or "tests" in path.parts:
            continue
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
        assert (MQTT / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"


def test_the_package_declares_nothing_and_every_word_it_speaks_is_mqtt4ssns():
    """The ontology imports MQTT4SSN and declares no term; every `mqtt4ssn:` word in the code, a
    test or a world is one the vendored vocabulary declares."""
    own = (MQTT / "ontology.ttl").read_text()
    assert "owl:imports <https://www.w3id.org/MQTT4SSN-Ontology>" in own
    assert not re.search(r"^:\w+ a ", own, re.M), "the transport declares a word of its own"
    vocabulary = rdflib.Graph(); vocabulary.parse(VENDORED, format="turtle")
    ns = "https://www.w3id.org/MQTT4SSN-Ontology#"
    declared = {str(s)[len(ns):] for s in vocabulary.subjects() if isinstance(s, rdflib.URIRef) and str(s).startswith(ns)}
    assert declared, "the vendored vocabulary declares nothing"
    spoken = {}
    for path in sorted(p for p in MQTT.rglob("*") if p.suffix in (".py", ".ttl", ".trig")):
        for word in re.findall(r"\bmqtt4ssn:(\w+)", path.read_text()) + re.findall(r'MQTT4SSN \+ "(\w+)"', path.read_text()):
            spoken.setdefault(word, set()).add(path.name)
    undeclared = {w: sorted(where) for w, where in spoken.items() if w not in declared}
    assert not undeclared, f"spoken and not declared by MQTT4SSN: {undeclared}"


def test_the_package_says_it_is_one():
    assert (MQTT / "__init__.py").exists()
    assert not (ROOT / "agent" / "__init__.py").exists() and not (ROOT / "agent" / "transport" / "__init__.py").exists(), \
        "agent/ and agent/transport/ are namespace portions"
