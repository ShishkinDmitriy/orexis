"""What the prediction tree's SHAPE promises, and the one direction its arrows may point.

Prediction sits ABOVE sensing and beneath the mind: it predicts what a sensor will read, and with
no sensing there is nothing to predict, so it reads the observation a sensor last made by
sensing's kind, `sensing:ObservationGraph` — the one word of sensing's it speaks (#944) — and SOSA's
words, and imports nothing of sensing's code, of the mind, of the belief package or of any
transport; the planner reads what it writes by kind and imports nothing of it. A module named for an act exports that act alone, a
module named for a thing may answer several questions about it, and every public function has a
test named for it. A TEST here may import its neighbours, to tell the whole story of a pot; the
code may not.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PREDICTION = ROOT / "agent" / "prediction"
CODE = sorted(p for p in PREDICTION.glob("*.py"))
VOCABULARY = sorted(PREDICTION.glob("*.ttl"))

#  A MODULE NAMED FOR A THING, which may export several reads of it.
NOUNS = {"ontology", "ranges"}

ELSEWHERE = ("sensing", "planning", "execution", "belief", "mqtt", "transport")


def test_the_package_imports_nothing_of_its_neighbours():
    assert CODE, "the glob stopped matching"
    reaching = []
    for p in CODE:
        for n in ast.walk(ast.parse(p.read_text())):
            mod = (n.module if isinstance(n, ast.ImportFrom) else None) or ""
            names = [a.name for a in getattr(n, "names", [])] if isinstance(n, ast.Import) else []
            if any(w in mod for w in ELSEWHERE) or any(any(w in a for w in ELSEWHERE) for a in names):
                reaching.append(f"{p.name}:{n.lineno}")
    assert not reaching, f"prediction reaches into a neighbour at {reaching}"


@pytest.mark.parametrize("path", CODE + VOCABULARY, ids=lambda p: p.name)
def test_no_file_of_this_package_speaks_a_neighbours_words(path):
    said = re.findall(r"\b(?:planning|execution|belief|mqtt):\w+", path.read_text())
    assert not said, f"{path.name} names a neighbour's words: {sorted(set(said))}"


def test_the_one_word_of_sensing_this_package_speaks_is_the_kind_an_observation_is_kept_in():
    """Sensing is beneath prediction, and its observations are what prediction runs from, so prediction
    names them in sensing's word — the kind, and that alone: no `sensing:` word else, by prefix or by
    spelling, is spoken in the code or the vocabulary, and the kind is spoken somewhere."""
    said = {p.name: set(re.findall(r"\bsensing:(\w+)", p.read_text()))
            | set(re.findall(r'SENSING \+ "(\w+)"', p.read_text())) for p in CODE + VOCABULARY}
    assert any("ObservationGraph" in words for words in said.values()), said
    assert all(words <= {"ObservationGraph"} for words in said.values()), said


def test_the_mind_imports_nothing_of_prediction():
    """The planner reads predictions by KIND: a graph classified `orexis:PredictionGraph` is
    its to read whoever wrote it."""
    for path in sorted((ROOT / "agent").rglob("*.py")):
        if PREDICTION in path.parents or "tests" in path.parts or path == ROOT / "agent" / "runtime.py":
            continue                  # the container assembles every layer and may import them all
        for node in ast.walk(ast.parse(path.read_text())):
            mod = (node.module if isinstance(node, ast.ImportFrom) else None) or ""
            assert "agent.prediction" not in mod, f"{path.relative_to(ROOT)} imports prediction"
            if isinstance(node, ast.Import):
                assert not any(a.name.startswith("agent.prediction") for a in node.names), path


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
        assert (PREDICTION / "tests" / f"test_{path.stem}.py").exists(), f"{path.name} has no test named for it"


def test_every_prediction_word_the_tree_speaks_is_declared_in_its_ontology():
    """One word of its own, and every `prediction:` word in the code, a test, a world or a
    case is one `ontology.ttl` beside the code declares."""
    declared = set(re.findall(r"^:(\w+) a ", (PREDICTION / "ontology.ttl").read_text(), re.M))
    assert declared, "the ontology declares nothing"
    spoken = {}
    for path in sorted(p for p in PREDICTION.rglob("*") if p.suffix in (".py", ".ttl", ".trig", ".diff")):
        text = path.read_text()
        for word in re.findall(r"\bprediction:(\w+)", text) + re.findall(r'PREDICTION \+ "(\w+)"', text):
            spoken.setdefault(word, set()).add(path.name)
    undeclared = {w: sorted(where) for w, where in spoken.items() if w not in declared}
    assert not undeclared, f"spoken and not declared: {undeclared}"


def test_the_package_says_it_is_one():
    assert (PREDICTION / "__init__.py").exists()
    assert not (ROOT / "agent" / "__init__.py").exists(), "agent/ is a namespace portion"
