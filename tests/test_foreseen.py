"""A predicted crossing derives a want met at that instant (#619) — the second child of
an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it, held to the code.

The loner's pot at 0.12 is inside its region and falling at 0.03 a day: the drift says it
leaves the region in sixteen hours. The gardener derives a want under the root that must hold
AT the crossing, plans the dose it would have planned once the pot was dry, and holds the dose
until the crossing less the valve's own ceiling. A pot with no crossing in view derives nothing.

A FORESIGHT once stood between the judgment and the want — `sensing:foresightS`, a per-agent
pick discarding a crossing further out than N seconds — and it is gone: `judge_desires` judges
each desire at every instant a prediction reaches and says which fail, and how far ahead the
agent sees is what the drifts predict at. No shipped world ever set the pick.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_deliberation import pursuit
from orexis_agent_deliberation.derive_wants import derive_wants
from orexis_agent_deliberation.planner import Planner
from orexis_agent_progression.store import bindings
from conftest import build_agent, genesis_store, write_reading
from orexis_agent_deliberation.wants import find_wants

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
DOSING = "http://example.org/orexis/actuation#Dosing"
FALLING, CONTENT = 0.12, 0.20          # 0.12 at 0.03/day is below the loner's floor of 0.10 a day out, not five hours out
DAY = 86400.0


def _gardener(monkeypatch, moisture):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    return build_agent("gardener", genesis_store({("zz", MOISTURE): moisture}, world="loner"),
                       monkeypatch)


def _stake(agent):
    return next(d for d in agent.pursuing()
                if getattr(d, "observed_property", None) == MOISTURE and not d.is_epistemic)


def _crossing_of(agent):
    """The crossing the water package states, from the reading the agent holds.

    DERIVED FIRST, so a want stands where one is implied — and the crossing is asked of the
    DESIRE, never of the want derived under it: a want has no crossing, it is what a crossing
    produced.
    """
    derive_wants(agent.beliefs.engine)
    return pursuit.crossing_of(agent, _stake(agent).desire or _stake(agent).uri)


def test_the_drift_says_when_the_reading_leaves_its_region(monkeypatch):
    """The crossing is the start of the earliest prediction at which the root reads unmet (#643):
    five hours out the pot is still in its region and a day out it is below, so the crossing is
    where the window that reaches the day opens — five hours after the reading, not sixteen,
    the safe direction the ladder gives."""
    agent = _gardener(monkeypatch, FALLING)
    crossing = _crossing_of(agent)
    assert crossing is not None
    ahead = (crossing - datetime.now(timezone.utc)).total_seconds()
    assert abs(ahead - 18000.0) < 120, ahead
    under = _gardener(monkeypatch, 0.05)
    below = _crossing_of(under)
    assert below is not None and 0.0 <= (below - datetime.now(timezone.utc)).total_seconds() < 3600.0, \
        "a reading already below reads unmet at the first prediction, the next expected observation; a root unmet now is pursued as itself"


def test_a_root_with_no_crossing_in_view_derives_nothing(monkeypatch):
    """A pot at 0.20 falling at 0.03 a day is inside its region at every horizon a drift
    predicts at, so no judgment says it fails and there is nothing to pursue — the first
    child's path, unchanged."""
    agent = _gardener(monkeypatch, CONTENT)
    root = _stake(agent)
    assert root.is_met and _crossing_of(agent) is None
    assert agent.deliberator.decide(root) is None
    assert pursuit.child_of(agent, root.uri) is None


def test_a_crossing_derives_a_want_met_at_that_instant(monkeypatch):
    """The claim. Content now, crossing in view: the root derives a
    want bound AT the crossing, presented in its place — unmet, since the newest prediction
    says the reading will have crossed, its urgency the fraction of the stretch run — and the
    search, judged at the instant, plans the dose the dry pot would have got."""
    agent = _gardener(monkeypatch, FALLING)
    root = _stake(agent)
    assert root.is_met
    plan = agent.deliberator.decide(root)
    assert plan is not None and [s.action for s in plan.steps] == [DOSING], plan

    child = _stake(agent)
    assert child.desire == root.uri and child.holds_at is not None
    assert abs((child.holds_at - _crossing_of(agent)).total_seconds()) < 1.0
    assert child.state == "unmet", "the newest prediction still says the reading crosses by the instant"
    assert child.urgency == root.urgency > 0.0, \
        "its room is the stretch to the instant, barely run — never less than the root's own measure"
    said = {r["p"]: r["o"] for r in bindings(agent.desires.query(
        f"SELECT ?p ?o WHERE {{ <{child.uri}> ?p ?o }}"))}
    #  THE INSTANT IS WHAT SAYS IT, and it is all that ever did: the want carried
    #  `orexis:bindsWhen orexis:At` beside this, computed from whether an instant was known
    #  (#681). One fact, and the instant is the half an interval cannot carry.
    assert "http://example.org/orexis#holdsAt" in said and "http://www.w3.org/ns/prov#generatedAtTime" in said


def test_a_crossing_derives_a_want_however_far_out_it_is(monkeypatch):
    """The crossing the loner's pot has is five hours out, and there is no second number to
    say whether five hours is too far: the want is minted at it. What bounds the lookahead is
    the horizons the drift predicts at — beyond the furthest, nothing is judged and nothing is
    derived, which is the test above."""
    agent = _gardener(monkeypatch, FALLING)
    root = _stake(agent)
    assert agent.deliberator.decide(root) is not None
    child = pursuit.child_of(agent, root.uri)
    assert child is not None
    assert _stake(agent).holds_at == _crossing_of(agent)


def test_the_search_judges_a_candidate_at_the_instant(monkeypatch):
    """Handed the want directly, the planner reads the root as UNMET at the instant — the
    present drifted sixteen hours is below the region — and a dose's world as met there."""
    agent = _gardener(monkeypatch, FALLING)
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
    agent = _gardener(monkeypatch, FALLING)
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


def test_a_reading_that_lifts_the_prediction_withdraws_the_want(monkeypatch):
    """The world moved — the pot was watered by someone — so the newest prediction crosses
    after the instant: the desire no longer reads that cluster unmet, so THE DERIVATION drops
    the want it implied, with nothing standing for it.

    It used to read met here and be withdrawn by the next `decide`, which meant the want's own
    met-test was run a second time to conclude what the desire's rows had already said. The
    derivation withdraws from the rows it read, and the withdrawn want is in what it returns —
    so a caller refreshing on a change refreshes on a withdrawal too."""
    agent = _gardener(monkeypatch, FALLING)
    root = _stake(agent)
    agent.deliberator.decide(root)
    child = _stake(agent)
    assert child.state == "unmet"
    write_reading(agent, CONTENT)
    changed = derive_wants(agent.beliefs.engine)   # the reading moved the predictions
    assert child.uri in changed, "the derivation withdrew it, and said so"
    assert pursuit.child_of(agent, root.uri) is None
    assert agent.deliberator.decide(_stake(agent)) is None, "a met root is nothing to pursue"


def test_a_pot_that_crosses_before_the_drift_said_is_wanted_now_and_not_at_the_crossing(monkeypatch):
    """What was foreseen has arrived. The want was minted AT the predicted crossing, and a plan
    for it is placed to land there (#619); then a reading shows the pot already below its
    floor. The root is unmet NOW, and a want still saying "hold at the crossing" would have
    the dose placed hours out. The derivation re-mints it with no instant under the same name, and
    the pass that stood on the old judgment is handed the new one."""
    agent = _gardener(monkeypatch, FALLING)
    root = _stake(agent)
    agent.deliberator.decide(root)
    child = _stake(agent)
    [minted] = find_wants(agent.beliefs, desire=root.uri)     # every desire derives; the stake's
    assert minted.uri == child.uri and minted.holds_at is not None, "minted at the crossing"

    write_reading(agent, 0.05)                                       # below the floor, now
    assert pursuit.handed(agent, child).holds_at is None, \
        "handed the want as it stands now, not as the pass first read it"
    [again] = find_wants(agent.beliefs, desire=root.uri)
    assert again.uri == minted.uri and again.holds_at is None, "the same want, at no instant"
    derive_wants(agent.beliefs.engine)
    assert derive_wants(agent.beliefs.engine) == [], "and once is enough"
