"""A bed's air drifts toward what surrounds it — one link and no physics (#617) — and a cold
night foreseen derives a want the heater serves, the second half of #619.

The greenhouse states `climate:surroundedBy :outside` and one degree an hour, and says nothing
else about heat. From that the climate package's drift moves the bed toward the outside, and
says when the bed leaves its region; a grower that foresees six hours derives a want bound at
the crossing, and the search, judged at that instant, plans the heater and refuses the vent
onto the cold — where a warm afternoon foresees nothing at all.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_deliberation import pursuit, trace
from orexis_agent_progression.ontology import DESIRE_ASSERTED_GRAPH
from test_greenhouse import AIR, COMFORT, HEATING, VENTING, _comfort, _grower, _outside_as_periods

HOURS = 3600.0


def _foreseeing(monkeypatch, seconds: float, **kw):
    """A grower whose asserted want states how far ahead it acts on a prediction."""
    agent, _ = _grower(monkeypatch, **kw)
    agent.beliefs.update(f"""INSERT DATA {{ GRAPH <{DESIRE_ASSERTED_GRAPH}> {{
        <{COMFORT}> orexis:foresees {seconds} }} }}""")
    agent.desires.rebuild()
    return agent


def _pursued(agent):
    """The want the container presents for the bed's comfort: the root, or what is derived under it."""
    return next(d for d in agent.pursuing() if d.uri == COMFORT or d.derived_from == COMFORT)


def test_the_bed_crosses_toward_a_cold_outside_at_the_stated_rate(monkeypatch):
    """At 20 degrees inside [18, 24] and one degree an hour toward an outside at 8, the bed
    reaches its floor in two hours — the earliest of the want's two crossings, the soil's being
    days away. Toward an outside at 21 the bed never leaves its region, and only the soil's
    crossing remains."""
    agent, _ = _grower(monkeypatch, moisture=0.45, air=20.0, outside=8.0)
    crossing = pursuit.crossing_of(agent, COMFORT)
    assert crossing is not None
    assert abs((crossing - datetime.now(timezone.utc)).total_seconds() - 2 * HOURS) < 120

    warm, _ = _grower(monkeypatch, moisture=0.45, air=20.0, outside=21.0)
    soil_only = pursuit.crossing_of(warm, COMFORT)
    assert soil_only is not None and (soil_only - datetime.now(timezone.utc)).total_seconds() > 3 * 86400


def test_a_cold_night_foreseen_derives_a_want_the_heater_serves_and_the_vent_cannot(monkeypatch):
    """The claim of #619's second half in the greenhouse's own terms. Content now and cooling,
    foreseeing six hours: the want derived under the root holds AT the crossing, the search is
    judged there, the heater's world is met and the vent's — opened onto the cold at the
    instant — is not."""
    agent = _foreseeing(monkeypatch, 6 * HOURS, moisture=0.45, air=20.0, outside=8.0)
    root = _comfort(agent)
    assert root.is_met
    plan = agent.deliberator.decide(root)
    assert plan is not None and [s.action for s in plan.steps] == [HEATING], plan

    child = _pursued(agent)
    assert child.derived_from == COMFORT and child.holds_at is not None and child.state == "unmet"
    assert child.read_at is not None, "a kernel-lifted want takes the instant of the reading the crossing came from"
    weighed = agent.deliberator._planners[child.uri]._weighed
    verdicts = {str(r.action).rsplit("#", 1)[-1]: v for _, r, _, v, *rest in weighed}
    assert verdicts.get("Heating") == trace.MET
    assert "Venting" in verdicts and verdicts["Venting"] != trace.MET, \
        "the vent is weighed at the instant and, onto the cold, does not meet the want"


def test_a_warm_afternoon_foresees_nothing(monkeypatch):
    """The same bed toward an outside at 21 never leaves its region: no crossing within the
    foresight, nothing derived, nothing planned — the first child's road, unchanged."""
    agent = _foreseeing(monkeypatch, 6 * HOURS, moisture=0.45, air=20.0, outside=21.0)
    root = _comfort(agent)
    assert agent.deliberator.decide(root) is None
    assert pursuit.child_of(agent, COMFORT) is None


def test_the_drift_reads_the_surroundings_holding_at_the_instant(monkeypatch):
    """The surroundings are read as the vent reads them, from whatever holds at the instant the
    world is asked about. A cold evening the forecast says turns warm before the crossing: the
    crossing is predicted from the cold in hand, and at the instant the bed has warmed toward
    the forecast instead — the want reads met there, and nothing is planned."""
    agent = _foreseeing(monkeypatch, 6 * HOURS, moisture=0.45, air=20.0, outside=8.0)
    now = datetime.now(timezone.utc)
    _outside_as_periods(agent, (8.0, now - timedelta(hours=1), now + timedelta(minutes=30)),
                        (21.0, now + timedelta(minutes=30), now + timedelta(hours=6)))
    root = _comfort(agent)
    crossing = pursuit.crossing_of(agent, COMFORT)
    assert crossing is not None and (crossing - now).total_seconds() < 3 * HOURS, "predicted from the cold in hand"
    plan = agent.deliberator.decide(root)
    assert plan is None or plan.steps == (), "at the instant the forecast has warmed the bed: nothing to do"
