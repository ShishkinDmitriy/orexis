"""What the world does while nobody acts (#592).

A pot dries whether or not its agent waters it. `water:driesPerDay` has been stated on every
plant since #164 and read by nothing in planning, so a search could imagine an hour passing and
find the pot exactly as wet as when it started.

A DRIFT is that, declared: the grammar of an effect — a construct and its retraction — with
nobody taking it, parameterised by `$elapsed`, the seconds the world has had to itself. It is a
rule run AT THE NODE and its answer is part of where the plan stands, which is what separates it
from a forecast: the rate is exogenous and the result is not, since a pot dries from wherever
the plan has left it (planning-branches-on-action-forecasting-on-belief).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agent import genesis, runtime
from conftest import genesis_store
from orexis_agent_deliberation import effects
from orexis_agent_progression.ontology import ACTIONS_GRAPH, STATE_GRAPH, beliefs_graph
from orexis_agent_progression.store import Raw, bindings

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
OBSERVING = "http://example.org/orexis/sensing#Observing"
LANDS = "http://example.org/orexis#landsAfter"
AT = Raw('"2026-09-13T12:00:00+00:00"^^xsd:dateTime')
DAY = 600.0    # the loner's day, ten bench minutes (`orexis:secondsPerDay`): a rate per day is in it


def _gardener(monkeypatch, moisture=0.30):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): moisture}, world="loner")
    genesis.classify_own_graphs(st, "gardener")
    return runtime.Agent("gardener", st=st)


def _dried(agent, elapsed: float):
    """What the world's own rule says the pot reaches, left alone for `elapsed` seconds."""
    rule = next(r for r in effects.drifts_of(agent.beliefs) if r["drift"].endswith("#Drying"))
    added, retracted = effects.drift(
        agent.beliefs, rule, elapsed=elapsed, when=datetime.now(timezone.utc),
        me=f"<{agent.me.uri}>", subject=f"<{agent.me.acts_for}>", about=f"<{MOISTURE}>",
        state=f"<{STATE_GRAPH}>", beliefs=f"<{beliefs_graph('gardener')}>",
        litres="0.0", lands=AT)
    values = [float(t.object.value) for t in added
              if t.predicate.value.endswith("hasSimpleResult")]
    return (values[0] if values else None), retracted


def test_a_pot_dries_by_what_its_world_says_it_loses(monkeypatch):
    """The rate is the world's, in the domain's own words, and the arithmetic is the domain's
    too — `water:driesPerDay` on the pot, which the loner world states at 0.03."""
    agent = _gardener(monkeypatch, moisture=0.30)

    assert _dried(agent, DAY)[0] == pytest.approx(0.27), "a day at three hundredths"
    assert _dried(agent, DAY / 2)[0] == pytest.approx(0.285), "and half a day, half of it"


def test_the_reading_it_dries_is_the_one_it_replaces(monkeypatch):
    """The sensed graph holds one node per (subject, property), so a drift that added a reading
    without taking the old one would leave two results on one node — the same invariant every
    effect's `orexis:retracts` leans on."""
    agent = _gardener(monkeypatch, moisture=0.30)

    _, retracted = _dried(agent, DAY)
    assert retracted, "the reading it drifts from is retracted"
    assert any(t.predicate.value.endswith("hasSimpleResult") for t in retracted)


def test_a_pot_does_not_dry_past_empty(monkeypatch):
    """The one bound the domain knows without asking anything: a fraction of saturation has a
    floor at nothing, and a week of drying does not make a pot owe water."""
    agent = _gardener(monkeypatch, moisture=0.05)

    assert _dried(agent, 7 * DAY)[0] == pytest.approx(0.0)


def test_nothing_drifts_where_no_time_passes(monkeypatch):
    """Every shipped step lands at once but a market bid, so today this is the ordinary case —
    and it is why every shipped world plans exactly as it did. A step that gives the world no
    seconds gives it nothing to do."""
    agent = _gardener(monkeypatch, moisture=0.30)

    assert _dried(agent, 0.0) == (None, [])


