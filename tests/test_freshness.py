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


from conftest import sensing_of, open_round_for, desires_build, MOISTURE, build_agent, genesis_store

FERN = "http://example.org/orexis/world/simulation#fern_agent"
_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


def _fern(monkeypatch, value=0.55):
    """A fern with a reading and a sensing module that has published its horizon."""
    st = genesis_store({("fern", MOISTURE): value})
    agent = build_agent("fern", st, monkeypatch)
    next(m for m in agent.modules if m.name == "subscribing").start()
    return agent, st


def _age_the_reading(st, hours=3):
    from orexis_agent_progression.ontology import STATE_GRAPH

    old = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    st.update(f"""
        DELETE {{ GRAPH <{STATE_GRAPH}> {{ ?o <http://www.w3.org/ns/sosa/resultTime> ?t }} }}
        INSERT {{ GRAPH <{STATE_GRAPH}> {{ ?o <http://www.w3.org/ns/sosa/resultTime>
                 "{old}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}
        WHERE  {{ GRAPH <{STATE_GRAPH}> {{ ?o <http://www.w3.org/ns/sosa/resultTime> ?t }} }}""")


def test_the_horizon_the_shape_reads_is_the_one_the_module_computes(monkeypatch):
    """One definition, which is the whole reason the horizon is published at all.

    `stale_after_s` works it out from the rhythm in force — the board's acknowledgement where it
    gives one, the agent's intent where it does not, the slowest cadence where neither — and
    none of that was ever written down. A shape cannot run a method, so the alternatives were a
    second copy of the fallback chain in SPARQL, free to drift, or a baked constant, wrong the
    moment urgency re-commands the cadence. This asserts the third way stayed true: what is in
    the graph is what the method returns.
    """
    from orexis_capability_sensing.terms import INSTRUMENTS_GRAPH
    from orexis_agent_progression.store import bindings
    from orexis_capability_sensing.terms import STALE_AFTER_S

    agent, st = _fern(monkeypatch)
    sensing = next(m for m in agent.modules if m.name == "subscribing")

    published = {r["s"]: int(r["h"]) for r in bindings(st.query(
        f"SELECT ?s ?h WHERE {{ GRAPH <{INSTRUMENTS_GRAPH}> {{ ?s <{STALE_AFTER_S}> ?h }} }}"))}
    assert published, "a sensor with no published horizon is a want that can never fire"
    for sensor in sensing.sensors:
        assert published[sensor.uri] == sensing.stale_after_s(sensor.subject, sensor.observes)


def test_a_reading_past_the_horizon_is_stale_where_a_fresh_one_is_met(monkeypatch):
    """The same number, two different wants — the age is what separates them.

    0.55 sits inside fern's 0.45-0.65, so while it is fresh there is nothing to want. Aged
    past the horizon it is not suddenly wrong, it is no longer EVIDENCE — and that is the
    FRESHNESS want's verdict, sensing's judgment through the measure it declares: maximal,
    for the same reason an unread property's is. The STAKE judges the number it has
    (sensing-owns-the-reading-pipeline): 0.55 is still inside the region, so it stays met,
    and not knowing is the epistemic want beside it, which `propose_about` answers first.
    """
    agent, st = _fern(monkeypatch, value=0.55)
    def wants():
        mine = [g for g in sensing_of(agent).desires() if g.observed_property == MOISTURE]
        return (next(g for g in mine if g.is_epistemic), next(g for g in mine if not g.is_epistemic))
    look, stake = wants()
    assert look.state == "met" and look.urgency == 0.0
    assert stake.state == "met"

    _age_the_reading(st)
    look, stake = wants()
    assert look.state == "stale"
    assert look.urgency == 1.0, \
        "not knowing is not knowing — scaling it by a distance the agent no longer trusts " \
        "would rank it by something it does not know"
    assert look.value == 0.55, "the last reading is still carried, and still shown"
    assert stake.state == "met", "the stake judges the number it has; staleness is sensing's"


def test_stale_and_unmeasured_are_told_apart(monkeypatch):
    """They differ in fact, so they differ in the ledger. One has never looked; the other looked
    and let the answer go cold — the same repair, and not the same situation."""
    agent, st = _fern(monkeypatch, value=0.55)
    _age_the_reading(st)
    by_state = {g.state for g in sensing_of(agent).desires() if g.is_epistemic}
    assert by_state == {"stale", "unmeasured"}, \
        "moisture was read and went cold; temperature was never read at all"


