"""One graph, both engines — the guard on the thing issue #27 was about.

Two engines read this society's graphs. `pyshacl` used to entail what the vocabulary implies and
`pyoxigraph` entailed nothing, so a world could satisfy a shape about a relationship the code
would never observe. `agora/inference.py` now asserts the entailments once, into the store, and
validation runs with inference OFF against that same graph.

The interesting test here is not that the closure computes something. It is that **nothing has
drifted back apart** — that pyshacl, given its own RDFS reasoner, still reaches the same verdict
as the materialised closure. The day that stops being true is the day the bug returns wearing
different clothes, and it would otherwise be found in production rather than here.

See knowledge/decisions/one-graph-both-engines-read.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import rdflib
from pyshacl import validate as shacl_validate

from agent import genesis, inference, loader
from agent.ontology import ONTOLOGY_GRAPH, WORLD_GRAPH
from agent.store import Store, bindings

MC = "http://example.org/agora/microcontroller#"
ONEWIRE = "http://example.org/agora/onewire#"
AG = "http://example.org/agora#"


def _public(world: str = "sensing") -> Store:
    st = Store()
    genesis.refresh_public(st, genesis.world_dir(world))
    return st


def _types_of(st: Store, graph: str, subject: str) -> set[str]:
    return {r["t"] for r in bindings(st.query(
        f"SELECT ?t WHERE {{ GRAPH <{graph}> {{ <{subject}> a ?t }} }}"))}


# --- what the closure asserts ----------------------------------------------------------------

def test_a_t_box_individual_gets_the_whole_chain():
    """`onewire:DataPinRole a mc:BidirectionalRole`, and Bidirectional is under both Input and
    Output, which are under PinRole. The shape keeping a driven line off pins 34-39 asks whether
    the role is an OUTPUT — asserted nowhere, entailed twice over, and the reason seven shape
    tests failed the moment inference was switched off."""
    types = _types_of(_public(), ONTOLOGY_GRAPH, ONEWIRE + "DataPinRole")
    assert {MC + "BidirectionalRole", MC + "InputRole",
            MC + "OutputRole", MC + "PinRole"} <= types


def test_a_world_instance_is_typed_by_what_its_class_is_under():
    """The probe is declared a `probe:CapacitiveMoistureProbe` in the stand and an `ag:Sensor` in
    the society. Being observably a Sensor to the RUNTIME is what let the derivation rules stop
    joining the ontology to walk a subclass path."""
    types = _types_of(_public(), WORLD_GRAPH, AG + "moisture_sensor_fern")
    assert AG + "Sensor" in types
    assert MC + "Peripheral" in types


def test_the_closure_is_not_full_rdfs():
    """Deliberately narrow. Full entailment asserts every resource is an `rdfs:Resource` and
    every property an `rdf:Property` — true, useless, and it would multiply the triple count an
    agent reports as flat. See knowledge/domain/agent-metrics.md."""
    types = _types_of(_public(), ONTOLOGY_GRAPH, ONEWIRE + "DataPinRole")
    assert "http://www.w3.org/2000/01/rdf-schema#Resource" not in types


def test_materialising_twice_changes_nothing():
    """`refresh_public` runs on every start, so the closure has to be a function of the files
    rather than an accumulation — otherwise a long-lived agent's ontology graph would grow by
    restart count."""
    st = _public()
    before = len(st)
    inference.materialise(st)
    assert len(st) == before


# --- the guard that matters ------------------------------------------------------------------

@pytest.mark.parametrize("world", ["society", "simulation", "sensing"])
def test_pyshacl_agrees_with_the_materialised_closure(world):
    """The drift guard, and the reason this file exists.

    Validation ships with `inference="none"` because the store already carries the entailments.
    That is only safe while pyshacl's own RDFS reasoner would reach the same verdict — so run it
    both ways over the same graph and require the same answer. A failure here means pyshacl
    entails something `agora/inference.py` does not, which is exactly the two-engine disagreement
    #27 was opened about, and it is worth catching as a test rather than as a 3am surprise.
    """
    st = _public(world)
    data = rdflib.Graph()
    for iri in (ONTOLOGY_GRAPH, WORLD_GRAPH):
        data.parse(data=st.get_graph(iri), format="turtle")

    ontology, shapes = rdflib.Graph(), rdflib.Graph()
    for path in loader.ontology_files():
        ontology.parse(str(path), format="turtle")
    for path in loader.shapes_files():
        shapes.parse(str(path), format="turtle")

    verdicts = {}
    for mode in ("none", "rdfs"):
        conforms, _, _ = shacl_validate(
            data + ontology, shacl_graph=shapes, ont_graph=ontology,
            inference=mode, advanced=True)
        verdicts[mode] = conforms
    assert verdicts["none"] == verdicts["rdfs"], (
        f"{world}: pyshacl reaches a different verdict with its own reasoner than against the "
        "materialised closure — agora/inference.py no longer covers what the shapes rely on")


# --- nobody should need to infer by hand again -----------------------------------------------

_QUERY_SOURCES = {
    "agent": sorted(Path(genesis.__file__).parent.rglob("*.py")),
    "rules": sorted(Path(genesis.__file__).parent.rglob("*.ru")),
    "review": sorted(Path(genesis.__file__).parent.rglob("*.rq")),
    "onboarding": sorted(loader.REPO_ROOT.glob("onboarding/*.py")),
}


@pytest.mark.parametrize("group", sorted(_QUERY_SOURCES))
def test_every_source_group_is_still_found(group):
    """The guard on the guard, borrowed from test_store.py — moving a tree has twice emptied a
    glob and taken cases off a scan without failing anything."""
    assert _QUERY_SOURCES[group], f"the {group} glob is stale and this guard checks nothing"


# The one file allowed to walk the hierarchy, because it is the file that flattens it.
_DEFINES_THE_CLOSURE = "inference.py"


def _query_text(path: Path) -> str:
    """Everything a SPARQL engine could see in this file, and nothing a human wrote for humans.

    Scanning raw source finds the word in prose — the comment on `_family_q` explaining why the
    path went away trips a naive grep, which would make this guard punish documentation. Python
    is parsed so only string literals are read (comments are not literals, and docstrings are
    dropped); `.ru` and `.rq` just lose their `#` lines.
    """
    if path.suffix != ".py":
        return "\n".join(line.split("#", 1)[0] for line in path.read_text().splitlines())

    tree = ast.parse(path.read_text())
    docstrings = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    return "\n".join(
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node not in docstrings)


@pytest.mark.parametrize(
    "path", sorted(p for g in _QUERY_SOURCES.values() for p in g), ids=lambda p: p.name)
def test_no_query_walks_a_subclass_path_by_hand(path):
    """Six queries used to carry `rdfs:subClassOf*` to compensate for a runtime that could not
    infer, and twenty-five axioms were declared for those six sites to read. An axiom meant
    something only where an author remembered to spell out the path.

    The entailments are asserted before anything reads them now, so a hand-rolled walk is either
    redundant or a sign that someone is working around the closure instead of extending it.
    """
    if path.name == _DEFINES_THE_CLOSURE:
        pytest.skip("this is the closure")
    text = _query_text(path)
    for walk in ("rdfs:subClassOf*", "rdfs:subClassOf+",
                 "rdfs:subPropertyOf*", "rdfs:subPropertyOf+"):
        assert walk not in text, (
            f"{path.name} walks {walk} by hand. Entailments are materialised at genesis — ask "
            "what a thing IS. If the closure does not cover your case, widen agora/inference.py "
            "rather than working around it here.")
