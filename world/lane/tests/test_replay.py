"""A replay of the lane: the courier's grid as its view document states it, drawn from the history each courier's
history part wrote (`onboarding/replay.py`). The frames are held on points written by hand, one of each kind; and one
walk records the head-on meeting and replays it, the two couriers seen by each other and agreeing who won."""

from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.series import HISTORY, install
from onboarding import reading
from onboarding.replay import Axis, Grid, _kept, frames, page, recorder, recording, things, views

LANE = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
ROAD = Grid("the_road", "the road", Axis("x", "Column", "RelativeColumn", "toX"), Axis("y", "Row", "RelativeRow", "toY"))


@pytest.fixture(scope="module")
def world():
    return reading.world(LANE)


def test_the_courier_states_the_road_as_a_grid_in_its_own_words(world):
    assert views(world) == [ROAD]


def test_a_contact_is_drawn_from_the_van_carrying_it_as_the_thing_it_is_a_sample_of(world):
    said = things(world)
    assert (said.hosts["contact_b"], said.of["contact_b"], said.hosts["contact_1"], "contact_1" in said.of) == ("van_a", "van_b", "van_a", False)
    assert said.ranges["receiver_b_column"] == (-4.0, 4.0)


def _at(seconds: int) -> datetime:
    return NOW + timedelta(seconds=seconds)


def _observed(measurement, feature, sensor, value, t):
    return {"measurement": measurement, "tags": {"feature": feature, "sensor": sensor}, "fields": {"value": float(value)}, "time": _at(t)}


#  ONE AGENT'S HISTORY, a point of each kind: its van fixed at (0, 1) and then (1, 1); van B heard two cells on, and then
#  beyond the receiver's range; a plan of two drives, the first taken and answered; van B foreseen at two places, the
#  second for a window ending at twenty seconds; and a conflict won.
_HISTORY = [
    _observed("Column", "van_a", "fix_a_column", 0, 0), _observed("Row", "van_a", "fix_a_row", 1, 0),
    _observed("RelativeColumn", "contact_b", "receiver_b_column", 2, 0), _observed("RelativeRow", "contact_b", "receiver_b_row", 0, 0),
    {"measurement": "Plan", "tags": {"action": "Drive", "van": "van_a", "toX": "1", "toY": "1", "want": "w", "plan": "p", "order": "0"},
     "fields": {"lands": "", "latest": ""}, "time": _at(0)},
    {"measurement": "Plan", "tags": {"action": "Drive", "van": "van_a", "toX": "2", "toY": "1", "want": "w", "plan": "p", "order": "1"},
     "fields": {"lands": "", "latest": ""}, "time": _at(0)},
    {"measurement": "Step", "tags": {"action": "Drive", "van": "van_a", "toX": "1", "toY": "1", "want": "w"}, "fields": {"taken": True}, "time": _at(0)},
    {"measurement": "Holdings", "tags": {"origin": "foreseen", "peer": "courier_b", "constraint": "c"}, "fields": {"count": 2}, "time": _at(0)},
    *({"measurement": "Holding", "tags": {"origin": "foreseen", "peer": "courier_b", "constraint": "c", "thing": f"van_b.at.{x}.1", "n": str(n)},
       "fields": {"x": float(x), "y": 1.0, "type": "Van", "from": _at(0).isoformat(), "until": _at(20).isoformat(), "taken": False},
       "time": _at(0)} for n, x in enumerate((2, 3))),
    {"measurement": "Conflicts", "tags": {}, "fields": {"count": 1}, "time": _at(0)},
    {"measurement": "Conflict", "tags": {"peer": "courier_b", "constraint": "c"},
     "fields": {"standing": True, "silent": True, "round": 0, "won_by": "courier_a"}, "time": _at(0)},
    _observed("Column", "van_a", "fix_a_column", 1, 30), _observed("Row", "van_a", "fix_a_row", 1, 30),
    _observed("RelativeColumn", "contact_b", "receiver_b_column", 5, 30), _observed("RelativeRow", "contact_b", "receiver_b_row", 0, 30),
    {"measurement": "Step", "tags": {"action": "Drive", "van": "van_a", "toX": "1", "toY": "1", "want": "w"}, "fields": {"landed": True}, "time": _at(30)},
    {"measurement": "Holdings", "tags": {"origin": "foreseen", "peer": "courier_b", "constraint": "c"}, "fields": {"count": 0}, "time": _at(30)},
]


def test_a_frame_shows_what_each_kind_of_point_places_on_the_grid_at_its_instant(world):
    replay = frames({"courier_a": _HISTORY}, [ROAD], things(world))
    first, then = replay["grids"][0]["frames"]["courier_a"]
    assert replay["instants"] == [_at(0).isoformat(), _at(30).isoformat()]
    assert first["fixed"] == [{"x": 0.0, "y": 1.0, "name": "van_a"}]
    assert first["seen"] == [{"x": 2.0, "y": 1.0, "name": "van_b", "sample": "contact_b"}], "van B two cells on from van A, as van B"
    assert [(c["x"], c["order"]) for c in first["planned"]] == [(1.0, 0), (2.0, 1)]
    assert first["flight"] == [{"x": 1.0, "y": 1.0, "action": "Drive"}]
    assert [(c["x"], c["now"]) for c in first["foreseen"]] == [(2.0, True), (3.0, True)]
    assert first["conflicts"] == [{"peer": "courier_b", "constraint": "c", "standing": True, "silent": True, "round": 0, "won_by": "courier_a"}]
    assert then["fixed"] == [{"x": 1.0, "y": 1.0, "name": "van_a"}]
    assert then["seen"] == [], "an offset beyond the range its receiver declares sees nothing"
    assert [c["x"] for c in then["planned"]] == [2.0], "the drive answered since the plan was published is walked"
    assert then["flight"] == [] and "foreseen" not in then, "the drive answered; the set said again, empty"
    assert replay["grids"][0]["box"] == [0.0, 1.0, 3.0, 1.0]


