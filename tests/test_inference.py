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
from agent.ontology import (SOSA, AG, MC, ONTOLOGY_ENTAILED_GRAPH, ONTOLOGY_GRAPH, SENSING,
                            WORLD_ENTAILED_GRAPH, WORLD_GRAPH)
from agent.store import Store, bindings

MC = "http://example.org/agora/microcontroller#"
ONEWIRE = "http://example.org/agora/onewire#"
DHT11 = "http://example.org/agora/dht11#"
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
    types = _types_of(_public(), ONTOLOGY_ENTAILED_GRAPH, ONEWIRE + "DataPinRole")
    assert {MC + "InputRole", MC + "OutputRole", MC + "PinRole"} <= types


def test_a_world_instance_is_typed_by_what_its_class_is_under():
    """The probe is declared a `probe:CapacitiveMoistureProbe` in the stand and a `sosa:Sensor` in
    the society. Being observably a Sensor to the RUNTIME is what let the derivation rules stop
    joining the ontology to walk a subclass path."""
    types = _types_of(_public(), WORLD_ENTAILED_GRAPH, AG + "moisture_sensor_fern")
    assert MC + "Peripheral" in types


def test_a_world_instance_gets_what_its_class_fixes_for_every_member():
    """The one OWL construct the closure honours. `dht11:Dht11` is put under an `owl:hasValue`
    restriction, so every DHT11 has that capability — including the one bolted to the fern's
    board, which the wiring declares a `dht11:Dht11` and which nobody hands a capability to.

    Worth its own test because the guard in test_layout.py cannot cover it. Revert the restriction
    to the punned `dht11:Dht11 ssn-system:hasSystemCapability …` and the vocabulary still says the
    same thing to a reader, still parses, still validates — and entails nothing, so the wiring
    side of that guard goes empty and it passes by having nothing to check. Measured, not assumed.
    """
    caps = {r["c"] for r in bindings(_public().query(
        f"SELECT ?c WHERE {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{"
        f" <{AG}air_sensor_fern> ssn-system:hasSystemCapability ?c }} }}"))}
    assert caps == {DHT11 + "ContinuousOperationCapability"}


def test_a_part_described_once_reaches_every_device_it_is_fitted_to():
    """The DHT11 package is the worked example for describing a part, and this is what makes it
    a description rather than documentation: nothing in `world/sensing/` states a procedure or a
    per-sensor capability, and every one of them is observable on a device.

    It counts, and refuses zero. That is not ceremony — the guard on the capability floor
    asserted nothing for four PRs after a rename moved a term out from under its query, and
    passed the whole time, so a test that walks a vocabulary now says how far it walked. See
    issue #106.
    """
    st = _public()
    reached = {}
    for row in bindings(st.query(
            f"SELECT ?s ?p WHERE {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?s ssn:implements ?p }} }}")):
        reached.setdefault(row["s"], set()).add(row["p"])

    # The part performs the conversation; each sub-sensor performs its half of the frame. Both
    # levels, because stating only one of them was what made the old class-level triples look
    # sufficient — `dht11:Dht11 ssn:implements dht11:CombinedRead` reads as though a device does
    # something, and the only subject it ever gave that predicate was the class itself.
    assert reached.get(AG + "air_sensor_fern") == {DHT11 + "CombinedRead", ONEWIRE + "Transaction"}
    assert reached.get(AG + "air_temp_fern") == {DHT11 + "TemperatureRead"}
    assert reached.get(AG + "air_humidity_fern") == {DHT11 + "HumidityRead"}

    # And the datasheet figures the sub-sensor types carry, which no world repeats.
    for device, capability in ((AG + "air_temp_fern", DHT11 + "TemperatureSensorCapability"),
                               (AG + "air_humidity_fern", DHT11 + "HumiditySensorCapability")):
        caps = {r["c"] for r in bindings(st.query(
            f"SELECT ?c WHERE {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{"
            f" <{device}> ssn-system:hasSystemCapability ?c }} }}"))}
        assert capability in caps, f"<{device}> was not reached by its sub-sensor's capability"

    assert len(reached) == 3, f"walked the vocabulary and reached {len(reached)} devices"


def test_an_anonymous_class_expression_never_becomes_a_type():
    """A restriction is a class, so `?x a _:restriction` follows and is perfectly true. It is also
    unaskable — a blank node has no name to put in a query — and it inflates a triple count
    agent-metrics reports as flat. `isIRI(?super)` in rules 2 and 3 leaves it out, and it had to
    be added the moment the first class expression entered the vocabulary."""
    st = _public()
    for graph in (ONTOLOGY_ENTAILED_GRAPH, WORLD_ENTAILED_GRAPH):
        anonymous = bindings(st.query(
            f"SELECT ?s ?t WHERE {{ GRAPH <{graph}> {{ ?s a ?t FILTER(!isIRI(?t)) }} }}"))
        assert not anonymous, f"{graph} types something by an unaskable class expression"


