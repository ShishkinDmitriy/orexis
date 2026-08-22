"""A species is described once and planted many times.

`packages/plant/zamioculcas/` is the plant-side counterpart of `packages/part/dht11/`, and deliberately
the same shape: a species is a model, the pots are the units, and what the species knows is stated
on the class and reaches each pot by entailment. These check that the mechanism actually carries —
that typing a pot is the ONLY thing a world writes, and that everything else follows.

See knowledge/decisions/a-species-is-described-once-and-planted-many-times.md.
"""

from __future__ import annotations

import pathlib
import shutil
import tempfile

import pytest
import rdflib

from agent import genesis, inference
from agent.ontology import beliefs_graph
from agent.store import Store, bindings
from agent.store import PREFIXES
from agent.validate import conforms

ZZ = "http://example.org/agora/zamioculcas#ZamioculcasZamiifolia"

# The fern's block exactly as world/simulation/world.ttl states it. Matched in full and asserted
# present, so that editing that world fails this loudly instead of silently testing nothing —
# a substitution that quietly matches nothing is the failure mode issue #106 exists for.
_FERN = """:fern a water:Plant ;
    ag:localId "fern" ; water:servedBy :barrel1 ;
    ag:rainTopic "rain/fern" ;
    water:driesPerDay 0.12 ; water:litresPerFraction 2.0 ;
    ssn-system:hasOperatingRange [ a ssn-system:OperatingRange ;
        ssn-system:inCondition [ a ssn-system:Condition , schema:PropertyValue ;
            ssn:forProperty water:SoilMoisture ;
            schema:minValue 0.45 ; schema:maxValue 0.65 ; schema:unitCode unit:UNITLESS ] ,
        [ a ssn-system:Condition , schema:PropertyValue ;
            ssn:forProperty water:AirTemperature ;
            schema:minValue 18.0 ; schema:maxValue 24.0 ; schema:unitCode unit:DEG_C ] ] ;
    ssn-system:hasSurvivalRange [ a ssn-system:SurvivalRange ;
        ssn-system:inCondition [ a ssn-system:Condition , schema:PropertyValue ;
            ssn:forProperty water:SoilMoisture ;
            schema:minValue 0.20 ; schema:maxValue 0.85 ; schema:unitCode unit:UNITLESS ] ,
        [ a ssn-system:Condition , schema:PropertyValue ;
            ssn:forProperty water:AirTemperature ;
            schema:minValue 5.0 ; schema:maxValue 35.0 ; schema:unitCode unit:DEG_C ] ] ."""

# What a world says when the pot holds a ZZ: its type, and nothing else. No range, no conditions,
# no numbers — that is the whole point of the package.
_ZZ = f""":fern a <{ZZ}> ;
    ag:localId "fern" ; water:servedBy :barrel1 ;
    water:driesPerDay 0.12 ; water:litresPerFraction 2.0 ."""


@pytest.fixture(scope="module")
def zz_world():
    """`world/simulation` with the fern's pot replanted as a Zamioculcas."""
    with tempfile.TemporaryDirectory() as d:
        w = pathlib.Path(d) / "zz"
        shutil.copytree(genesis.world_dir("simulation"), w)
        path = w / "world.ttl"
        text = path.read_text()
        assert _FERN in text, "world/simulation/world.ttl changed — update _FERN"
        path.write_text(text.replace(_FERN, _ZZ, 1))
        yield w


def _store(world):
    st = Store()
    genesis.refresh_public(st, world)
    inference.materialise(st)
    return st


