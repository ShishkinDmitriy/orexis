"""world/greenhouse: one want about two properties, and a knob that couples them (#566).

Every world before this holds wants about a single property. A bed is comfortable when its
soil is in the range the bed states AND its air is, which is ONE want two different levers
serve — the pump for the soil, a heater for the air — so its plan takes a step from each.

The knob is `climate:driesTheSoil`, one triple on the heater. Off, warming touches nothing
the watering half of the want reads. On, warming writes a reading the dosing rule reads, and
the two halves stop being independent — which the search discovers on its own, by planning
them the other way round.
"""

from __future__ import annotations

import pytest

from conftest import genesis_store
from agent import genesis, runtime
from orexis_agent_deliberation import relevance as R
from orexis_agent_deliberation.planner import Planner

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
AIR = "http://example.org/orexis/water#AirTemperature"
STORED = "http://example.org/orexis/water#StoredLitres"
CLIMATE = "http://example.org/orexis/climate#"
WORLD = "http://example.org/orexis/world/greenhouse#"
DOSING = "http://example.org/orexis/actuation#Dosing"
HEATING = CLIMATE + "Heating"
VENTING = CLIMATE + "Venting"
COMFORT = WORLD + "the_bed_is_comfortable"


def _grower(monkeypatch, dries=False, moisture=0.20, air=12.0, outside=8.0, heater=True):
    """A cold, dry bed, and whether its heater dries what it warms. The two regimes are the
    same world one triple apart, which is what makes comparing them honest. `outside` is the
    air on the other side of the vent — a fact no lever of this agent moves — and `heater`
    takes the heater away, which leaves the vent as the only lever the air has."""
    monkeypatch.setenv("OREXIS_WORLD", "greenhouse")
    monkeypatch.setenv("INFLUX_BUCKET", "test-greenhouse")
    monkeypatch.setenv("INFLUX_TOKEN", "test-token-greenhouse")
    st = genesis_store({("bed", MOISTURE): moisture, ("bed", AIR): air,
                        ("outside", AIR): outside,
                        ("water_butt", STORED): 15.0}, world="greenhouse")
    if not heater:
        st.update(f"""DELETE DATA {{ GRAPH <http://example.org/orexis/graph/world> {{
            <{WORLD}grower> <{CLIMATE}hasHeater> <{WORLD}heater> }} }}""")
    if dries:
        st.update(f"""INSERT DATA {{ GRAPH <http://example.org/orexis/graph/world> {{
            <{WORLD}heater> <{CLIMATE}driesTheSoil> true }} }}""")
    genesis.classify_own_graphs(st, "grower")
    return runtime.Agent("grower", st=st), st


def _comfort(agent):
    return next(g for g in agent.pursuing() if g.uri == COMFORT)


def test_the_bed_holds_one_want_about_two_properties(monkeypatch):
    """The want this world exists for: one desire, two `orexis:about`, and the menu offering a
    row per property — which is what lets a single want reach two levers (#566)."""
    from orexis_agent_deliberation.afforder import affordances_of, wants_of
    from orexis_agent_progression.ontology import beliefs_graph
    agent, st = _grower(monkeypatch)
    abouts = wants_of(agent.desires.query_union, agent.me.uri)
    assert set(abouts[COMFORT]) == {MOISTURE, AIR}, "one want, about both properties"
    rows = [r for r in affordances_of(st.query, agent.me.uri, agent.desires.query_union,
                                      beliefs_graph("grower")) if r.want == COMFORT]
    assert {(r.action, r.about) for r in rows} >= {(DOSING, MOISTURE), (HEATING, AIR)}, \
        "the dose is offered about the soil and the heating about the air, for the one want"


def test_a_cold_dry_bed_is_watered_and_warmed(monkeypatch):
    """The plan is a step from each half. Neither lever serves the other's property, so a
    plan with one step could not satisfy this want — which is the whole reason for the
    world."""
    agent, _ = _grower(monkeypatch)
    plan = Planner(agent, agent.me).plan(_comfort(agent))
    assert {s.action for s in plan.steps} == {DOSING, HEATING}, \
        [s.action.rsplit("#", 1)[-1] for s in plan.steps]
    assert plan.urgency_after < plan.urgency_now


def test_the_knob_reorders_the_plan_because_warming_undoes_the_dose(monkeypatch):
    """THE KNOB, and the finding. Off, the halves do not touch and the plan waters first.
    On, the heater's effect writes the soil reading the dosing rule reads — so a plan that
    watered and then warmed would have undone its own dose, and the search puts the heating
    FIRST without being told anything about evaporation. Nothing declares the order; the
    coupling is in the rules and the search reads it."""
    dry_agent, _ = _grower(monkeypatch, dries=False)
    apart = [s.action for s in Planner(dry_agent, dry_agent.me).plan(_comfort(dry_agent)).steps]
    wet_agent, _ = _grower(monkeypatch, dries=True)
    coupled = [s.action for s in Planner(wet_agent, wet_agent.me).plan(_comfort(wet_agent)).steps]
    assert apart == [DOSING, HEATING], "independent halves: water, then warm"
    assert coupled == [HEATING, DOSING], "coupled: warm first, or the warming undoes the dose"