def test_an_entailment_never_lands_in_the_graph_it_was_computed_from():
    """The whole of issue #58, as one assertion.

    A package's vocabulary stays exactly as that package wrote it, and what RDFS made of it sits
    beside it — so "who put this here" is answerable by looking. Merge them and the question
    becomes unanswerable for ever, because nothing records which triples were typed and which
    were concluded.
    """
    st = _public()
    asserted = _types_of(st, ONTOLOGY_GRAPH, ONEWIRE + "DataPinRole")
    entailed = _types_of(st, ONTOLOGY_ENTAILED_GRAPH, ONEWIRE + "DataPinRole")
    assert asserted == {MC + "BidirectionalRole"}  # what the file literally says
    assert MC + "OutputRole" in entailed and MC + "OutputRole" not in asserted


def test_a_reader_still_sees_one_world():
    """And the split costs a reader nothing: an ordinary pattern spans every public graph,
    because `store.query` makes them the default graph. A reader that had to know which of the
    five holds its fact would be a worse design than the one #58 replaced."""
    rows = bindings(_public().query(
        f"SELECT ?t WHERE {{ <{AG}moisture_sensor_fern> a ?t }}"))
    types = {r["t"] for r in rows}
    assert SOSA + "Sensor" in types  # asserted in the world
    assert MC + "Peripheral" in types  # entailed, in another graph entirely


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

@pytest.mark.parametrize("world", ["simulation", "sensing"])
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
    for iri in st.public_graphs():
        ttl = st.get_graph(iri)
        if ttl.strip():
            data.parse(data=ttl, format="turtle")

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
    # The KERNEL's Python and every PACKAGE's, as two groups. One `rglob` over `agent/` used to
    # reach both, because capabilities were subpackages of it. After they moved, that glob still
    # matched plenty of files — so the non-empty guard below stayed green while 143 parametrised
    # cases quietly stopped running, every one of them a capability's SPARQL. Non-empty is not
    # the same as complete, and this is what that looks like.
    "agent": sorted(Path(genesis.__file__).parent.rglob("*.py")),
    "packages": sorted(loader.PACKAGES_ROOT.rglob("*.py")),
    # Under packages/ and not under agent/. Every `.ru` and `.rq` belongs to a PACKAGE, and
    # packages left the kernel's tree — which is exactly the move that has twice emptied a glob
    # here and taken cases off this scan without failing anything. It failed loudly this time.
    "rules": sorted(loader.PACKAGES_ROOT.rglob("*.ru")),
    "review": sorted(loader.PACKAGES_ROOT.rglob("*.rq")),
    "onboarding": sorted(loader.REPO_ROOT.glob("onboarding/*.py")),
}


@pytest.mark.parametrize("group", sorted(_QUERY_SOURCES))
def test_every_source_group_is_still_found(group):
    """The guard on the guard, borrowed from test_store.py — moving a tree has twice emptied a
    glob and taken cases off a scan without failing anything."""
    assert _QUERY_SOURCES[group], f"the {group} glob is stale and this guard checks nothing"


# The one file allowed to walk the hierarchy, because it is the file that flattens it.
# The two files that may walk a subclass path, and the reason is the same for both: they run
# BEFORE the closure exists. `inference.py` computes it. `store.py` finds the graphs it will be
# written into — discovery is what tells the loader where the entailments go, so it cannot read
# them. Everything else runs after and must simply ask what a thing IS.
_BEFORE_THE_CLOSURE = ("inference.py", "store.py")


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

    Two files are exempt because they run before there is a closure to read: the one that
    computes it, and the one that discovers which graphs it lands in.
    """
    if path.name in _BEFORE_THE_CLOSURE:
        pytest.skip("runs before the closure exists — see _BEFORE_THE_CLOSURE")
    text = _query_text(path)
    for walk in ("rdfs:subClassOf*", "rdfs:subClassOf+",
                 "rdfs:subPropertyOf*", "rdfs:subPropertyOf+"):
        assert walk not in text, (
            f"{path.name} walks {walk} by hand. Entailments are materialised at genesis — ask "
            "what a thing IS. If the closure does not cover your case, widen agora/inference.py "
            "rather than working around it here.")


def test_hosting_is_entailed_from_the_deployment():
    """Rule 6 (#99): the wiring states a deployment — which systems, on which platform, from
    when, for what — and `sosa:hosts` is what SSN's property chain makes of it. The premise is
    finally in the graph, and the conclusion is computed rather than asserted beside it."""
    from conftest import genesis_store

    st = genesis_store(world="sensing")
    rows = bindings(st.query("""
SELECT ?hosted WHERE { <http://example.org/agora#esp32_fern>
  <http://www.w3.org/ns/sosa/hosts> ?hosted }"""))
    hosted = {r["hosted"].rsplit("#", 1)[-1] for r in rows}
    assert {"moisture_sensor_fern", "status_led_fern", "air_sensor_fern"} <= hosted
    # and the conclusion sits in the entailed graph, never the asserted wiring
    from agent.ontology import WORLD_ENTAILED_GRAPH
    entailed = bindings(st.query(f"""
SELECT ?hosted WHERE {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{
  <http://example.org/agora#esp32_fern> <http://www.w3.org/ns/sosa/hosts> ?hosted }} }}"""))
    assert len(entailed) >= 3, "the chain's conclusion must land in world/entailed"
