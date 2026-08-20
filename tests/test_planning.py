"""Planning by simulation: the world a lever would make, and whether it is worth reaching.

The reflex asks whether a lever points the right way. These are about the question that
replaces it — whether taking it leaves the agent BETTER OFF — and about the four constraints
the decision record makes non-negotiable. See
knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md.

Written against `world/loner`, and not by preference: it holds the only agent in any shipped
world whose lever can be simulated at all. The gardener owns its butt and its pump, so its
Actuate has an effect rule; every plant in `world/simulation` BUYS its water, and Acquire has
no rule for anyone to reason with. That asymmetry is the subject of one test here rather than
an inconvenience to route around, because it decides what the planner may conclude.
"""

from __future__ import annotations

import time

from agent import effects
from packages.capability.deliberation import search
from packages.capability.deliberation.search import Planner

from conftest import build_agent, genesis_store

MOISTURE = "http://example.org/agora/water#SoilMoisture"
GARDENER = "http://example.org/agora/world/loner#gardener"
#  zz states 0.1–0.3, survives 0.02–0.45, and the gardener aims at the centre.
WET, DRY, CONTENT = 0.42, 0.04, 0.20


def _gardener(monkeypatch, moisture):
    monkeypatch.setenv("AGORA_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): moisture}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    desire = next(m for m in agent.modules if m.name == "desire")
    goal = next(g for g in agent.goals() if g.observed_property == MOISTURE)
    return agent, Planner(agent, desire, agent.me).plan(goal), goal


def test_a_lever_that_would_overshoot_is_refused_by_simulating_it(monkeypatch):
    """The whole argument for simulation, in the case that motivated it.

    zz at 0.42 sits ABOVE its region, and every test the reflex applies says water it: the
    pump raises moisture, the aim is 0.2, the reading is a gap. Direction matches sign, and
    both are true of a drowning plant — which is how a society floods one while every module
    behaves exactly as written.

    The planner reaches the opposite answer without knowing anything about wetness: it builds
    the world the dose would make, scores it, finds it no better than the one it is in, and
    declines. `not better` is the finding, and it is a DECISION rather than an absence of one.
    """
    _, plan, goal = _gardener(monkeypatch, WET)

    assert goal.state == "unmet"
    assert plan.outcome == search.NOT_BETTER
    assert plan.steps == ()
    assert plan.urgency_after >= plan.urgency_now


def test_a_dose_that_reaches_the_region_is_planned(monkeypatch):
    """And the other side of it, or the test above would pass on a planner that never acts.

    Bone dry at 0.04, one dose sized to the aim, and the simulated world is inside the region
    — so the plan is one step and the urgency it predicts is the urgency the dose would leave.
    """
    _, plan, _ = _gardener(monkeypatch, DRY)

    assert plan.outcome == search.SATISFIED
    assert [s.means for s in plan.steps] == ["http://example.org/agora#Actuate"]
    assert plan.urgency_after < plan.urgency_now


def test_a_goal_already_met_plans_nothing(monkeypatch):
    _, plan, _ = _gardener(monkeypatch, CONTENT)

    assert plan.outcome == search.SATISFIED and plan.steps == ()


def test_a_search_that_could_not_see_every_lever_refuses_to_conclude(monkeypatch):
    """The finding that would have stopped fern buying water, and the rule it forced.

    A plant in `world/simulation` acquires its water: the lever that works is Acquire, and no
    package has stated what Acquire does. So the search sees Observe alone, correctly finds
    that looking does not wet soil, and — before this — reported that nothing helps. The
    reflex was overridden by a conclusion drawn from part of the menu, and the plant stopped
    bidding.

    A search that passed over any lever marks its plan PARTIAL, and a partial plan may not say
    "nothing helps". The deliberator defers, and the reflex answers as it always did — which
    is the honest division: simulation decides where the packages have said enough for it to,
    and nowhere else.
    """
    monkeypatch.setenv("AGORA_WORLD", "simulation")
    st = genesis_store({("fern", MOISTURE): 0.30})
    fern = build_agent("fern", st, monkeypatch)
    desire = next(m for m in fern.modules if m.name == "desire")
    goal = next(g for g in fern.goals() if g.observed_property == MOISTURE)

    plan = Planner(fern, desire, fern.me).plan(goal)
    assert plan.partial, "Acquire has no effect rule, so the menu was not fully simulated"

    reflex = fern.provider("http://example.org/agora/deliberation#DeliberationCapability")
    assert reflex.propose_for(goal) == reflex.propose(MOISTURE, 0.30), \
        "a thirsty plant must still buy — the search defers where it cannot see"


def test_a_possible_world_is_computed_and_nothing_is_written(monkeypatch):
    """The guarantee that makes hypotheses safe: the store never learns anyone imagined this.

    Asserted on the store rather than on the returned graph, because the danger is not that
    the world comes back wrong — it is that building one leaves a trace behind, and a
    predicted reading written into the sensed graph would be indistinguishable from a real one
    the moment anybody asked.
    """
    monkeypatch.setenv("AGORA_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): DRY}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    from agent.ontology import SENSED_GRAPH, beliefs_graph
    from agent.validate import graph_from

    before = graph_from(st, *st.public_graphs(), beliefs_graph("gardener"), SENSED_GRAPH)
    world = effects.world_after(
        before, st, "http://example.org/agora#Actuate",
        me=f"<{GARDENER}>", subject="<http://example.org/agora/world/loner#zz>",
        property=f"<{MOISTURE}>", litres=0.3, value=DRY,
        beliefs=f"<{beliefs_graph('gardener')}>")

    after = graph_from(st, *st.public_graphs(), beliefs_graph("gardener"), SENSED_GRAPH)
    assert len(after) == len(before), "the store is untouched by having imagined something"
    assert world is not before and len(world) > 0

    import rdflib
    sosa = rdflib.Namespace("http://www.w3.org/ns/sosa/")
    predicted = [float(o) for o in world.objects(None, sosa.hasSimpleResult)]
    real = [float(o) for o in after.objects(None, sosa.hasSimpleResult)]
    assert predicted != real, "the imagined world differs from the one on disk"
    assert DRY in real and DRY not in predicted, \
        "and it differs by the dose: the old reading is retracted, not left beside the new one"


def test_a_planning_pass_costs_about_a_second(monkeypatch):
    """The assumption most likely to sink this, pinned as a number rather than a hope.

    A pySHACL run per candidate on a Raspberry Pi is what the record warned about, and the
    measurement is why the goal shape is validated ALONE: one goal's shape costs 0.083s where
    everything the packages ship costs 1.73s, twenty times more, for an answer about rules no
    effect could have broken. Legality is asked once, of the winner.

    The bound is deliberately loose — this is a Pi, under whatever else is running — and it
    would still catch the failure that matters: a pass that had started validating the whole
    rulebook per candidate would take twenty seconds, not two.
    """
    start = time.monotonic()
    _gardener(monkeypatch, DRY)
    assert time.monotonic() - start < 10.0