def test_the_log_says_each_thing_the_agent_did_once_and_leaves_what_a_view_draws_to_the_view(world):
    replay = frames({"courier_a": _HISTORY}, [ROAD], things(world))
    lines = [text for _, text in replay["log"]["courier_a"]]
    assert not any(text.startswith(("Column", "RelativeColumn", "Holdings", "Conflicts")) for text in lines)
    assert "published a plan for w: Drive(toX=1, toY=1, van=van_a) → Drive(toX=2, toY=1, van=van_a)" in lines
    assert "foreseen: van_b.at.2.1 type=Van x=2 y=1, van_b.at.3.1 type=Van x=3 y=1" in lines
    assert "foreseen nothing of courier_b" in lines
    assert "conflict with courier_b over c: standing, silent, round 0, won by courier_a" in lines


def test_a_world_whose_domains_state_no_view_is_drawn_by_the_core_alone():
    replay = frames({"courier_a": _HISTORY}, [], things(reading.world(LANE)))
    assert replay["grids"] == [] and replay["log"]["courier_a"]


def test_a_recording_keeps_each_agents_points_apart_and_replays_as_the_series_store_keeps_them(tmp_path):
    path = tmp_path / "walk.jsonl"
    point = {"measurement": "Conflicts", "tags": {}, "fields": {"count": 1}, "time": NOW}
    recorder(path, "courier_a").write([point, {**point, "fields": {"count": 2}}])
    recorder(path, "courier_b").write([point])
    read = recording(path)
    assert {a: [p["fields"]["count"] for p in ps] for a, ps in read.items()} == {"courier_a": [1, 2], "courier_b": [1]}
    assert [p["fields"]["count"] for p in _kept(read["courier_a"])] == [2], "one point per measurement, tag set and instant: the last"


def test_the_page_holds_everything_it_draws(world):
    html = page("lane", frames({"courier_a": _HISTORY}, [ROAD], things(world)))
    assert "lane replay" in html and '"instants":[' in html
    assert not re.search(r'<script[^>]+src=|<link[^>]+href=', html), "no script or style from elsewhere"


# ------------------------------------------------------------------ a walk, recorded and replayed

_spec = importlib.util.spec_from_file_location("lane_harness", Path(__file__).with_name("test_lane.py"))
_lane = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lane)


@pytest.mark.walk
def test_the_head_on_meeting_is_recorded_and_replayed_with_each_courier_seeing_the_other_and_both_agreeing_who_won(
        monkeypatch, tmp_path, world):
    """The lane's two couriers driving at each other, each with a recorder for its history, walked until both have
    concluded who won their draw and a pass more; replayed, each pane holds its own van as fixed and the other as seen,
    each courier's plan and the conflict, won by the same courier in both."""
    path = tmp_path / "head_on.jsonl"
    for courier in ("courier_a", "courier_b"):
        install(HISTORY, recorder(path, courier), courier)
    try:
        bus, time = _lane._lane(monkeypatch, _lane.variant(tmp_path, "head_on", _lane._HEAD_ON))
        bus.simulator.open()
        bus.simulator.step(_lane.NOW)
        for runtime in bus.runtimes.values():
            runtime.run(passes=1, poll_s=0)
        for _ in range(20):
            replay = frames(recording(path), views(world), things(world))
            last = {a: f[-1] for a, f in replay["grids"][0]["frames"].items()}
            if all(any(c["won_by"] for c in f["conflicts"]) for f in last.values()):
                break
            time["at"] += timedelta(seconds=_lane.CADENCE_S)
            bus.simulator.step(time["at"])
            for runtime in bus.runtimes.values():
                runtime.run(passes=1, poll_s=0)
        else:
            raise AssertionError("no draw won within twenty ticks")
    finally:
        for courier in ("courier_a", "courier_b"):
            install(HISTORY, None, courier)
    assert replay["agents"] == ["courier_a", "courier_b"]
    a, b = last["courier_a"], last["courier_b"]
    assert [c["name"] for c in a["fixed"]] == ["van_a"] and [c["name"] for c in b["fixed"]] == ["van_b"]
    assert "van_b" in {c["name"] for c in a["seen"]} and "van_a" in {c["name"] for c in b["seen"]}, "each sees the other"
    seen = {f: next((c["x"], c["y"]) for c in other["seen"] if c["name"] == thing)
            for f, other, thing in (("van_b", a, "van_b"), ("van_a", b, "van_a"))}
    fixed = {c["name"]: (c["x"], c["y"]) for c in (*a["fixed"], *b["fixed"])}
    assert seen == fixed, f"what each sees is where the other is fixed: {seen} against {fixed}"
    won = {f["conflicts"][i]["won_by"] for f in (a, b) for i, c in enumerate(f["conflicts"]) if c["won_by"]}
    assert len(won) == 1, f"both agree who won: {won}"
    assert any(f["planned"] for f in (a, b)), "a plan is drawn"
    assert json.loads(re.search(r'<script id="replay" type="application/json">(.*?)</script>', page("lane", replay), re.S).group(1)) == replay
