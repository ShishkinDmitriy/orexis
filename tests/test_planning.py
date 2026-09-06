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

import pytest
import rdflib

from orexis_agent_deliberation import effects
from orexis_agent_progression.ontology import DELIBERATION_GRAPH, STATE_GRAPH
from orexis_agent_progression.store import bindings
from orexis_agent_deliberation import planner as search, trace
from orexis_agent_deliberation.planner import Planner

from orexis_capability_sensing.regions import ObservedDesire
from conftest import stake_of, build_agent, genesis_store, open_round_for, write_reading

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
GARDENER = "http://example.org/orexis/world/loner#gardener"
DOSING = "http://example.org/orexis/actuation#Dosing"
OBSERVING = "http://example.org/orexis/sensing#Observing"
#  zz states 0.1–0.3, survives 0.02–0.45, and the gardener aims at 0.18 — dry-side of centre,
#  deliberately (see knowledge/domain/aim.md), which is what makes this world the live case of
#  the aim-vs-centre finding: the measure scores distance from 0.18, so CONTENT is comfortable
#  and still carries a little urgency, and AT_PICK alone carries none.
WET, DRY, CONTENT, AT_PICK = 0.42, 0.04, 0.20, 0.18


def _gardener(monkeypatch, moisture):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): moisture}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    #  THE STAKE, said out loud. Two wants are about this property now — the region zz should
    #  sit in, and that the probe has reported recently — and asking for "the want about
    #  moisture" would take whichever happened to be hotter, which on a dry pot is the wrong
    #  one and answers a different question. These tests are about doses.
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    return agent, Planner(agent, agent.me).plan(desire), desire


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
    _, plan, desire = _gardener(monkeypatch, WET)

    assert desire.state == "unmet"
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
    assert [s.action for s in plan.steps] == ["http://example.org/orexis/actuation#Dosing"]
    assert plan.urgency_after < plan.urgency_now


def test_a_desire_already_met_plans_nothing(monkeypatch):
    _, plan, _ = _gardener(monkeypatch, CONTENT)

    assert plan.outcome == search.SATISFIED and plan.steps == ()


def test_met_is_the_label_and_the_aim_is_the_target_with_a_deadband_at_the_pick(monkeypatch):
    """The half a-desire-states-its-own-measure adds: a met desire with urgency still searches.

    zz at 0.12 is INSIDE its region (0.1-0.3) and below the gardener's 0.18 pick, so the shape
    is met and the measure is not zero — the situation the old root short-circuit collapsed:
    it returned SATISFIED without searching, the deliberator deferred to the reflex over a
    comment claiming the reflex would also propose nothing, and the reflex steered to the aim
    unsatisficed. Now the SEARCH steers to the pick: a dose is proposed, sized and simulated,
    and the outcome label stays SATISFIED because met is the shape's verdict, not the search's.

    At the pick the deadband arrives from satisficing rather than from a tolerance anybody
    chose: the dose sizes to ~0, the actor's litres<=EPS refusal makes the effect predict no
    change, the candidate is pruned as the world already stood in — no move, as a DECISION the
    deliberator answers (None) rather than a hand-off to the reflex.
    """
    agent, plan, desire = _gardener(monkeypatch, 0.12)
    assert desire.state == "met" and desire.urgency > 0, \
        "met and urgent must be expressible at once — that is what the measure bought"
    assert plan.outcome == search.SATISFIED
    assert [s.action for s in plan.steps] == [DOSING], \
        "inside the region and off the pick, a dose is proposed"
    assert plan.urgency_after < plan.urgency_now
    assert agent.deliberator.propose_for(desire) == DOSING

    at_pick, plan2, desire2 = _gardener(monkeypatch, AT_PICK)
    assert desire2.urgency == 0.0
    assert plan2.outcome == search.SATISFIED and plan2.steps == ()
    assert at_pick.deliberator.propose_for(desire2) is None, \
        "at the pick: no move, decided — not deferred to a reflex that might disagree"


