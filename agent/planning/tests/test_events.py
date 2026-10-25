"""What the Planner says happened, as events: what an imaginarium holds is counted in it and never in
the belief base, a search and a pass are said whole, and an event nobody hears is not made. Their
figures on a whole run are Hanoi's and the greenhouse's to hold."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.metrics import measurement, reported
from agent.planning import events
from agent.runtime import Runtime, boot

HANOI = Path(__file__).resolve().parents[3] / "world" / "hanoi"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _one_pass(monkeypatch, heard: list | None = None) -> Runtime:
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(HANOI, "hanoi"), "hanoi", budget=20)
    planner = runtime.parts["planning"].planner
    if heard is not None:
        for signal in (planner.imagined, planner.searched, planner.planned, planner.rerooted):
            signal.connect(heard.append)
    runtime.run(passes=1, poll_s=0)
    return runtime


def test_what_an_imaginarium_holds_and_how_its_search_ended_are_said_in_one_pass(monkeypatch):
    """One pass at twenty candidates: a plan cut short and the cone it left, in the imaginarium; the
    search said as it ended, of a want the world authored, so under no desire; the pass by its parts."""
    heard = []
    _one_pass(monkeypatch, heard)
    (imagined,) = [e for e in heard if isinstance(e, events.Imagined)]
    assert imagined.exhausted == 1 and imagined.worlds == 20 and imagined.satisfied == 0
    (search,) = [e for e in heard if isinstance(e, events.SearchEnded)]
    assert (search.outcome, search.desire, search.budget, search.weighed) == ("Exhausted", None, 20, 20)
    (planned,) = [e for e in heard if isinstance(e, events.Planned)]
    assert planned.wants == 1 and all(v is not None for v in (planned.ground_s, planned.search_s))
    (rerooted,) = [e for e in heard if isinstance(e, events.Rerooted)]
    assert rerooted.present == "first"


def test_an_event_nobody_hears_is_not_made(monkeypatch):
    """No handler on the pass, the search, the re-root or the imaginarium: none of them is said,
    so nothing is read or timed for them."""
    runtime = _one_pass(monkeypatch)
    planner = runtime.parts["planning"].planner
    assert not any(s.connected for s in (planner.imagined, planner.searched, planner.planned, planner.rerooted))


def test_every_event_that_reports_names_its_measurement_once():
    """A class marking a field reports it, so it names the measurement it is written under; no two
    classes of the package name the same one."""
    names = [measurement(cls) for cls in reported(events)]
    assert names and len(names) == len(set(names))
    assert {events.PlanPublished, events.SearchEnded, events.Imagined} <= set(reported(events))


def test_a_plan_published_is_said_with_its_steps_and_written_as_a_point_per_step(monkeypatch):
    """Hanoi's three disks at a budget that finds the seven moves: the plan is said with its steps in the order they are
    walked, each the action it fills and the values it takes, and its history is a point per step, tagged as a step
    taken is and by its place in the plan."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(HANOI, "hanoi"), "hanoi", budget=400)
    heard = []
    runtime.parts["planning"].planner.plan_published.connect(heard.append)
    runtime.run(passes=1, poll_s=0)
    (published,) = heard
    assert [(s.action, dict(s.parameters)) for s in published.steps] == [
        ("Move", {"disk": "disk_1", "onto": "PegC"}), ("Move", {"disk": "disk_2", "onto": "PegB"}),
        ("Move", {"disk": "disk_1", "onto": "PegB"}), ("Move", {"disk": "disk_3", "onto": "PegC"}),
        ("Move", {"disk": "disk_1", "onto": "PegA"}), ("Move", {"disk": "disk_2", "onto": "PegC"}),
        ("Move", {"disk": "disk_1", "onto": "PegC"})], "the seven moves, in the order they are walked"
    points = published.point()
    assert [p["tags"]["order"] for p in points] == [str(n) for n in range(7)]
    assert all(p["measurement"] == "Plan" and p["time"] == published.at and p["tags"]["action"] == "Move" for p in points)
    assert points[0]["tags"] == {"disk": "disk_1", "onto": "PegC", "action": "Move", "want": points[0]["tags"]["want"],
                                 "plan": points[0]["tags"]["plan"], "order": "0"}