def test_a_dosed_pot_does_not_drift_because_it_has_no_number(monkeypatch):
    """The honest limit, pinned where it can be read. A reading the agent OBSERVED carries a
    number; one an effect PREDICTED carries a band and no value (#579), so there is nothing to
    subtract a rate from. A pot left alone dries; a pot already dosed keeps the band its dose
    declared, and the plan learns the rest when the world answers.
    """
    agent = _gardener(monkeypatch, moisture=0.30)
    agent.beliefs.update(f"""DELETE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:hasSimpleResult ?v }} }}
        WHERE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:observedProperty <{MOISTURE}> ;
                                          sosa:hasSimpleResult ?v }} }}""")

    assert _dried(agent, DAY) == (None, []), \
        "a band alone says where the reading is, not how far into it"


def test_a_step_that_takes_time_leaves_a_drier_pot(monkeypatch):
    """The search's side: a drift runs at the node, over the seconds the step gave the world.

    Asked of a LOOK given a minute, because a look is the one shipped effect that carries the
    number forward — it predicts the value it found — so there is something left to dry. A dose
    declares a band instead, which is the limit above.
    """
    from orexis_agent_deliberation.planner import Planner

    #  A DRY pot, because a met want returns before it forks anything: there is no search to
    #  watch when the agent is already content.
    agent = _gardener(monkeypatch, moisture=0.04)
    agent.beliefs.update(f"""DELETE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}
        INSERT {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}>
            "SELECT (25 AS ?seconds) WHERE {{ }}" }} }}
        WHERE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}""")
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    planner.plan(desire)

    looked = [m for m in planner._nodes
              if m.taken and str(m.taken[-1].action) == OBSERVING]
    assert looked, "the gardener polls a probe, so looking is on its menu"
    values = [float(t.object.value) for m in looked for t in m.added
              if t.predicate.value.endswith("hasSimpleResult")]
    assert values and all(v < 0.04 for v in values), \
        f"an hour passed inside that step and the pot is no drier: {values}"
    assert values[0] == pytest.approx(0.04 - 0.03 / 24, abs=1e-6), \
        "by exactly what the world says it loses in an hour"


def test_a_step_leaves_one_reading_per_key_even_when_it_drifts(monkeypatch):
    """The invariant the sensed graph's upsert exists for, met where a drift could break it.

    A drift is asked of the world the step REACHED, so the reading it replaces may be one this
    very step predicted: a look carries the value it found forward, and an hour of drying
    replaces that. Left in, the step would add two readings for one key — and a shape asking
    whether ANY reading sits past an edge would answer about the one the step already
    superseded.
    """
    from orexis_agent_deliberation.planner import Planner

    agent = _gardener(monkeypatch, moisture=0.04)
    agent.beliefs.update(f"""DELETE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}
        INSERT {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}>
            "SELECT (25 AS ?seconds) WHERE {{ }}" }} }}
        WHERE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}""")
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    planner.plan(desire)

    for node in planner._nodes:
        values = [t.object.value for t in node.added
                  if t.predicate.value.endswith("hasSimpleResult")]
        assert len(values) <= 1, f"a step added two readings for one key: {values}"


