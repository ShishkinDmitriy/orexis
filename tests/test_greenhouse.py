"""The greenhouse: one want about two properties, and a knob that couples them (#566).

Every world before this holds wants about a single property. A bed is comfortable when its
soil is in the range the bed states AND its air is, which is ONE want two different levers
serve — the pump for the soil, a heater for the air — so its plan takes a step from each.

The knob is `greenhouse:driesTheSoil`, one triple on the heater. Off, warming touches nothing
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
GREENHOUSE = "http://example.org/orexis/greenhouse#"
WORLD = "http://example.org/orexis/world/greenhouse#"
DOSING = "http://example.org/orexis/actuation#Dosing"
HEATING = GREENHOUSE + "Heating"
COMFORT = WORLD + "the_bed_is_comfortable"


def _grower(monkeypatch, dries=False, moisture=0.20, air=12.0):
    """A cold, dry bed, and whether its heater dries what it warms. The two regimes are the
    same world one triple apart, which is what makes comparing them honest."""
    monkeypatch.setenv("OREXIS_WORLD", "greenhouse")
    monkeypatch.setenv("INFLUX_BUCKET", "test-greenhouse")
    monkeypatch.setenv("INFLUX_TOKEN", "test-token-greenhouse")
    st = genesis_store({("bed", MOISTURE): moisture, ("bed", AIR): air,
                        ("water_butt", STORED): 15.0}, world="greenhouse")
    if dries:
        st.update(f"""INSERT DATA {{ GRAPH <http://example.org/orexis/graph/world> {{
            <{WORLD}heater> <{GREENHOUSE}driesTheSoil> true }} }}""")
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