def test_a_possible_world_is_computed_and_nothing_is_written(monkeypatch):
    """The guarantee that makes hypotheses safe: the store never learns anyone imagined this.

    Asserted on the store rather than on the returned graph, because the danger is not that
    the world comes back wrong — it is that building one leaves a trace behind, and a
    predicted reading written into the sensed graph would be indistinguishable from a real one
    the moment anybody asked.
    """
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): DRY}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    from orexis_agent_progression.ontology import STATE_GRAPH, beliefs_graph
    from agent.validate import graph_from

    before = graph_from(st, *st.public_graphs(), beliefs_graph("gardener"), STATE_GRAPH)
    world = effects.world_after(
        before, st, "http://example.org/orexis/actuation#Dosing",
        me=f"<{GARDENER}>", subject="<http://example.org/orexis/world/loner#zz>",
        about=f"<{MOISTURE}>", litres=0.3, value=DRY,
        beliefs=f"<{beliefs_graph('gardener')}>")

    after = graph_from(st, *st.public_graphs(), beliefs_graph("gardener"), STATE_GRAPH)
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
    measurement is why the desire shape is validated ALONE: one desire's shape costs 0.083s where
    everything the packages ship costs 1.73s, twenty times more, for an answer about rules no
    effect could have broken. Legality is asked once, of the winner.

    The bound is deliberately loose — this is a Pi, under whatever else is running — and it
    would still catch the failure that matters: a pass that had started validating the whole
    rulebook per candidate would take twenty seconds, not two.
    """
    start = time.monotonic()
    _gardener(monkeypatch, DRY)
    assert time.monotonic() - start < 10.0


def test_a_step_is_simulated_from_where_it_is_taken(monkeypatch):
    """A plan's second step starts where its first one finished, or depth 2 is a number.

    The bindings a rule is filled with were first computed from the GOAL and reused at every
    depth, so a second dose predicted `0.04 + 0.21/conversion` exactly as the first had, landed
    on the world the first one reached, and was discarded by cycle detection as somewhere
    already seen. The loop iterated twice and the search was depth 1, silently, for every means
    that moves a measured property.

    Measured before the fix: 0.04 at the start, the world at 0.18 after one step, and `_bind`
    still saying 0.04. This pins both halves — the reading a rule predicts FROM, and the dose,
    which `dose_for` sizes from where the property stands and which is therefore the act the
    actor would take NEXT rather than a repeat of the first.
    """
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): DRY}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    planner = Planner(agent, agent.me)
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)

    here = planner._begin(desire)
    row = next(iter(planner._candidates(here, desire)))
    step = planner._step_from(here, row, desire)

    #  What a property reads in a candidate world is SENSING's answer, asked at the node's
    #  graph (the-stake-is-sensings-want) — the planner no longer walks sosa for it.
    sensing = agent.provider("http://example.org/orexis/sensing#SensingCapability")
    value_at = lambda node: sensing.value_in(planner.imaginarium.query, node.graph,
                                             agent.me.acts_for, MOISTURE)
    assert value_at(here) == DRY
    moved = value_at(step)
    assert moved > DRY, "the dose moved the world it was simulated into"

    #  The ROW is passed because sizing dispatches on its taker (#268) — an actuator sizes a
    #  dose, a bidder sizes a bid — and because an obligation borrows the row's property when it has
    #  none of its own (#255). A bare `_bind` sizes nothing on purpose. The value is not in the
    #  binding any more: the rule reads it from `$state`, which names the node's own graph.
    assert planner._bind(desire, step, row)["state"] != planner._bind(
        desire, here, row)["state"], \
        "a step taken from here must ASK about here — a rule reads the readings its own node reached"

    asked = []
    monkeypatch.setattr(agent.provider("http://example.org/orexis/actuation#Actuation"),
                        "dose_for", lambda prop, value: asked.append(value) or 0.06)
    planner._bind(desire, step, row)
    assert asked == [moved], "the dose is sized from the world the step starts in"


def test_a_plant_that_buys_its_water_can_see_the_lever_that_waters_it(monkeypatch):
    """#268, from the other side: what the menu being complete actually buys.

    Measured the hour #265 landed — `better` zero across three societies, `blind` 1 for every
    plant. Only sensing and actuation shipped effects, so a plant that BUYS its water had a
    search that saw Observe alone. It decided correctly, at 0.2–0.5s per agent per tick, and
    could not see the one lever that mattered.

    Two things had to be true for that to change, and the second is the one that bites. The
    market states what buying does; and the DOSE is asked of whoever would take the act, which
    for Acquire is the bidder. Asking the actuator — as the planner did for every means —
    returns nothing for a plant that holds no valve, so the rule would have predicted a world
    identical to the one the agent stands in, and the search would have concluded that buying
    does not help. That is worse than the blindness: a partial plan defers to the reflex, but a
    confident "nothing is better" overrides it and stops the plant bidding.
    """
    monkeypatch.setenv("OREXIS_WORLD", "simulation")
    st = genesis_store({("fern", MOISTURE): 0.30})
    fern = build_agent("fern", st, monkeypatch)
    open_round_for(fern, "fern")
    desire = next(g for g in fern.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)

    plan = Planner(fern, fern.me).plan(desire)

    assert [s.action for s in plan.steps] == ["http://example.org/orexis/market#Acquiring"], \
        "the lever that waters this plant is the one the search found"
    assert plan.urgency_after < plan.urgency_now, \
        "and the world it reaches is better than standing still — `better` was zero before"


def test_a_content_plant_does_not_buy_water_to_find_out_how_wet_it_is(monkeypatch):
    """A zero-size act must make nothing true, or ending ignorance pays for itself.

    `value_bid` cedes at or above the aim, so a content agent sizes its bid at nothing. Without
    a guard the effect rule still CONSTRUCTs a reading equal to the value it started from —
    and in a world holding no reading yet that FABRICATES one. The search then scores the step
    as an improvement, because ending ignorance is an improvement (#137), and a content plant
    buys water to discover how wet it is.

    Caught by an equivalence — the reflex ceded at the aim and the planner did not — and kept
    as the claim rather than the comparison, because the reflex it was compared against has
    since been deleted. What must be true is the cede itself, on both sides of the aim.
    """
    from orexis_agent_deliberation.desire import Desire

    monkeypatch.setenv("OREXIS_WORLD", "simulation")
    fern = build_agent("fern", genesis_store(), monkeypatch)
    open_round_for(fern, "fern")
    decider = fern.deliberator

    #  fern aims at 0.55, and the store holds NO reading — which is the arrangement that makes
    #  the fabrication possible at all. A bare Desire suffices: the measure is not the want's
    #  to carry, and sensing answers the choir for any observation-backed stake.
    write_reading(fern, 0.30, MOISTURE)   # the world holds the value; a want's `value` is not it
    stake = ObservedDesire(uri=stake_of(fern).uri, urgency=0.4, observed_property=MOISTURE,
                         value=0.30)
    assert decider.propose_for(stake) == "http://example.org/orexis/market#Acquiring", \
        "below the aim there is a deficit to close, and the search must still close it"
    for value in (0.55, 0.80):
        write_reading(fern, value, MOISTURE)
        stake = ObservedDesire(uri=stake_of(fern).uri, urgency=0.4,
                             observed_property=MOISTURE, value=value)
        assert decider.propose_for(stake) is None, \
            f"a content plant bought water at {value} — a zero-size act made something true"


# --- a rule is asked about a WORLD, not about the store (#254) ------------------------------

#  A butt with barely anything in it, so `dose_for` caps every pour at what the vessel holds and
#  no single dose can close the gap. That is the situation depth 2 exists for — "my doses are
#  too coarse" is the finding the record calls EXHAUSTED — and it is the only situation in which
#  a second step's baseline can be observed at all.
STORED = "http://example.org/orexis/water#StoredLitres"
NEARLY_EMPTY = 0.05


def _thirsty_with_a_nearly_empty_butt(monkeypatch):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): DRY, ("water_butt", STORED): NEARLY_EMPTY},
                       world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    return agent, Planner(agent, agent.me), desire


def _readings_of(world, subject, prop):
    """Every value sitting on `prop` for `subject` in this world. A LIST, because the bug this
    is about is a second one appearing beside the first."""
    sosa = rdflib.Namespace("http://www.w3.org/ns/sosa/")
    return [float(value)
            for obs in world.subjects(sosa.observedProperty, rdflib.URIRef(prop))
            if (obs, sosa.hasFeatureOfInterest, rdflib.URIRef(subject)) in world
            for value in world.objects(obs, sosa.hasSimpleResult)]


def test_a_second_dose_is_predicted_from_what_the_first_one_left(monkeypatch):
    """Depth 2, meaning what it says. The defect #254 closed, in the case that measured it.

    A means' effect is a `sh:construct` and an `orexis:retracts`, and both used to run against the
    STORE while the diff was applied to the HYPOTHESIS. So the retraction re-asked the belief
    base, found the observation still sitting there, and never saw what the previous step added:
    the second dose's predicted reading landed BESIDE the first's instead of replacing it, the
    reader took whichever it found, and the step was thrown away by cycle detection as somewhere
    already seen. Measured before the fix, exactly here: one step, `exhausted`, and a world
    holding 0.0733 where the plan had computed 0.1067.

    The butt is nearly empty, so no single dose closes the gap — which is the only arrangement
    in which a second step's baseline is observable at all.
    """
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    plan = planner.plan(desire)

    assert [s.action for s in plan.steps] == [DOSING, DOSING], \
        "two doses, because one cannot pour more than the butt holds"
    assert plan.outcome == search.SATISFIED
    assert plan.urgency_after < plan.urgency_now


def test_the_world_a_plan_reaches_holds_ONE_reading_per_subject_and_property(monkeypatch):
    """The shape of the wrongness, rather than its symptom — and the reason it stayed hidden.

    Two results on one (subject, property) is not merely untidy: `sensed_writer` upserts one
    observation node per pair, so a world holding two is a world no instrument could produce.
    A shape asking whether ANY reading sits past an edge then answers about the reading the plan
    just replaced, and the planner rejects the plan that works.

    Asserted on the world the LAST step reached, which is the one every consumer of a plan cares
    about: the value in it must be the one that step predicted, and there must be nothing else
    beside it.
    """
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    plan = planner.plan(desire)

    assert len(plan.steps) == 2, \
        "a one-step plan cannot show this — the second step is where the two readings met"
    node = planner._begin(desire)
    for step in plan.steps:
        node = planner._step_from(node, step, desire)

    #  The node's world is the imaginarium's, not a copy it carries (#481), so the assertion
    #  reads it the way every judge does: through the planner's own border.
    import rdflib
    world = rdflib.Graph()
    world.parse(data=planner._border(node), format="nt")
    readings = _readings_of(world, agent.me.acts_for, MOISTURE)
    assert len(readings) == 1, \
        f"the plan's world holds {readings} — a step landed beside its predecessor"
    assert readings[0] > DRY, "and it is the reading the last step predicted, not the stored one"


def test_legality_is_judged_on_the_world_the_plan_would_actually_reach(monkeypatch):
    """`_world_of` had the same defect as the search loop, at the end rather than during.

    It replayed the chosen plan against the store to check the world's legality, so past step
    one it validated a world the plan would not reach — and the society's refusal is the one
    check that must be about the world the agent actually intends. It is not replayed at all
    now: the node that won already holds that world, so it is passed to the check.

    Caught by looking at what the legality check is handed — the border text since #485,
    parsed here to read it — because a legality check that is quietly about the wrong world
    passes exactly as loudly as one about the right world.
    """
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    judged = []

    def spy(self, node, selects):
        #  The world the check is asked about, taken from the imaginarium the moment it is
        #  asked — the store is dropped when the pass ends.
        judged.append(self.imaginarium.dump_nt(node.graph))
        return []
    monkeypatch.setattr(search.Planner, "_illegal", spy)

    plan = planner.plan(desire)

    assert len(plan.steps) == 2 and len(judged) == 1, "the winner is checked, once"
    world = rdflib.Graph()
    world.parse(data=judged[0], format="nt")
    readings = _readings_of(world, agent.me.acts_for, MOISTURE)
    assert len(readings) == 1 and readings[0] == pytest.approx(_last_predicted(planner, desire,
                                                                              plan)), \
        "the society judged a world the plan would not have reached"


def _last_predicted(planner, desire, plan) -> float:
    """What the plan's final step predicts, replayed step by step from the root."""
    node = planner._begin(desire)
    for step in plan.steps:
        node = planner._step_from(node, step, desire)
    sensing = planner.agent.provider("http://example.org/orexis/sensing#SensingCapability")
    return sensing.value_in(planner.imaginarium.query, node.graph, planner.me.acts_for,
                            desire.observed_property)   # an ObservedDesire: sensing's field


def test_a_whole_search_writes_nothing_to_the_belief_base(monkeypatch):
    """The property the imaginarium exists to keep, asserted over a search rather than a step.

    One possible world computed and dropped was already pinned. What a store of its own buys is
    that the guarantee survives DEPTH: seven live worlds, each in a named graph of its own, and
    not one of them in the graph where a reading written by an instrument would be
    indistinguishable from a reading nobody took. Asserted on the graph names as well as on the
    contents, because a hypothesis graph left behind in the belief base is litter that outlives
    the premise it was concluded from.
    """
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    before = agent.beliefs.get_graph(STATE_GRAPH)
    names = set(agent.beliefs.graph_names())

    plan = planner.plan(desire)

    assert len(plan.steps) == 2, "a search that never went deep would assert nothing here"
    assert agent.beliefs.get_graph(STATE_GRAPH) == before, "readings the agent never took"
    assert set(agent.beliefs.graph_names()) - names <= {DELIBERATION_GRAPH}, \
        "a possible world escaped into the store that keeps things"
    assert planner.imaginarium is None, "the imaginarium outlived the plan"


def test_two_paths_to_the_same_world_still_collide(monkeypatch):
    """Cycle detection stays keyed on the WORLD, which naming a graph per node could have broken.

    `seen` holds each world's net diff against the base, and it is global across the search
    rather than per branch — so two paths arriving at the same world collide and the second is
    pruned. A node
    now carries a graph name derived from its path, and keying on THAT would have turned cycle
    detection into a per-branch check silently, since two names for one world would each look
    new.

    Looking is the case that proves it: Observe predicts the value it found, so its world is the
    world it started in, under a different name. It must still be seen.
    """
    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    planner.plan(desire)

    looks = [(row.action, verdict) for _, row, _, verdict in planner._weighed
             if row.action == OBSERVING]
    assert looks, "the gardener polls a probe, so looking is on its menu"
    assert {verdict for _, verdict in looks} == {trace.SEEN}, \
        "a look reaches the world it started in, whatever its node's graph is called"


def test_a_sensing_action_still_ends_a_plan_with_no_rule_of_its_own(monkeypatch):
    """The constraint, and the whole of what now upholds it — which is not a term on the rule.

    "A plan may not chain PAST a sensing action" was enforced for a while by asking the
    effect a question of its own, and that guard is what made depth 1: it read `orexis:confirmedBy
    orexis:ByObservation`, which every effect here answers, so the frontier came back empty at every
    depth whatever MAX_DEPTH said. Replacing it with a truer term was the first fix and the
    wrong one. **What a look does is already stated by its EFFECT** — it predicts the value it
    found — so the world it reaches carries its parent's signature and `seen` discards it, by
    the same road a zero-size bid arrives at "this does not help".

    So there is no guard, and this is the test that says the constraint survives without one.
    THE HARD CASE IS THE FIRST LOOK, with nothing sensed at all: the construct emits an
    observation with no `sosa:hasSimpleResult`, because nobody can predict what a first look
    will say. Both worlds then read None and collide — which is the case a reader would most
    expect to escape, and the reason it is the one asserted here.

    If this fails, the thing to look at is `signature.py`. Since #258 the signature is the
    world's net diff in canonical facts, and in canonical form a look nets to nothing: an
    observation is its upsert key and its value, never its `sosa:resultTime`, and a valueless
    first look states no fact at all. A signature that noticed a fresher timestamp would make
    "look, then look" a new world every time; chaining past a look becomes a real question
    again exactly there.
    """
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("water_butt", STORED): NEARLY_EMPTY}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)
    planner = Planner(agent, agent.me)

    plan = planner.plan(desire)

    looked = [v for _, row, _, v in planner._weighed if row.action == OBSERVING]
    assert looked == [trace.SEEN], \
        "a look with nothing to carry forward reached somewhere new — it must not"
    assert not any(step.action == OBSERVING for step in plan.steps[:-1]), \
        "a plan chained past a sensing action"