def test_a_look_that_takes_an_hour_is_somewhere_new(monkeypatch):
    """The consequence worth naming rather than discovering later.

    A look's world used to be its parent's — it predicts the value it found, so its diff nets
    to nothing and cycle detection discards it. Give the step an hour and the world moved while
    it ran, so the look now reaches somewhere genuinely new and the search will keep looking as
    long as its budget lasts. That is not a defect of the drift: it is the truth, and it is
    exactly what [#590](https://github.com/ShishkinDmitriy/orexis/issues/590) is for — a look valued by the narrowing it buys rather than
    kept alive by changing nothing.

    Every shipped world is unaffected: `sensing:Observing` lands at once, so no time passes
    inside it and the look collides as it always did.
    """
    from orexis_agent_deliberation import trace
    from orexis_agent_deliberation.planner import Planner

    agent = _gardener(monkeypatch, moisture=0.04)
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    planner.plan(desire)
    assert {v for _, row, _, v in planner._weighed if str(row.action) == OBSERVING} == {trace.SEEN}, \
        "a look that takes no time reaches the world it started in, as it always has"

    agent.beliefs.update(f"""DELETE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}
        INSERT {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}>
            "SELECT (25 AS ?seconds) WHERE {{ }}" }} }}
        WHERE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}""")
    timed = Planner(agent, agent.me)
    timed.plan(desire)

    verdicts = [v for _, row, _, v in timed._weighed if str(row.action) == OBSERVING]
    assert any(v != trace.SEEN for v in verdicts), \
        f"an hour passed inside every look and not one reached anywhere new: {set(verdicts)}"


def test_a_dose_now_takes_the_time_its_valve_needs(monkeypatch):
    """What #595 found and this closes: a dose landed at nought seconds in every imagined
    world, because its timing is a function of how much is poured and the search does not size
    an act (#579). Unsized, the rule answers the CEILING — the longest that valve can be open —
    which is an over-estimate, and over-estimating is the safe direction for a deadline: it
    refuses a plan that MIGHT be late where nought accepted one that would be.
    """
    from orexis_agent_deliberation.planner import Planner

    agent = _gardener(monkeypatch, moisture=0.04)
    row = bindings(agent.beliefs.query("""SELECT ?cap ?rate WHERE {
        ?lever <http://example.org/orexis/actuation#maxDoseMl> ?cap ;
               <http://example.org/orexis/actuation#mlPerSecond> ?rate }"""))[0]
    ceiling = float(row["cap"]) / float(row["rate"])

    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    plan = planner.plan(desire)

    assert plan.outcome == "satisfied", plan.outcome
    dosed = min((m for m in planner._nodes if m.met), key=lambda m: m.cost)
    assert dosed.landing == pytest.approx(ceiling), \
        f"a dose still lands instantly: {dosed.landing}"
    assert ceiling > 0, "the loner's valve takes real seconds to empty"


# --- and what it does to a reading that carries no number (#612) --------------


DOSING = "http://example.org/orexis/actuation#Dosing"


def _band_only(agent):
    """A reading known by its band and not by a value — what every effect leaves behind."""
    agent.beliefs.update(f"""DELETE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:hasSimpleResult ?v }} }}
        WHERE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:observedProperty <{MOISTURE}> ;
                                          sosa:hasSimpleResult ?v }} }}""")


def _fell(agent, elapsed: float):
    """The bands the band-drift says the reading reaches, left alone for `elapsed` seconds."""
    rule = next(r for r in effects.drifts_of(agent.beliefs) if r["drift"].endswith("DryingABand"))
    added, retracted = effects.drift(
        agent.beliefs, rule, elapsed=elapsed, when=datetime.now(timezone.utc),
        me=f"<{agent.me.uri}>", subject=f"<{agent.me.acts_for}>", about=f"<{MOISTURE}>",
        state=f"<{STATE_GRAPH}>", beliefs=f"<{beliefs_graph('gardener')}>",
        litres="0.0", lands=AT)
    return ({t.object.value.rsplit(".", 1)[-1] for t in added
             if t.predicate.value.endswith("#type") and "band." in t.object.value}, retracted)


