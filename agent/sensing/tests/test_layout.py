"""What the sensing tree's SHAPE promises, and the one direction its arrows may point.

Sensing is the translation row and BENEATH the mind: the planner reads the predictions it
writes and the executor the observations, both by kind, and neither imports a line of it; it
imports nothing of theirs, nor of the belief package whose deliberator concludes over what it
writes, and speaks none of their words — and not one word of any transport, which is the
decoupling this layer exists for. A module named for an act exports that act alone, a module
named for a thing may answer several questions about it, and every public function has a test
named for it. A TEST here may import the belief package, to hold this layer's rules to what
they conclude; the code may not.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SENSING = ROOT / "agent" / "sensing"
CODE = sorted(p for p in SENSING.glob("*.py"))
VOCABULARY = sorted(SENSING.glob("*.ttl"))

#  A MODULE NAMED FOR A THING, which may export several reads of it.
NOUNS = {"ontology", "pipeline", "driver", "ranges"}

ABOVE = ("planning", "execution", "belief")


def test_the_layer_imports_nothing_above_it_and_no_transport():
    assert CODE, "the glob stopped matching"
    reaching = []
    for p in CODE:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            names = [a.name for a in getattr(n, "names", [])] if isinstance(n, ast.Import) else []
            if any(w in mod for w in (*ABOVE, "mqtt", "transport")) \
                    or any(any(w in a for w in (*ABOVE, "mqtt", "transport")) for a in names):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, f"sensing reaches above itself or into a transport at {reaching}"


@pytest.mark.parametrize("path", CODE + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_layer_speaks_the_minds_words_or_a_transports(path):
    said = re.findall(r"\b(?:planning|execution|belief|mqtt):\w+", path.read_text())
    assert not said, f"{path.name} names another layer's or a transport's words: {sorted(set(said))}"


def test_the_mind_imports_nothing_of_sensing():
    """The planner reads predictions and the executor observations, by KIND: a graph classified
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
    for path in CODE:
        if path.stem in NOUNS or path.stem == "__init__":
            continue
        tree = ast.parse(path.read_text())
        public = sorted(n.name for n in tree.body
                        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"))
        assert public == [path.stem], f"{path.name} exports {public}"


def test_every_module_with_a_public_function_has_a_test_named_for_it():
    for path in CODE:
        if path.stem in ("__init__", "ontology"):
            continue
        tree = ast.parse(path.read_text())
        if not any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_") for n in tree.body):
            continue
        assert (SENSING / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"


def test_the_rules_are_the_drafts_and_the_graph_kind_is_its():
    """The rule set this layer registers is a `sh:RuleSet` of `sh:SPARQLRule`s and nothing of
    ours types a rule; and `register` classifies by `sh:RulesGraph`."""
    rules = (SENSING / "rules.ttl").read_text()
    assert "a sh:RuleSet" in rules and rules.count("a sh:SPARQLRule") == 3
    assert not re.search(r"sensing:\w*Rule\b", rules)
    assert "RulesGraph" in (SENSING / "register.py").read_text()


def test_every_sensing_word_the_tree_speaks_is_declared_in_its_ontology():
    """Sensing speaks SOSA and SSN, and declares only what they lack: a `sensing:` word in the
    code, the rules, a test, a world or a case is one `ontology.ttl` beside the code declares.
    The 0.1.0 package's own — what an agent polled, what a sensor monitored or sampled, a
    device's sense mode, a drift's horizons — are not spoken here."""
    declared = set(re.findall(r"^:(\w+) a owl:", (SENSING / "ontology.ttl").read_text(), re.M))
    assert declared, "the ontology declares nothing"
    spoken = {}
    for path in sorted(p for p in SENSING.rglob("*") if p.suffix in (".py", ".ttl", ".trig", ".diff")):
        text = path.read_text()
        for word in re.findall(r"\bsensing:(\w+)", text) + re.findall(r'SENSING \+ "(\w+)"', text):
            spoken.setdefault(word, set()).add(path.name)
    undeclared = {w: sorted(where) for w, where in spoken.items() if w not in declared}
    assert not undeclared, f"spoken and not declared: {undeclared}"


def test_the_package_says_it_is_one():
    assert (SENSING / "__init__.py").exists()
    assert not (ROOT / "agent" / "__init__.py").exists(), "agent/ is a namespace portion"