def test_a_step_that_moves_something_else_is_not_mistaken_for_a_cycle(monkeypatch):
    """The whole of #258, as one assertion per direction.

    The old signature was the goal's own value, so a world differing in anything EXCEPT that
    number was indistinguishable from where you started — and the step that makes a chain a
    chain is exactly one that does not move the goal's number yet. You buy the water first
    precisely because buying it does not wet the soil, and under the old signature that step
    died as a false cycle at depth 1, in the one place nobody would look for it.

    So Actuate's effect is hijacked here to do what an Acquire with a claim will do: add a
    fact that is not a reading and move no number. The world it reaches must count as
    somewhere NEW — and taking the same step again from there must still be pruned, because
    a world that already holds the claim is not moved by adding it twice.
    """
    import pyoxigraph as ox

    agent, planner, desire = _thirsty_with_a_nearly_empty_butt(monkeypatch)
    claim = ox.Triple(ox.NamedNode(GARDENER),
                      ox.NamedNode("http://example.org/orexis/market#holdsClaim"),
                      ox.NamedNode("urn:test:claim"))
    real = effects.apply

    def hijacked(store, means, **bind):
        if means == DOSING:
            return [claim], []
        return real(store, means, **bind)

    monkeypatch.setattr(effects, "apply", hijacked)
    planner.plan(desire)

    doses = {depth: verdict for depth, row, _, verdict in planner._weighed
             if row.action == DOSING}
    assert doses[0] != trace.SEEN, \
        "a step that adds a claim without moving the goal's number was discarded as a cycle"
    assert doses[1] == trace.SEEN, \
        "adding the claim a second time reaches the world that already holds it"