def test_one_triple_plants_it_and_the_species_supplies_the_rest():
    """The world says what KIND of plant it is. Both ranges, all four properties and every
    number arrive from the package by `owl:hasValue`."""
    with tempfile.TemporaryDirectory() as d:
        w = pathlib.Path(d) / "zz"
        shutil.copytree(genesis.world_dir("simulation"), w)
        path = w / "world.ttl"
        path.write_text(path.read_text().replace(_FERN, _ZZ, 1))

        rows = bindings(_store(w).query(PREFIXES + """
            SELECT ?kind ?property ?min ?max WHERE {
              <http://example.org/agora/world/simulation#fern> ?rel ?range .
              VALUES ?rel { ssn-system:hasOperatingRange ssn-system:hasSurvivalRange }
              ?range a ?kind ; ssn-system:inCondition ?c .
              ?c ssn:forProperty ?property ; schema:minValue ?min ; schema:maxValue ?max }"""))

        got = {(r["kind"].rsplit("/", 1)[-1], r["property"].rsplit("#", 1)[-1]) for r in rows}
        # Illuminance among them although nothing measures light: a range is a fact about the
        # plant, and it does not wait for an instrument to be true or to be carried.
        properties = ("SoilMoisture", "AirTemperature", "AirHumidity", "Illuminance")
        assert got == {("OperatingRange", p) for p in properties} \
                    | {("SurvivalRange", p) for p in properties}, \
            f"the species did not reach the pot: {sorted(got)}"


def test_a_ferns_desire_will_not_do_for_a_zamioculcas(zz_world):
    """The payoff, and the reason the range is worth stating at all.

    That world's agent still wants 0.55 — right for a fern, and a rotted rhizome for a ZZ. Nothing
    about the agent changed; the plant did, and the agent will no longer start. This is the whole
    of "the range is the plant's and the pick is the agent's" with a species behind the range.
    """
    st = _store(zz_world)
    genesis.birth(st, zz_world, "fern")
    data = rdflib.Graph()
    for iri in st.public_graphs():
        ttl = st.get_graph(iri)
        if ttl.strip():
            data.parse(data=ttl, format="turtle")
    # The wants and the pick record arrive through the desire modality (#312) — the aim this
    # test is about is a pick, and the region it violates is derived, so both come from the
    # one build the boot would make.
    from agent import effects
    from conftest import desires_build
    for triple in desires_build(st, "fern").construct(
            "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
        data.add(effects._triple(triple))

    ok, report = conforms(data)
    assert not ok
    assert "pick within a range" in report


def test_it_cannot_thrive_where_it_would_not_survive():
    """Two ranges only mean something together. Raising the operating ceiling above the rot limit
    is the mistake that matters — and it is the direction a well-meaning edit goes."""
    ontology = pathlib.Path("packages/plant/zamioculcas/ontology.ttl").read_text()
    data = rdflib.Graph().parse(data=ontology, format="turtle")
    data.parse(data=pathlib.Path("packages/plant/water/ontology.ttl").read_text(), format="turtle")

    # a pot of it, and the operating ceiling pushed past the survival ceiling
    data.parse(format="turtle", data="""
        @prefix ag: <http://example.org/agora#> .
        @prefix water: <http://example.org/agora/water#> .
        @prefix zz: <http://example.org/agora/zamioculcas#> .
        @prefix ssn-system: <http://www.w3.org/ns/ssn/systems/> .
        ag:pot a water:Plant ;
            ag:localId "pot" ; water:litresPerFraction 2.0 ;
            water:servedBy ag:tap ;
            ssn-system:hasOperatingRange zz:IndoorOperatingRange ;
            ssn-system:hasSurvivalRange  zz:IndoorSurvivalRange .
        ag:tap a water:WaterSource ; water:capacityL 10.0 .""")

    # About the POT alone. A hand-built graph is not a world, and validating it whole would ask
    # after a supplier's capabilities and a market — none of which this is about. `conforms` takes
    # a focus for exactly this reason; see agent/validate.py.
    pot = "http://example.org/agora#pot"
    assert conforms(data, focus=pot)[0], conforms(data, focus=pot)[1]

    # push the moisture operating ceiling to 0.60, above the 0.45 where rot starts
    for condition in data.objects(
            rdflib.URIRef("http://example.org/agora/zamioculcas#IndoorOperatingRange"),
            rdflib.URIRef("http://www.w3.org/ns/ssn/systems/inCondition")):
        prop = data.value(condition, rdflib.URIRef("http://www.w3.org/ns/ssn/forProperty"))
        if str(prop).endswith("SoilMoisture"):
            maxv = rdflib.URIRef("https://schema.org/maxValue")
            data.remove((condition, maxv, None))
            data.add((condition, maxv, rdflib.Literal("0.60", datatype=rdflib.XSD.decimal)))

    ok, report = conforms(data, focus=pot)
    assert not ok
    assert "would not survive" in report
