"""A reading that stopped being evidence is a want of its own (#240).

The first end-to-end case for desires as graphs: a want nobody can read, repaired by looking and
by nothing else. Three things have to hold together — the horizon is published so a SHAPE can
read what only Python could compute, the want reports `stale` where the region reports met or
unmet, and the reflex's `value is None` special case is gone with its behaviour intact.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import rdflib
from pyshacl import validate as shacl_validate

from packages.capability.desire import desires_of

from conftest import desires_build, MOISTURE, build_agent, genesis_store

FERN = "http://example.org/agora/world/simulation#fern_agent"
_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


def _fern(monkeypatch, value=0.55):
    """A fern with a reading and a sensing module that has published its horizon."""
    st = genesis_store({("fern", MOISTURE): value})
    agent = build_agent("fern", st, monkeypatch)
    next(m for m in agent.modules if m.name == "subscribing").start()
    return agent, st


def _age_the_reading(st, hours=3):
    from agent.ontology import SENSED_GRAPH

    old = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    st.update(f"""
        DELETE {{ GRAPH <{SENSED_GRAPH}> {{ ?o <http://www.w3.org/ns/sosa/resultTime> ?t }} }}
        INSERT {{ GRAPH <{SENSED_GRAPH}> {{ ?o <http://www.w3.org/ns/sosa/resultTime>
                 "{old}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}
        WHERE  {{ GRAPH <{SENSED_GRAPH}> {{ ?o <http://www.w3.org/ns/sosa/resultTime> ?t }} }}""")


def test_the_horizon_the_shape_reads_is_the_one_the_module_computes(monkeypatch):
    """One definition, which is the whole reason the horizon is published at all.

    `stale_after_s` works it out from the rhythm in force — the board's acknowledgement where it
    gives one, the agent's intent where it does not, the slowest cadence where neither — and
    none of that was ever written down. A shape cannot run a method, so the alternatives were a
    second copy of the fallback chain in SPARQL, free to drift, or a baked constant, wrong the
    moment urgency re-commands the cadence. This asserts the third way stayed true: what is in
    the graph is what the method returns.
    """
    from agent.ontology import INSTRUMENTS_GRAPH
    from agent.store import bindings
    from packages.capability.sensing.terms import STALE_AFTER_S

    agent, st = _fern(monkeypatch)
    sensing = next(m for m in agent.modules if m.name == "subscribing")

    published = {r["s"]: int(r["h"]) for r in bindings(st.query(
        f"SELECT ?s ?h WHERE {{ GRAPH <{INSTRUMENTS_GRAPH}> {{ ?s <{STALE_AFTER_S}> ?h }} }}"))}
    assert published, "a sensor with no published horizon is a want that can never fire"
    for sensor in sensing.sensors:
        assert published[sensor.uri] == sensing.stale_after_s(sensor.subject, sensor.observes)


def test_a_reading_past_the_horizon_is_stale_where_a_fresh_one_is_met(monkeypatch):
    """The same number, the same region, two different wants — the age is what separates them.

    0.55 sits inside fern's 0.45-0.65, so while it is fresh there is nothing to want. Aged past
    the horizon it is not suddenly wrong, it is no longer EVIDENCE: what the agent wants is to
    look again, and its urgency is the maximum for the same reason an unread property's is.
    """
    agent, st = _fern(monkeypatch, value=0.55)
    fresh = {g.observed_property: g for g in desires_of(desires_build(st, "fern").query_union, st.query, FERN, "fern")}
    assert fresh[MOISTURE].state == "met" and fresh[MOISTURE].urgency == 0.0

    _age_the_reading(st)
    stale = {g.observed_property: g for g in desires_of(desires_build(st, "fern").query_union, st.query, FERN, "fern")}
    assert stale[MOISTURE].state == "stale"
    assert stale[MOISTURE].urgency == 1.0, \
        "not knowing is not knowing — scaling it by a distance the agent no longer trusts " \
        "would rank it by something it does not know"
    assert stale[MOISTURE].value == 0.55, "the last reading is still carried, and still shown"


def test_stale_and_unmeasured_are_told_apart(monkeypatch):
    """They differ in fact, so they differ in the ledger. One has never looked; the other looked
    and let the answer go cold — the same repair, and not the same situation."""
    agent, st = _fern(monkeypatch, value=0.55)
    _age_the_reading(st)
    by_state = {g.state for g in desires_of(desires_build(st, "fern").query_union, st.query, FERN, "fern") if not g.is_duty}
    assert by_state == {"stale", "unmeasured"}, \
        "moisture was read and went cold; temperature was never read at all"


def test_the_want_fires_as_a_shape_and_does_not_refuse_the_boot(monkeypatch):
    """A want is checkable by the same machinery that checks legitimacy, and must never refuse.

    Both halves are asserted because they were separately wrong while this was built. pySHACL
    ignores `sh:severity` on a `sh:sparql` constraint and honours the NODE shape's — measured
    both ways — so the want first reported as `sh:Violation` and stopped a dry agent from
    starting, which is precisely the failure the severity split exists to prevent.
    """
    from agent.ontology import INSTRUMENTS_GRAPH, SENSED_GRAPH, beliefs_graph
    from agent.validate import _shapes_and_vocabulary, conforms, graph_from

    agent, st = _fern(monkeypatch, value=0.55)
    _age_the_reading(st)
    data = graph_from(st, *st.public_graphs(), SENSED_GRAPH,
                      INSTRUMENTS_GRAPH)
    from agent import effects
    for triple in desires_build(st, "fern").construct(
            "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
        data.add(effects._triple(triple))

    ok, _ = conforms(data, focus=FERN)
    assert ok, "a want must never refuse a boot — the agent has to run to repair it"

    ontology, _ = _shapes_and_vocabulary()
    mine = rdflib.Graph()
    for shape in set(data.subjects(rdflib.RDF.type, _SH.NodeShape)):
        mine += data.cbd(shape)
    _, results, _ = shacl_validate(data + ontology, shacl_graph=mine + ontology,
                                   advanced=True, inference="none")
    stale = [r for r in results.subjects(rdflib.RDF.type, _SH.ValidationResult)
             if "no longer evidence about now" in str(results.value(r, _SH.resultMessage))]
    assert stale, "the shape must actually fire — a want that never reports is not a want"
    assert all(str(results.value(r, _SH.resultSeverity)).endswith("ShouldBecome") for r in stale)


def test_a_property_with_no_sensor_holds_no_freshness_want(monkeypatch):
    """The decision this rule takes, and why it is not an oversight.

    An epistemic want in a property nothing measures could never be satisfied: it would sit at
    maximum urgency for ever, top every ranking a person or a model reads, and inflate the
    `unactionable` count the dashboards carry — training a reader to ignore the top row, which
    is the failure that count exists to prevent. The case is already reported once, by the shape
    that says a desire exists in a property this agent polls no sensor for.

    `world/loner`'s zz plant is exactly that: it states ranges for light and humidity nothing
    reads. Its gardener must hold freshness wants for what it polls and for nothing else.
    """
    from agent.store import bindings

    st = genesis_store(world="loner")
    wants = desires_build(st, "gardener")
    rows = bindings(wants.query_union("""
        SELECT ?property WHERE {
          ?agent <http://example.org/agora#holds> ?shape .
          ?shape <http://example.org/agora#violationIs> <http://example.org/agora#Stale> ;
                 <http://www.w3.org/ns/ssn/forProperty> ?property }"""))
    wanted = {r["property"].rsplit("#", 1)[-1] for r in rows}
    polled = {r["p"].rsplit("#", 1)[-1] for r in bindings(st.query("""
        SELECT ?p WHERE { ?agent <http://example.org/agora/sensing#polls> ?s .
                          ?s <http://www.w3.org/ns/sosa/observes> ?p }"""))}
    assert wanted, "the gardener polls sensors, so it wants their readings fresh"
    assert wanted == polled, \
        "and wants freshness in exactly what it can look at — no want it could never satisfy"


def test_an_instrument_pointed_at_something_i_do_not_act_for_is_still_watched(monkeypatch):
    """The regression this nearly shipped with, pinned.

    `world/loner`'s gardener polls a water butt it does not act for: it holds a region in the
    zz plant's moisture and none in the butt's level. Freshness was first derived from the
    SUBJECT's stated ranges, matching the region's premise — which left the butt with no want,
    and since the keeper pursues desires rather than sweeping noticed gaps, nothing would have
    watched it at all. `notices()` covered every sensor, and what replaces it must cover the
    same ground.

    Asserted through the keeper, not the query, because the ledger is where the loss would
    have shown: a commitment to look that stopped being made.
    """
    gardener = build_agent("gardener", genesis_store(world="loner"), monkeypatch)
    keeper = next(m for m in gardener.modules if m.name == "intention")
    keeper.deliberate_on_gaps()

    watched = {s.observed_property.rsplit("#", 1)[-1] for s in keeper.standing()
               if s.means.endswith("Observe")}
    assert "StoredLitres" in watched, \
        "the butt is polled, so its level is wanted current — stake or no stake"
    assert "SoilMoisture" in watched, "and the plant it does act for, as ever"