def test_a_path_that_returns_to_the_base_world_returns_to_the_empty_diff(monkeypatch):
    """+3 then −3 is still collapsed — as the world REACHED, never as the diffs accumulated.

    The two runs mint different blank nodes and different `resultTime`s, and the value comes
    back with floating-point noise, because that is what the effect rules actually do: every
    predicted observation is `BNODE()` stamped `NOW()`, and SPARQL arithmetic does not promise
    bit-identical round trips. If any of that counted as somewhere new, cycle detection would
    be decorative — so this is the test that says an observation is its upsert key and its
    value, and its identity and its timestamp are not part of where a plan stands.
    """
    import pyoxigraph as ox

    from orexis_agent_deliberation import signature

    sosa = "http://www.w3.org/ns/sosa/"
    xsd = "http://www.w3.org/2001/XMLSchema#"
    zz = ox.NamedNode("http://example.org/orexis/world/loner#zz")
    prop = ox.NamedNode(MOISTURE)

    def observation(node, value, datatype, when):
        return [
            ox.Triple(node, ox.NamedNode(sosa + "hasFeatureOfInterest"), zz),
            ox.Triple(node, ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                      ox.NamedNode(sosa + "Observation")),
            ox.Triple(node, ox.NamedNode(sosa + "observedProperty"), prop),
            ox.Triple(node, ox.NamedNode(sosa + "hasSimpleResult"),
                      ox.Literal(value, datatype=ox.NamedNode(xsd + datatype))),
            ox.Triple(node, ox.NamedNode(sosa + "resultTime"),
                      ox.Literal(when, datatype=ox.NamedNode(xsd + "dateTime"))),
        ]

    base = observation(ox.NamedNode("http://example.org/orexis#obs_zz_SoilMoisture"),
                       "0.30", "decimal", "2026-01-01T00:00:00Z")
    up = observation(ox.BlankNode(), "0.33", "double", "2026-01-01T00:01:00Z")
    back = observation(ox.BlankNode(), repr(0.33 - 0.03),   # 0.30000000000000004
                       "double", "2026-01-01T00:02:00Z")

    #  What sensing declares of an observation (`orexis:keyedBy`, `orexis:carries`), as the planner
    #  reads it once per pass — the signature no longer spells sosa itself.
    keys = {sosa + "Observation": (frozenset({sosa + "hasFeatureOfInterest", sosa + "observedProperty"}),
                                   frozenset({sosa + "hasSimpleResult"}))}
    base_facts = signature.facts(base, keys)
    there = signature.advance(signature.EMPTY,
                              signature.facts(up, keys), signature.facts(base, keys), base_facts)
    assert there != signature.EMPTY, "a dose reaches somewhere new"
    home = signature.advance(there,
                             signature.facts(back, keys), signature.facts(up, keys), base_facts)
    assert home == signature.EMPTY, \
        "+3 then −3 nets to nothing, whatever nodes and timestamps the runs minted"