def test_the_want_fires_as_a_shape_and_does_not_refuse_the_boot(monkeypatch):
    """A want is checkable by the same machinery that checks legitimacy, and must never refuse.

    Both halves are asserted because they were separately wrong while this was built. pySHACL
    ignores `sh:severity` on a `sh:sparql` constraint and honours the NODE shape's — measured
    both ways — so the want first reported as `sh:Violation` and stopped a dry agent from
    starting, which is precisely the failure the severity split exists to prevent.
    """
    from orexis_capability_sensing.terms import INSTRUMENTS_GRAPH
    from orexis_agent_progression.ontology import STATE_GRAPH, beliefs_graph
    from agent.validate import _shapes_and_vocabulary, conforms, graph_from

    agent, st = _fern(monkeypatch, value=0.55)
    _age_the_reading(st)
    data = graph_from(st, *st.public_graphs(), STATE_GRAPH,
                      INSTRUMENTS_GRAPH)
    from orexis_agent_deliberation import effects
    for triple in desires_build(st, "fern").construct(
            "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
        data.add(effects._triple(triple))

    ok, _ = conforms(data, focus=FERN)
    assert ok, "a want must never refuse a boot — the agent has to run to repair it"

    assert _fires(data), "the shape must actually fire — a want that never reports is not a want"


def _fires(data) -> list:
    """The freshness results this data produces when the want's shape is validated DIRECTLY.

    The planner's road (#472): a met-test enters no `conforms()` pass — the metWhen linkage
    keeps it out, which is what lets it carry no severity — so firing is proven here the way
    the planner asks: over the shapes the data holds, results at whatever severity the
    engine defaults to.
    """
    from agent.validate import _shapes_and_vocabulary

    ontology, _ = _shapes_and_vocabulary()
    mine = rdflib.Graph()
    for shape in set(data.subjects(rdflib.RDF.type, _SH.NodeShape)):
        mine += data.cbd(shape)
    _, results, _ = shacl_validate(data + ontology, shacl_graph=mine + ontology,
                                   advanced=True, inference="none")
    stale = [r for r in results.subjects(rdflib.RDF.type, _SH.ValidationResult)
             if "reads now" in str(results.value(r, _SH.resultMessage))]
    return stale


def test_a_horizon_nobody_published_leaves_the_want_unmet_not_met(monkeypatch):
    """The direction a shape about knowledge has to fail in (#342), pinned by taking the
    horizon away.

    The met-test used to hunt for a reading whose `resultTime` plus the horizon had PASSED,
    and a shape that looks for a bad reading is satisfied by the absence of any reading — and
    by the absence of the horizon it would have judged one against. Measured on pySHACL
    0.40.1 by renaming the term: `conforms` flipped from False to True, so an agent whose
    sensing module had not yet said what it treats as stale believed every reading current,
    for ever, with nothing red anywhere.

    Saying what the agent WANTS instead of what would disappoint it fixes both at the root: a
    fresh reading exists, or it does not. This asserts the case that used to lie — a reading
    that is current by any reasonable reading of the clock, with no horizon stated at all.
    """
    from orexis_capability_sensing.terms import INSTRUMENTS_GRAPH
    from orexis_agent_progression.ontology import STATE_GRAPH
    from agent.validate import graph_from
    from orexis_capability_sensing.terms import STALE_AFTER_S
    from orexis_agent_deliberation import effects

    agent, st = _fern(monkeypatch, value=0.55)          # horizons published by `start()`
    st.update(f"DELETE WHERE {{ GRAPH <{INSTRUMENTS_GRAPH}> "
              f"{{ ?s <{STALE_AFTER_S}> ?h }} }}")

    data = graph_from(st, *st.public_graphs(), STATE_GRAPH, INSTRUMENTS_GRAPH)
    for triple in desires_build(st, "fern").construct(
            "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
        data.add(effects._triple(triple))

    assert _fires(data), \
        "with no horizon there is no recent-enough, so nothing is known to be current — a " \
        "want that reads MET here is a want that can never be short"
    assert next(d for d in agent.pursuing()
                if d.is_epistemic and d.observed_property == MOISTURE).urgency == 1.0, \
        "and the measure fails the same way round, or the search would rank it as content"


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
    from orexis_agent_progression.store import bindings

    st = genesis_store(world="loner")
    wants = desires_build(st, "gardener")
    rows = bindings(wants.query_union("""
        SELECT ?property WHERE {
          ?agent <http://example.org/orexis#holds> ?shape .
          ?shape <http://example.org/orexis#violationIs> <http://example.org/orexis#Stale> ;
                 <http://www.w3.org/ns/ssn/forProperty> ?property }"""))
    wanted = {r["property"].rsplit("#", 1)[-1] for r in rows}
    polled = {r["p"].rsplit("#", 1)[-1] for r in bindings(st.query("""
        SELECT ?p WHERE { ?agent <http://example.org/orexis/sensing#polls> ?s .
                          ?s <http://www.w3.org/ns/sosa/observes> ?p }"""))}
    assert wanted, "the gardener polls sensors, so it wants their readings fresh"
    assert wanted == polled, \
        "and wants freshness in exactly what it can look at — no want it could never satisfy"


def test_an_instrument_pointed_at_something_i_do_not_act_for_is_still_wanted_current(monkeypatch):
    """The regression this nearly shipped with, and the limit that sits beside it.

    `world/loner`'s gardener polls a water butt it does not act for: it holds a region in the
    zz plant's moisture and none in the butt's level. Freshness was first derived from the
    SUBJECT's stated ranges, matching the region's premise — which left the butt with no want
    at all. The premise is the INSTRUMENT, so the want exists, and that half is unchanged.

    What is NOT unchanged is what the gardener does about it, and the change is the point of
    the mode-conditional affordance. The butt's level is a push device: it announces, and
    there is nothing to ask. So the want stands, hot, and the search answers NOTHING — no
    lever this agent holds points at it — which is the sentence that means *equip me*. What
    happened before was worse than nothing: an Observe intention adopted every patience
    period, `sense_now()` returning having done nothing, and the commitment outwaited and
    re-adopted for ever, in silence.
    """
    gardener = build_agent("gardener", genesis_store(world="loner"), monkeypatch)
    keeper = next(m for m in gardener.modules if m.name == "intention")
    butt = next(d for d in gardener.pursuing()
                if d.is_epistemic and d.observed_property.endswith("StoredLitres"))
    assert butt.urgency == 1.0, "the butt is polled, so its level is wanted current"

    keeper.agent.deliberator.deliberate_on_gaps()

    about = {w.uri: w.observed_property for w in sensing_of(gardener).desires()}
    watched = {about[s.want].rsplit("#", 1)[-1] for s in keeper.standing()
               if s.action.endswith("Observing")}
    assert "SoilMoisture" in watched, "the probe can be asked, so the look is committed to"
    assert "StoredLitres" not in watched, \
        "and the butt cannot, so nothing is committed to — a lever an agent cannot pull is " \
        "not a lever, and an intention nothing can carry out is not an intention"
    #  AND THE NUDGE ACTUALLY LEAVES, which is the other half of the same silence. This agent
    #  holds two sensing modules, and `provider` returns whichever comes first — the listener,
    #  here, whose `sense_now` is an empty method. So the look was committed to and nothing
    #  went out, every patience period, with every module behaving as written.
    assert any(topic.endswith("moisture_probe/command") and payload == {"sense": True}
               for topic, payload, _ in gardener.sent), \
        "the module that CAN ask is the one that has to hear about it"
    assert gardener.deliberator.propose_for(butt) is None, \
        "said as a decision rather than as an oversight"


def test_a_listener_reports_the_want_it_cannot_repair_as_unequipped(monkeypatch):
    """The mode-conditional rule's own fixture, which the gardener's butt cannot be.

    The butt is unreachable twice over — a push device, AND pointed at a subject the gardener
    does not act for, which the Observe row's walk already excludes. So a test written on it
    passes whether or not the sense mode is consulted. `world/simulation`'s supplier is the
    clean case: it ACTS FOR the barrel and its only instrument is the float switch, so the
    row's walk holds at every hop and the sense mode is the only thing standing between it
    and a lever that does nothing.

    The verdict is NOT_BETTER rather than NOTHING, and the difference between the two agents
    is worth stating because both are honest. The gardener holds NO lever at all on the
    butt's level, so its trace says `no candidate` — equip me. The supplier holds one, the
    Acquire that refills the barrel, and buying water does not tell you how much you have:
    the lever is weighed, the world it reaches is no better, and the pass says so. Neither
    reads as a look that happened, which is what the row used to buy.
    """
    from orexis_agent_deliberation import planner as search
    from orexis_agent_deliberation import trace

    supplier = build_agent("supplier", genesis_store(), monkeypatch)
    open_round_for(supplier, "supplier")   # the upstream lever exists only while a round is open
    want = next(d for d in supplier.pursuing()
                if d.is_epistemic and d.observed_property.endswith("StoredLitres"))

    assert supplier.deliberator.propose_for(want) is None
    assert trace.outcomes(supplier.beliefs.query_union) == {search.NOT_BETTER: 1}, \
        "weighed what it holds and found none of it answers — not: I looked"
