"""A predicted crossing derives a want met at that instant (#619) — the second child of
an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it, held to the code.

The loner's pot at 0.12 is inside its region and falling at 0.03 a day: the drift says it
leaves the region in sixteen hours. A gardener that foresees a day derives a want under the
root that must hold AT that instant, plans the dose it would have planned once the pot was
dry, and holds the dose until the crossing less the valve's own ceiling. A gardener that
foresees nothing plans exactly as before.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_deliberation import pursuit
from orexis_agent_deliberation.planner import Planner
from orexis_agent_progression.ontology import beliefs_graph
from orexis_agent_progression.store import bindings
from conftest import build_agent, genesis_store, write_reading

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
DOSING = "http://example.org/orexis/actuation#Dosing"
FORESIGHT = "http://example.org/orexis/sensing#foresightS"
FALLING, CONTENT = 0.12, 0.20          # 0.12 at 0.03/day is below the loner's floor of 0.10 a day out, not five hours out
DAY = 86400.0


def _gardener(monkeypatch, moisture, foresight: float | None = None):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): moisture}, world="loner")
    if foresight is not None:
        st.update(f"""INSERT DATA {{ GRAPH <{beliefs_graph("gardener")}> {{
            <http://example.org/orexis/world/loner#gardener> <{FORESIGHT}> {foresight} }} }}""")
    return build_agent("gardener", st, monkeypatch)


def _stake(agent):
    return next(d for d in agent.pursuing()
                if getattr(d, "observed_property", None) == MOISTURE and not d.is_epistemic)


def _crossing_of(agent):
    """The crossing the water package states, from the reading the agent holds."""
    return pursuit.crossing_of(agent, _stake(agent).derived_from or _stake(agent).uri)


def test_the_drift_says_when_the_reading_leaves_its_region(monkeypatch):
    """The crossing is the start of the earliest prediction at which the root reads unmet (#643):
    five hours out the pot is still in its region and a day out it is below, so the crossing is
    where the window that reaches the day opens — five hours after the reading, not sixteen,
    the safe direction the ladder gives."""
    agent = _gardener(monkeypatch, FALLING)
    crossing = pursuit.crossing_of(agent, _stake(agent).uri)
    assert crossing is not None
    ahead = (crossing - datetime.now(timezone.utc)).total_seconds()
    assert abs(ahead - 18000.0) < 120, ahead
    under = _gardener(monkeypatch, 0.05)
    below = pursuit.crossing_of(under, _stake(under).uri)
    assert below is not None and 0.0 <= (below - datetime.now(timezone.utc)).total_seconds() < 3600.0, \
        "a reading already below reads unmet at the first prediction, the next expected observation; a root unmet now is pursued as itself"


def test_a_root_that_foresees_nothing_derives_nothing_from_a_prediction(monkeypatch):
    """Every shipped world says no `sensing:foresightS`, so a content root stays nothing to
    pursue — the first child's road, unchanged."""
    agent = _gardener(monkeypatch, FALLING)
    root = _stake(agent)
    assert root.is_met and pursuit.foresees_of(agent, root.uri) is None
    assert agent.deliberator.decide(root) is None
    assert pursuit.child_of(agent, root.uri) is None


def test_a_crossing_within_the_foresight_derives_a_want_met_at_that_instant(monkeypatch):
    """The claim. Content now, crossing in sixteen hours, foreseeing a day: the root derives a
    want bound AT the crossing, presented in its place — unmet, since the newest prediction
    says the reading will have crossed, its urgency the fraction of the stretch run — and the
    search, judged at the instant, plans the dose the dry pot would have got."""
    agent = _gardener(monkeypatch, FALLING, foresight=DAY)
    root = _stake(agent)
    assert root.is_met
    plan = agent.deliberator.decide(root)
    assert plan is not None and [s.action for s in plan.steps] == [DOSING], plan

    child = _stake(agent)
    assert child.derived_from == root.uri and child.holds_at is not None
    assert abs((child.holds_at - _crossing_of(agent)).total_seconds()) < 1.0
    assert child.state == "unmet", "the newest prediction still says the reading crosses by the instant"
    assert child.urgency == root.urgency > 0.0, \
        "its room is the stretch to the instant, barely run — never less than the root's own measure"
    said = {r["p"]: r["o"] for r in bindings(agent.desires.query_union(
        f"SELECT ?p ?o WHERE {{ <{child.uri}> ?p ?o }}"))}
    assert said["http://example.org/orexis#bindsWhen"] == "http://example.org/orexis#At"
    assert "http://example.org/orexis#holdsAt" in said and "http://www.w3.org/ns/prov#generatedAtTime" in said


def test_a_crossing_beyond_the_foresight_derives_nothing(monkeypatch):
    """Five hours out, foreseeing one: not yet."""
    agent = _gardener(monkeypatch, FALLING, foresight=3600.0)
    root = _stake(agent)
    assert agent.deliberator.decide(root) is None
    assert pursuit.child_of(agent, root.uri) is None


def test_the_search_judges_a_candidate_at_the_instant(monkeypatch):
    """Handed the want directly, the planner reads the root as UNMET at the instant — the
    present drifted sixteen hours is below the region — and a dose's world as met there."""
    agent = _gardener(monkeypatch, FALLING, foresight=DAY)
    agent.deliberator.decide(_stake(agent))
    child = _stake(agent)
    planner = Planner(agent, agent.me)
    plan = planner.plan(child)
    assert [s.action for s in plan.steps] == [DOSING]
    assert plan.landing is not None and 0 < plan.landing <= 60, "a dose's duration is the valve's ceiling"
    assert not planner._met_in(planner._root, child), "the present, drifted to the instant, is below"


def test_the_dose_is_placed_at_the_instant_less_its_own_duration(monkeypatch):
    """Pursued, the plan's first step is held `notBefore` the crossing less the dose's
    duration: the intention stands, nothing is commanded now, and its patience does not run
    against a step that is waiting for its instant."""
    agent = _gardener(monkeypatch, FALLING, foresight=DAY)
    root = _stake(agent)
    uri = pursuit.pursue(agent, root)
    assert uri is not None
    child = _stake(agent)
    standing = agent.keeper.standing(want=child.uri)
    assert len(standing) == 1 and standing[0].step.not_before is not None
    placed = standing[0].step.not_before
    assert abs((child.holds_at - placed).total_seconds() - 50.0) < 1.0, \
        "placed at the crossing less the valve's ceiling of fifty seconds"
    assert agent.sent.to("actuators/pump/command") == [], "nothing is commanded before the instant"
    assert agent.keeper.in_progress(child.uri) is not None or \
        pursuit.pursue(agent, root) == uri, "a placed plan is not re-decided while it waits"


def test_a_reading_that_lifts_the_prediction_reads_the_want_met_and_withdraws_it(monkeypatch):
    """The world moved — the pot was watered by someone — so the newest prediction crosses
    after the instant: the derived want reads met and, with nothing standing for it, is gone."""
    agent = _gardener(monkeypatch, FALLING, foresight=DAY)
    root = _stake(agent)
    agent.deliberator.decide(root)
    child = _stake(agent)
    assert child.state == "unmet"
    write_reading(agent, CONTENT)
    now = _stake(agent)
    assert now.uri == child.uri and now.state == "met"
    assert agent.deliberator.decide(now) is None
    assert pursuit.child_of(agent, root.uri) is None