def test_two_mintings_of_the_same_claim_are_the_same_place():
    """A blank node is its content, not its identity — or every world would be novel."""
    import pyoxigraph as ox

    from orexis_agent_deliberation import signature

    holds = ox.NamedNode("http://example.org/orexis/market#holdsClaim")
    litres = ox.NamedNode("http://example.org/orexis/market#litres")
    double = ox.NamedNode("http://www.w3.org/2001/XMLSchema#double")

    def minted():
        c = ox.BlankNode()
        return [ox.Triple(ox.NamedNode(GARDENER), holds, c),
                ox.Triple(c, litres, ox.Literal("2.0", datatype=double))]

    assert signature.facts(minted()) == signature.facts(minted())


def test_no_ontology_graph_carries_a_law_so_the_carve_may_leave_the_vocabulary_out():
    """#484: the planner's flatten reads the data-borne graphs and, of the T-Box, its node
    shapes alone — a package may declare a want's shape in its vocabulary (the courier's
    `delivered`, hanoi's `solved`), and those are carried as subgraphs. A LAW is ratified and
    arrives as data, and this is what holds that half: the ontology graphs exist, and none
    carries a violation-severity node shape. The day one does, the narrowing fails here
    rather than judging a plan legal against a law it never read."""
    st = genesis_store()
    vocabulary = {r["g"] for r in bindings(st.query("SELECT ?g WHERE { ?g a orexis:OntologyGraph }"))}
    assert len(vocabulary) >= 2, "the ontology graphs stopped being typed — this checks nothing"
    laws = bindings(st.query_union("""
SELECT ?g ?s WHERE { GRAPH ?g { ?s a sh:NodeShape ; sh:severity sh:Violation } }"""))
    assert not [r for r in laws if r["g"] in vocabulary], \
        "a law in the vocabulary: the planner's carve would never find it"
