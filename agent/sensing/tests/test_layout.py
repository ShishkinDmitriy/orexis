"""What the sensing tree's SHAPE promises, and the one direction its arrows may point.

Sensing is the translation row and beneath everything but belief: the prediction package reads
the observations it writes by sensing's own kind, `sensing:ObservationGraph`, the word and not the
code — no sensing, no observations, so the kind is sensing's alone (#944) — and a domain's command
names that kind in its own text; neither imports a line of it, and it imports nothing of theirs and
speaks none of their words — and not one word of any transport, which is the decoupling this layer
exists for. BELIEF IS BENEATH IT, and that is said in one word: what an observation is of and its
quantity are revisions the deliberator concludes by this layer's rules, so its role, the observer,
is beneath the deliberator (#927), which its ontology states as `rdfs:subClassOf belief:Deliberator`
— the one word of belief's it speaks, since a package's need is said by its role sitting beneath the
role of a package below it. Sensing RUNS that revision over its own observations — belief, beneath,
knows no kind of them — and does it through the part it links to, handing each observation to
belief's part with the kind its revision is to be, as execution hands a saying to speech's; so it
still imports nothing of belief's code, having no use for it. A module named for an act exports that
act alone, a module named for a thing may answer several questions about it, and every public
function has a test named for it. A TEST here may import the belief package, to hold this layer's
rules to what they conclude; the code may not.
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
NOUNS = {"ontology", "pipeline", "cadence", "events"}

ABOVE = ("prediction", "planning", "execution", "belief")


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
def test_no_file_of_this_layer_speaks_a_higher_layers_words_or_a_transports(path):
    said = re.findall(r"\b(?:prediction|planning|execution|speech|mqtt):\w+", path.read_text())
    assert not said, f"{path.name} names another layer's or a transport's words: {sorted(set(said))}"


def test_the_one_word_of_belief_this_layer_speaks_is_the_role_its_own_is_beneath():
    """Belief is beneath sensing by one claim alone — the observer is a deliberator — and that claim
    is the whole of what sensing says in belief's words: no other file speaks one, and the ontology
    speaks exactly the role."""
    said = {p.name: set(re.findall(r"\bbelief:\w+", p.read_text())) for p in CODE + VOCABULARY}
    assert said.get("ontology.ttl") == {"belief:Deliberator"}, said
    assert not any(words for name, words in said.items() if name != "ontology.ttl"), said


#  A TRANSPORT IS BENEATH SENSING AND IMPORTS ITS CALLBACK, `received`, and its reads of a sensor's
#  cadence, and nothing else of it; the contract a transport answers is the transport family's own,
#  not sensing's.
CALLBACK = ("agent.sensing.received", "agent.sensing.cadence")


def test_nothing_above_imports_sensing():
    """The prediction package reads observations by sensing's KIND, a graph classified
    `sensing:ObservationGraph` — the word, which a package above may speak, and no line of the code —
    and the executor reads none: a domain's command names the kind in its own text. A transport,
    beneath, imports the callback and sensing's reads of a sensor's cadence — the frequency a polling
    member polls at, and which sensors' latest has lapsed, which the MQTT member nudges — and nothing
    else of sensing's."""
    for path in sorted((ROOT / "agent").rglob("*.py")):
        if SENSING in path.parents or "tests" in path.parts or path == ROOT / "agent" / "runtime.py":
            continue                  # the container assembles every layer and may import them all
        transport = "transport" in path.parts
        for node in ast.walk(ast.parse(path.read_text())):
            mod = (node.module if isinstance(node, ast.ImportFrom) else None) or ""
            if transport and mod in CALLBACK:
                continue
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
    """The rule set this layer ships is a `sh:RuleSet` of `sh:SPARQLRule`s and nothing of ours
    types a rule; and the document says it is a `sh:RulesGraph`, the draft's kind."""
    rules = (SENSING / "rules.ttl").read_text()
    assert "a sh:RuleSet" in rules and rules.count("a sh:SPARQLRule") == rules.count("sh:construct") > 0
    assert not re.search(r"sensing:\w*Rule\b", rules)
    assert "<> a sh:RulesGraph ." in rules


def test_every_sensing_word_the_tree_speaks_is_declared_in_its_ontology():
    """Sensing speaks SOSA and SSN, and declares only what they lack: a `sensing:` word in the
    code, the rules, a test, a world or a case is one `ontology.ttl` beside the code declares.
    The 0.1.0 package's own — what an agent polled, what a sensor monitored or sampled, a
    device's sense mode, a drift's horizons — are not spoken here."""
    declared = set(re.findall(r"^:(\w+) a ", (SENSING / "ontology.ttl").read_text(), re.M))
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
