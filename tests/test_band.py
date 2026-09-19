"""A reading is what the domain says it is (#576): the bands as classes, minted at genesis and
asserted by entailment.

Deliberation is on triples and a number is not special — the record of that name. Sensing
declares the five families of what a reading can be; genesis mints a member per (subject,
property) that states a range, defined in OWL; the store's entailment door asserts membership
when a reading is written and when a possible world forks; and the search matches, states a
premise and keys a remembered plan by the band, never by the number.
"""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from conftest import build_agent, genesis_store, write_reading
from orexis_agent_deliberation import signature
from orexis_agent_deliberation.planner import Planner
from orexis_agent_progression.ontology import STATE_GRAPH
from orexis_agent_progression.store import Store, bindings
from test_planning import MOISTURE, STORED

SOSA = "http://www.w3.org/ns/sosa/"
SENSING = "http://example.org/orexis/sensing#"
BAND = "http://example.org/orexis#band."
TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def _bands_of(store, subject_local: str, prop_local: str) -> dict:
    """member local name -> family, for one (subject, property)."""
    rows = bindings(store.query(f"""
SELECT ?c ?f WHERE {{ ?c a owl:Class ; rdfs:subClassOf ?f . FILTER(STRSTARTS(STR(?c), "{BAND}{subject_local}.{prop_local}.")) }}"""))
    return {r["c"].rsplit(".", 1)[-1]: r["f"].rsplit("#", 1)[-1] for r in rows}


def _classes_of(store, observed_property: str) -> set[str]:
    """The band MEMBERS a reading is typed with; its families ride beside them (#579) and
    are asserted too, but the member says which band."""
    rows = bindings(store.query(f"""
SELECT ?c WHERE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:observedProperty <{observed_property}> ; a ?c }}
  FILTER(STRSTARTS(STR(?c), "{BAND}")) }}"""))
    return {r["c"].rsplit(".", 1)[-1] for r in rows}


def _families_of(store, observed_property: str) -> set[str]:
    rows = bindings(store.query(f"""
SELECT ?c WHERE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:observedProperty <{observed_property}> ; a ?c }}
  FILTER(STRSTARTS(STR(?c), "{SENSING}")) }}"""))
    return {r["c"].rsplit("#", 1)[-1] for r in rows}


def test_genesis_mints_a_band_per_range_the_world_states_defined_in_owl(monkeypatch):
    """The loner's pot states an operating range for its moisture, so THREE members are minted
    — below it, inside it, above it — each a subclass of sensing's family, each an OWL
    intersection an outside reasoner could read: the observation class, the subject and the
    property by value, the result by facets.

    Three and no combinations, by the sovereign's ruling of 2026-09-08: the survival envelope
    used to mint two more beneath the region's, so a dying reading was typed with two bands at
    once. It mints none now — it is a range the subject states, read as a number by whoever
    scales urgency — and a domain that wants a fourth state declares its own."""
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): 0.10}, world="loner")
    assert _bands_of(st, "zz", "SoilMoisture") == {
        "below": "BelowRegion", "inside": "InRegion", "above": "AboveRegion"}
    rows = bindings(st.query(f"""
SELECT ?p ?v ?facet ?bound WHERE {{
  <{BAND}zz.SoilMoisture.inside> owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?r .
  ?r a owl:Restriction ; owl:onProperty ?p .
  OPTIONAL {{ ?r owl:hasValue ?v }}
  OPTIONAL {{ ?r owl:someValuesFrom/owl:withRestrictions/rdf:rest*/rdf:first ?f . ?f ?facet ?bound }} }}"""))
    stated = {(r["p"].rsplit("/", 1)[-1], r.get("v", "").rsplit("#", 1)[-1] or None,
               (r.get("facet") or "").rsplit("#", 1)[-1] or None, r.get("bound")) for r in rows}
    assert ("hasFeatureOfInterest", "zz", None, None) in stated
    assert ("observedProperty", "SoilMoisture", None, None) in stated
    assert ("hasSimpleResult", None, "minInclusive", "0.1") in stated
    assert ("hasSimpleResult", None, "maxInclusive", "0.3") in stated


def test_a_reading_is_classified_when_it_is_written_and_reclassified_when_it_moves(monkeypatch):
    """The sensed writer entails what it wrote: 0.05 and 0.01 are both below the region, which
    is all sensing's three bands say about either; 0.25 is inside; the upsert takes the old
    class with the old node. The butt's level, whose subject states no range, is nothing but
    an observation."""
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    agent = build_agent("gardener", genesis_store({("zz", MOISTURE): 0.10, ("water_butt", STORED): 3.0},
                                                  world="loner"), monkeypatch)
    assert _classes_of(agent.beliefs, MOISTURE) == {"inside"}, "the seeded 0.10 sits on the inclusive floor"
    write_reading(agent, 0.05, MOISTURE)
    assert _classes_of(agent.beliefs, MOISTURE) == {"below"}
    write_reading(agent, 0.01, MOISTURE)
    assert _classes_of(agent.beliefs, MOISTURE) == {"below"}, \
        "past the survival floor is still below the region and nothing more: three bands"
    assert _families_of(agent.beliefs, MOISTURE) == {"BelowRegion"}, \
        "and the family is asserted with the member, so a shape reads sh:class sensing:BelowRegion"
    write_reading(agent, 0.25, MOISTURE)
    assert _classes_of(agent.beliefs, MOISTURE) == {"inside"}
    assert _classes_of(agent.beliefs, STORED) == set(), "no range stated, no band"