def _crossing_s(agent) -> float:
    """How long the region takes to cross, from the world's own numbers: the band's width over
    the rate the pot states. Read rather than pinned, so a world that re-ranges its plant or
    re-states its physics does not fail this."""
    row = bindings(agent.beliefs.query(f"""SELECT ?lo ?hi ?rate WHERE {{
        ?band rdfs:subClassOf sensing:InRegion ; sensing:ofProperty <{MOISTURE}> ;
              sensing:ofSubject ?pot ;
              owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?r .
        ?r owl:onProperty sosa:hasSimpleResult ; owl:someValuesFrom/owl:withRestrictions ?f .
        ?f rdf:rest*/rdf:first/xsd:minInclusive ?lo .
        ?f rdf:rest*/rdf:first/xsd:maxInclusive ?hi .
        ?pot water:driesPerDay ?rate }}"""))[0]
    return (float(row["hi"]) - float(row["lo"])) / float(row["rate"]) * DAY


def test_a_band_falls_when_its_own_crossing_time_has_passed(monkeypatch):
    """The drift the numeric one could not do, and the reason there are two.

    A reading an effect predicted carries a band and no value (#579), so there is nothing to
    subtract a rate from — which left the first drift correct and inert in every shipped world,
    since a plan's first step erases the only number it could work on. What is left to say
    without a value is how long the BAND takes to cross: its own width, from the facets genesis
    minted it with, over the rate the world states.
    """
    agent = _gardener(monkeypatch, moisture=0.30)
    _band_only(agent)
    crossing = _crossing_s(agent)

    assert _fell(agent, crossing * 0.9)[0] == set(), "it has not had time to cross its band"
    reached, retracted = _fell(agent, crossing * 1.1)
    assert reached == {"below"}, "a full width's worth of drying takes it out of the region"
    assert retracted, "and the reading it replaces goes, as every reading-mover's does"


def test_the_crossing_time_is_the_bands_own_width_over_the_worlds_rate(monkeypatch):
    """Nothing new is stated for this. The width comes from the facets a band was minted with
    and the rate from the plant, so a world that re-ranges its bed or re-states its physics
    changes the answer by changing what it already says."""
    agent = _gardener(monkeypatch, moisture=0.30)
    _band_only(agent)
    crossing = _crossing_s(agent)

    assert crossing == pytest.approx(0.2 / 0.03 * DAY), \
        "the loner's region is 0.1-0.3 and its pot loses three hundredths a day"
    assert _fell(agent, crossing - 1.0)[0] == set()
    assert _fell(agent, crossing + 1.0)[0] == {"below"}


def test_a_reading_already_below_does_not_fall_further(monkeypatch):
    """The right answer rather than a gap: the below band is open at the bottom, so it has no
    width to cross and there is no band under it to reach."""
    agent = _gardener(monkeypatch, moisture=0.04)          # below the region already
    _band_only(agent)

    assert _fell(agent, 365 * DAY)[0] == set(), "a year below is still below"


def test_a_step_long_enough_leaves_a_dosed_pot_below_again(monkeypatch):
    """The search's side, asked of a dose given a week — the shortest way to put a band-only
    reading and a long elapsed in one node, since a dose is what erases the number and every
    shipped step is far too quick to cross a band. What it shows is the composition: the
    effect declares the band its act reaches, and the world takes it away again.
    """
    from orexis_agent_deliberation.planner import Planner

    agent = _gardener(monkeypatch, moisture=0.04)
    week = int(_crossing_s(agent) * 1.5)
    agent.beliefs.update(f"""DELETE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{DOSING}> <{LANDS}> ?t }} }}
        INSERT {{ GRAPH <{ACTIONS_GRAPH}> {{ <{DOSING}> <{LANDS}>
            "SELECT ({week} AS ?seconds) WHERE {{ }}" }} }}
        WHERE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{DOSING}> <{LANDS}> ?t }} }}""")
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)
    planner.plan(desire)

    dosed = [m for m in planner._nodes if m.taken and str(m.taken[-1].action) == DOSING]
    assert dosed, "a dry pot is dosed"
    bands = {t.object.value.rsplit(".", 1)[-1] for m in dosed for t in m.added
             if t.predicate.value.endswith("#type") and "band." in t.object.value}
    assert bands == {"below"}, \
        f"a dose that took a week left the pot in the region it cannot still be in: {bands}"