def test_both_regimes_are_one_scope_which_is_the_predicate_level_limit(monkeypatch):
    """What the knob does NOT change, and it is worth pinning because the issue expected it
    to. A scope is a set of PREDICATES (#565), and both readings of this bed carry the same
    predicates — feature, property, type — so warming and dosing write the same words whether
    the heater dries the soil or not. One scope in both regimes.

    So the coupling this world demonstrates is real and the scope computation cannot see it:
    telling these two halves apart needs a scope over VARIABLES, a subject and a property
    together. That is the measurement, and it is why one cone per scope is still unbuilt."""
    _, apart = _grower(monkeypatch, dries=False)
    _, coupled = _grower(monkeypatch, dries=True)
    for store, regime in ((apart, "independent"), (coupled, "coupled")):
        parts = R.scopes(R.actions_of(store.query), R.rule_edges())
        assert len(parts) == 1, f"{regime}: {len(parts)} scopes"


def test_a_comfortable_bed_plans_nothing(monkeypatch):
    """The other side of the want: both readings in their ranges, and there is nothing to do.
    A want about two properties is met when BOTH are, which its shape says as two constraints
    and the kernel compiles into one select whose rows are its violations."""
    agent, _ = _grower(monkeypatch, moisture=0.45, air=21.0)
    want = _comfort(agent)
    assert want.state == "met"
    assert Planner(agent, agent.me).plan(want).steps == ()


def test_the_warm_half_alone_is_planned_when_only_the_air_is_cold(monkeypatch):
    """And the want is not all-or-nothing: a bed whose soil is fine and whose air is cold is
    one heating away, so the plan is one step. The two halves are one want and still weigh
    separately, which is what makes the split worth measuring at all."""
    agent, _ = _grower(monkeypatch, moisture=0.45, air=12.0)
    plan = Planner(agent, agent.me).plan(_comfort(agent))
    assert [s.action for s in plan.steps] == [HEATING]


# --- the vent: one act, and the world decides what it does ---------------------

def test_the_same_venting_reaches_a_different_band_for_each_outside(monkeypatch):
    """THE FIRST EFFECT WHOSE OUTCOME IS THE WORLD'S. A heater warms, always. Opening a vent
    does whatever the other side is doing, so the same act declares a different band per
    outside reading: warm out and the bed lands in its region, cold out and it lands below,
    hot out and above. Nothing about the act changed between these three.

    Asked of the RULE rather than of a plan, because what is under test is the declaration."""
    from orexis_agent_deliberation import effects
    from orexis_agent_progression.ontology import STATE_GRAPH, beliefs_graph
    reached = {}
    for outside in (21.0, 5.0, 30.0):
        agent, _ = _grower(monkeypatch, air=12.0, outside=outside)
        added, retracted = effects.apply(
            agent.beliefs, VENTING, me=f"<{agent.me.uri}>", subject=f"<{agent.me.acts_for}>",
            about=f"<{AIR}>", state=f"<{STATE_GRAPH}>",
            beliefs=f"<{beliefs_graph('grower')}>", litres="0.0")
        reached[outside] = sorted(t.object.value.rsplit(".", 1)[-1] for t in added
                                  if t.predicate.value.endswith("#type") and "band." in t.object.value)
        assert retracted, "and it replaces the reading it moves, as every reading-mover does"
    assert reached == {21.0: ["inside"], 5.0: ["below"], 30.0: ["above"]}, reached


def test_a_vent_is_planned_onto_a_warm_afternoon_and_not_onto_a_cold_night(monkeypatch):
    """The same claim where it decides something: with the heater gone, the vent is the only
    lever the bed's air has. Onto a warm afternoon it is the plan. Onto a cold night it makes
    the bed colder, so it reaches no better world and the search answers that nothing helps —
    which is the honest answer rather than a shrug, and is what an agent that cannot warm
    itself in February should say."""
    warm, _ = _grower(monkeypatch, moisture=0.45, air=12.0, outside=21.0, heater=False)
    assert [s.action for s in Planner(warm, warm.me).plan(_comfort(warm)).steps] == [VENTING]
    cold, _ = _grower(monkeypatch, moisture=0.45, air=12.0, outside=5.0, heater=False)
    plan = Planner(cold, cold.me).plan(_comfort(cold))
    assert plan.steps == (), "opening onto a colder night is not a way to get warm"


def test_the_outside_is_read_as_a_number_because_no_lever_moves_it(monkeypatch):
    """Why the rule may read a number at all, in a repository whose worlds state what a reading
    IS (#579). The outside states no range, so it mints no band and keeps its number; and no
    lever of this agent writes it, so that number is the same at the root of a cone and at
    every leaf. It is a constant of the plan rather than a value a step might have changed."""
    from orexis_agent_progression.store import bindings
    from orexis_agent_progression.ontology import STATE_GRAPH
    agent, st = _grower(monkeypatch, outside=8.0)
    rows = bindings(st.query(f"""
SELECT ?c WHERE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:hasFeatureOfInterest <{WORLD}outside> ; a ?c }}
  FILTER(CONTAINS(STR(?c), "band.")) }}"""))
    assert rows == [], "the outside is nobody's want, so it is in no band"
    values = bindings(st.query(f"""
SELECT ?v WHERE {{ GRAPH <{STATE_GRAPH}> {{ ?o sosa:hasFeatureOfInterest <{WORLD}outside> ;
  sosa:hasSimpleResult ?v }} }}"""))
    assert [float(r["v"]) for r in values] == [8.0], "and it keeps the number the instrument gave"