def test_the_entailment_door_honours_an_intersection_of_values_and_facets():
    """The store's second OWL construct, on a bare store: a class defined as the intersection
    of a named class, two `owl:hasValue` restrictions and a datatype restriction with facets.
    Membership needs all of them; the facets are read as XSD reads them, inclusive or
    exclusive; a node in another graph or of another subject is not asked."""
    st = Store()
    #  A bare store discovers its public graphs from the one graph that describes every graph
    #  and itself, so the case brings that graph, saying the definitions' graph is public.
    st.update("""INSERT DATA { GRAPH <urn:g:catalogue> {
      <urn:g:catalogue> a orexis:CatalogueGraph . <urn:g:vocabulary> a orexis:PublicGraph } }""")
    st.update("""INSERT DATA { GRAPH <urn:g:vocabulary> {
      <urn:c:cold> a owl:Class ; owl:equivalentClass [ a owl:Class ; owl:intersectionOf ( <urn:Thing>
          [ a owl:Restriction ; owl:onProperty <urn:of> ; owl:hasValue <urn:room> ]
          [ a owl:Restriction ; owl:onProperty <urn:v> ;
            owl:someValuesFrom [ a rdfs:Datatype ; owl:onDatatype xsd:decimal ;
                                 owl:withRestrictions ( [ xsd:minInclusive 5 ] [ xsd:maxExclusive 10 ] ) ] ] ) ] } }""")
    st.update("""INSERT DATA { GRAPH <urn:g:state> {
      <urn:a> a <urn:Thing> ; <urn:of> <urn:room> ; <urn:v> 5 .
      <urn:b> a <urn:Thing> ; <urn:of> <urn:room> ; <urn:v> 10 .
      <urn:c> a <urn:Thing> ; <urn:of> <urn:hall> ; <urn:v> 7 .
      <urn:d> a <urn:Other> ; <urn:of> <urn:room> ; <urn:v> 7 . } }""")
    found = {(n.value, c.value) for n, c in st.entail("urn:g:state")}
    assert found == {("urn:a", "urn:c:cold")}, found
    assert {(n.value, c.value) for n, c in st.entail("urn:g:state", of=["<urn:b>"])} == set()
    rows = bindings(st.query("SELECT ?x WHERE { GRAPH <urn:g:state> { ?x a <urn:c:cold> } }"))
    assert [r["x"] for r in rows] == ["urn:a"], "asserted where the node is"


def test_a_predicted_reading_carries_its_band_and_a_premise_states_the_standing_one(monkeypatch):
    """A dry gardener's dose predicts what the reading will BE and nothing else (#579): the
    band its rule declared, with the family the fork's entailment closes it up to, and no
    number. Its premise states the standing reading by its band alone: a triple the present
    can be asked, never a number."""
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    agent = build_agent("gardener", genesis_store({("zz", MOISTURE): 0.05, ("water_butt", STORED): 3.0},
                                                  world="loner"), monkeypatch)
    desire = next(g for g in agent.pursuing() if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    plan = Planner(agent, agent.me).plan(desire)
    assert plan.steps, "a dry gardener doses"
    adds, _ = plan.steps[0].predicts
    keyed = [f for f in adds if f[0] == "keyed"]
    assert {f[3] for f in keyed} == {TYPE}, "a prediction says what the reading IS and no number"
    assert {f[4] for f in keyed} == {BAND + "zz.SoilMoisture.inside", SENSING + "InRegion"}
    premise = [f for f in plan.steps[0].precondition if f[0] == "keyed"]
    assert premise and {f[3] for f in premise} == {TYPE}
    assert {f[4] for f in premise} == {BAND + "zz.SoilMoisture.below", SENSING + "BelowRegion"}, premise


def test_facts_by_class_drop_a_classed_readings_number_and_keep_an_unclassed_one():
    key = ((SOSA + "hasFeatureOfInterest", "urn:pot"), (SOSA + "observedProperty", "urn:m"))
    other = ((SOSA + "hasFeatureOfInterest", "urn:butt"), (SOSA + "observedProperty", "urn:l"))
    facts = frozenset({("keyed", SOSA + "Observation", key, SOSA + "hasSimpleResult", 0.27),
                       ("keyed", SOSA + "Observation", key, TYPE, "urn:band:inside"),
                       ("keyed", SOSA + "Observation", other, SOSA + "hasSimpleResult", 2.5),
                       ("urn:s", "urn:p", "urn:o")})
    assert signature.by_class(facts) == frozenset({
        ("keyed", SOSA + "Observation", key, TYPE, "urn:band:inside"),
        ("keyed", SOSA + "Observation", other, SOSA + "hasSimpleResult", 2.5),
        ("urn:s", "urn:p", "urn:o")})


def test_the_signature_states_a_keyed_node_by_its_bands_and_never_by_its_keyed_class():
    node = ox.BlankNode()
    obs, band = ox.NamedNode(SOSA + "Observation"), ox.NamedNode("urn:band:inside")
    dec = ox.NamedNode("http://www.w3.org/2001/XMLSchema#decimal")
    triples = [ox.Triple(node, ox.NamedNode(TYPE), obs), ox.Triple(node, ox.NamedNode(TYPE), band),
               ox.Triple(node, ox.NamedNode(SOSA + "hasFeatureOfInterest"), ox.NamedNode("urn:pot")),
               ox.Triple(node, ox.NamedNode(SOSA + "observedProperty"), ox.NamedNode("urn:m")),
               ox.Triple(node, ox.NamedNode(SOSA + "hasSimpleResult"), ox.Literal("0.5", datatype=dec))]
    keys = {SOSA + "Observation": (frozenset({SOSA + "hasFeatureOfInterest", SOSA + "observedProperty"}),
                                   frozenset({SOSA + "hasSimpleResult"}))}
    stated = {(f[3], f[4]) for f in signature.facts(triples, keys)}
    assert stated == {(TYPE, "urn:band:inside"), (SOSA + "hasSimpleResult", 0.5)}
