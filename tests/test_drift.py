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


def _gardener(monkeypatch, moisture=0.30):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): moisture}, world="loner")
    genesis.classify_own_graphs(st, "gardener")
    return runtime.Agent("gardener", st=st)


def _dried(agent, elapsed: float):
    """What the world's own rule says the pot reaches, left alone for `elapsed` seconds."""
    rule = effects.drifts_of(agent.beliefs)[0]
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

    assert _dried(agent, 86400.0)[0] == pytest.approx(0.27), "a day at three hundredths"
    assert _dried(agent, 43200.0)[0] == pytest.approx(0.285), "and half a day, half of it"


def test_the_reading_it_dries_is_the_one_it_replaces(monkeypatch):
    """The sensed graph holds one node per (subject, property), so a drift that added a reading
    without taking the old one would leave two results on one node — the same invariant every
    effect's `orexis:retracts` leans on."""
    agent = _gardener(monkeypatch, moisture=0.30)

    _, retracted = _dried(agent, 86400.0)
    assert retracted, "the reading it drifts from is retracted"
    assert any(t.predicate.value.endswith("hasSimpleResult") for t in retracted)


def test_a_pot_does_not_dry_past_empty(monkeypatch):
    """The one bound the domain knows without asking anything: a fraction of saturation has a
    floor at nothing, and a week of drying does not make a pot owe water."""
    agent = _gardener(monkeypatch, moisture=0.05)

    assert _dried(agent, 7 * 86400.0)[0] == pytest.approx(0.0)


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

    assert _dried(agent, 86400.0) == (None, []), \
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
            "SELECT (3600 AS ?seconds) WHERE {{ }}" }} }}
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
            "SELECT (3600 AS ?seconds) WHERE {{ }}" }} }}
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
            "SELECT (3600 AS ?seconds) WHERE {{ }}" }} }}
        WHERE {{ GRAPH <{ACTIONS_GRAPH}> {{ <{OBSERVING}> <{LANDS}> ?t }} }}""")
    timed = Planner(agent, agent.me)
    timed.plan(desire)

    verdicts = [v for _, row, _, v in timed._weighed if str(row.action) == OBSERVING]
    assert any(v != trace.SEEN for v in verdicts), \
        f"an hour passed inside every look and not one reached anywhere new: {set(verdicts)}"
