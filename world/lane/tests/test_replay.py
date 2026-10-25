"""A replay of the lane: the courier's road drawn by the courier's scene, and on it what coordination, planning and
execution decided, each drawn by its own package (`onboarding/replay/`). Held on points written by hand, one of each
kind, rendered by the page's own components under Node with no browser; and on one walk that records the head-on
meeting and replays it, the two couriers seen by each other where each is fixed and agreeing who won. Every drawing is
held to the contract by TypeScript's own check."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.series import HISTORY, install
from onboarding import reading
from onboarding.replay import data, drawings, headless, kept, page, recorder, recording, thinned, things

LANE = Path(__file__).resolve().parents[1]
REPO = LANE.parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def world():
    return reading.world(LANE)


def test_the_lane_is_drawn_by_the_courier_s_scene_and_by_each_package_s_own_layer():
    assert [p.relative_to(REPO).as_posix() for p in drawings(LANE)] == [
        "domains/courier/replay.tsx", "agent/coordination/replay.tsx", "agent/execution/replay.tsx", "agent/planning/replay.tsx"]


def test_every_drawing_holds_to_the_contract_the_core_states():
    """`npm run check`: TypeScript over the core and every scene and layer in the tree, strictly — a drawing that reads a
    prop the core does not hand it, or hands back what the contract does not take, fails here and not in a page."""
    checked = subprocess.run(["npx", "tsc", "--noEmit", "-p", "onboarding/replay/tsconfig.json"], cwd=REPO, capture_output=True, text=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr


def _at(seconds: int) -> datetime:
    return NOW + timedelta(seconds=seconds)


def _observed(measurement, feature, sensor, value, t):
    return {"measurement": measurement, "tags": {"feature": feature, "sensor": sensor}, "fields": {"value": float(value)}, "time": _at(t)}


#  ONE AGENT'S HISTORY, a point of each kind: its van fixed at (0, 1) and then (1, 1); van B heard two cells on, and then
#  beyond the receiver's range; a plan of two drives, the first taken and answered; van A asked with at (1, 1), van B
#  said at (2, 1) and foreseen at two places, each for a window ending at twenty seconds; and a conflict won.
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
    *({"measurement": "Holdings", "tags": {"origin": origin, "peer": "courier_b", "constraint": "c"}, "fields": {"count": 1}, "time": _at(0)}
      for origin in ("asked", "said")),
    {"measurement": "Holding", "tags": {"origin": "asked", "peer": "courier_b", "constraint": "c", "thing": "van_a", "n": "0"},
     "fields": {"x": 1.0, "y": 1.0, "from": _at(0).isoformat(), "until": "", "taken": True}, "time": _at(0)},
    {"measurement": "Holding", "tags": {"origin": "said", "peer": "courier_b", "constraint": "c", "thing": "van_b", "n": "0"},
     "fields": {"x": 2.0, "y": 1.0, "from": "", "until": _at(20).isoformat(), "taken": False}, "time": _at(0)},
    {"measurement": "Conflicts", "tags": {}, "fields": {"count": 1}, "time": _at(0)},
    {"measurement": "Conflict", "tags": {"peer": "courier_b", "constraint": "c"},
     "fields": {"standing": True, "silent": True, "round": 0, "won_by": "courier_a"}, "time": _at(0)},
    _observed("Column", "van_a", "fix_a_column", 1, 30), _observed("Row", "van_a", "fix_a_row", 1, 30),
    _observed("RelativeColumn", "contact_b", "receiver_b_column", 5, 30), _observed("RelativeRow", "contact_b", "receiver_b_row", 0, 30),
    {"measurement": "Step", "tags": {"action": "Drive", "van": "van_a", "toX": "1", "toY": "1", "want": "w"}, "fields": {"landed": True}, "time": _at(30)},
    {"measurement": "Holdings", "tags": {"origin": "foreseen", "peer": "courier_b", "constraint": "c"}, "fields": {"count": 0}, "time": _at(30)},
]


def test_what_the_world_states_of_a_thing_the_history_names_is_handed_to_the_scenes(world):
    said = things(world, {"courier_a": _HISTORY})
    assert (said["contact_b"]["isHostedBy"], said["contact_b"]["isSampleOf"]) == (["van_a"], ["van_b"])
    (capability,) = said["receiver_b_column"]["hasSystemCapability"]
    (span,) = [p for p in capability["hasSystemProperty"] if "MeasurementRange" in p["type"]]
    assert (span["minValue"], span["maxValue"]) == ([-4.0], [4.0])
    assert "hedge_2_0" not in said, "a thing no point names is not handed over"


def _drawn(world, history=None):
    history = history or {"courier_a": _HISTORY}
    return data("lane", history, things(world, history))


def _pane(world, at: int, history=None, agents=("courier_a",)) -> ET.Element:
    return ET.fromstring(headless(_drawn(world, history), drawings(LANE), pane=("road", list(agents), at)))


def _marks(svg: ET.Element, attribute: str) -> list[tuple]:
    return sorted((e.get(attribute), e.get("data-x"), e.get("data-y")) for e in svg.iter() if e.get(attribute) is not None)


def test_a_pane_draws_each_kind_of_point_where_the_courier_s_scene_places_it(world):
    first, then = _pane(world, 0), _pane(world, 1)
    assert _marks(first, "data-fixed") == [("van_a", "0", "1")]
    assert _marks(first, "data-seen") == [("van_b", "2", "1")], "van B two cells on from van A, drawn as van B"
    assert [e.get("data-order") for e in first.iter() if e.get("data-order")] == ["0", "1"], "planning's path"
    assert [e.get("data-flight") for e in first.iter() if e.get("data-flight")] == ["Drive"], "execution's step in flight"
    assert sorted((e.get("data-thing"), e.get("data-now")) for e in first.iter() if e.get("data-origin") == "foreseen") == [
        ("van_b.at.2.1", "true"), ("van_b.at.3.1", "true")], "coordination's foreseen places, while their window holds"
    assert sorted((e.get("data-origin"), e.get("data-thing")) for e in first.iter() if e.get("data-origin") in ("asked", "said")) == [
        ("asked", "van_a"), ("said", "van_b")], "what it asked with and what the peer said"
    assert [e.get("data-conflict") for e in first.iter() if e.get("data-conflict")] == ["courier_b"], "coordination's status"
    assert _marks(then, "data-fixed") == [("van_a", "1", "1")]
    assert _marks(then, "data-seen") == [], "an offset beyond the range its receiver declares sees nothing"
    assert [e.get("data-order") for e in then.iter() if e.get("data-order")] == ["1"], "the drive answered since is walked"
    assert not [e for e in then.iter() if e.get("data-flight") or e.get("data-origin") == "foreseen"], "nothing in flight, nothing foreseen"
    assert [(e.get("data-origin"), e.get("data-now")) for e in then.iter() if e.get("data-origin")] == [
        ("asked", "true"), ("said", "false")], "the peer's word past its window, still laid, faint"


def test_the_log_says_each_thing_the_agent_did_in_the_words_of_the_package_that_did_it(world):
    lines = headless(_drawn(world), drawings(LANE), log_of=["courier_a"])
    assert not any(line.startswith(("Column", "RelativeColumn", "Holdings", "Conflicts")) for line in lines), lines
    assert "published a plan for w: Drive(toX=1, toY=1, van=van_a) → Drive(toX=2, toY=1, van=van_a)" in lines
    assert "took Drive(toX=1, toY=1, van=van_a) for w" in lines and "Drive(toX=1, toY=1, van=van_a) landed for w" in lines
    assert "foreseen of courier_b: van_b.at.2.1 type=Van x=2 y=1, van_b.at.3.1 type=Van x=3 y=1" in lines
    assert "foreseen nothing of courier_b" in lines
    assert "conflict with courier_b over c: standing, silent, round 0, won by courier_a" in lines


def test_two_agents_shown_together_are_each_drawn_in_their_own_colour_on_one_scene(world):
    """Courier B's history beside courier A's: its own van fixed at (3, 1). Shown together, one scene holds both vans and
    each agent's layers, each mark in the colour of the agent whose history said it; shown alone, the other's are gone."""
    b = [_observed("Column", "van_b", "fix_b_column", 3, 0), _observed("Row", "van_b", "fix_b_row", 1, 0),
         {"measurement": "Holdings", "tags": {"origin": "asked", "peer": "courier_a", "constraint": "c"}, "fields": {"count": 1}, "time": _at(0)},
         {"measurement": "Holding", "tags": {"origin": "asked", "peer": "courier_a", "constraint": "c", "thing": "van_b", "n": "0"},
          "fields": {"x": 3.0, "y": 1.0, "from": "", "until": "", "taken": True}, "time": _at(0)}]
    history = {"courier_a": _HISTORY, "courier_b": b}
    together, alone = _pane(world, 0, history, ("courier_a", "courier_b")), _pane(world, 0, history, ("courier_b",))
    fixed = {e.get("data-fixed"): e.get("data-by") for e in together.iter() if e.get("data-fixed")}
    assert fixed == {"van_a": "courier_a", "van_b": "courier_b"}, "each van fixed by its own courier, on one scene"
    tints = {e.get("data-agent"): {r.get("stroke") for r in e.iter() if r.get("data-origin") == "asked"} for e in together.iter()
             if e.get("data-agent") and e.tag == "g" and any(r.get("data-origin") == "asked" for r in e.iter())}
    assert len(tints) == 2 and all(len(t) == 1 for t in tints.values()) and tints["courier_a"] != tints["courier_b"], tints
    assert {e.get("data-fixed") for e in alone.iter() if e.get("data-fixed")} == {"van_b"}, "shown alone, courier B's alone"


def test_a_reading_the_same_as_the_one_before_on_its_series_is_left_out_and_nothing_else_is():
    same = [_observed("Column", "van_a", "fix_a_column", 0, t) for t in (0, 10, 20)] + [_observed("Column", "van_a", "fix_a_column", 1, 30)]
    steps = [{"measurement": "Step", "tags": {"action": "Wait"}, "fields": {"taken": True}, "time": _at(t)} for t in (0, 10)]
    assert [(p["measurement"], p["time"]) for p in thinned(same + steps)] == [
        ("Column", _at(0)), ("Column", _at(30)), ("Step", _at(0)), ("Step", _at(10))]


def test_a_recording_keeps_each_agents_points_apart_and_replays_as_the_series_store_keeps_them(tmp_path):
    path = tmp_path / "walk.jsonl"
    point = {"measurement": "Conflicts", "tags": {}, "fields": {"count": 1}, "time": NOW}
    recorder(path, "courier_a").write([point, {**point, "fields": {"count": 2}}])
    recorder(path, "courier_b").write([point])
    read = recording(path)
    assert {a: [p["fields"]["count"] for p in ps] for a, ps in read.items()} == {"courier_a": [1, 2], "courier_b": [1]}
    assert [p["fields"]["count"] for p in kept(read["courier_a"])] == [2], "one point per measurement, tag set and instant: the last"


def test_the_page_holds_everything_it_draws(world):
    html = page(_drawn(world), drawings(LANE))
    assert "lane replay" in html and '"road"' in html and '"coordination"' in html
    assert not re.search(r'<script[^>]+src=|<link[^>]+href=', html), "no script or style from elsewhere"


# ------------------------------------------------------------------ a walk, recorded and replayed

_spec = importlib.util.spec_from_file_location("lane_harness", Path(__file__).with_name("test_lane.py"))
_lane = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lane)


@pytest.mark.walk
def test_the_head_on_meeting_is_recorded_and_replayed_with_each_courier_seeing_the_other_and_both_agreeing_who_won(
        monkeypatch, tmp_path, world):
    """The lane's two couriers driving at each other, each with a recorder for its history, walked until both have
    concluded who won their draw; replayed at the last instant, each pane holds its own van as fixed and the other as
    seen where the other is fixed, and the conflict won by the same courier in both."""
    path = tmp_path / "head_on.jsonl"
    for courier in ("courier_a", "courier_b"):
        install(HISTORY, recorder(path, courier), courier)

    def won() -> dict[str, set]:
        history = recording(path) if path.exists() else {}
        return {a: {p["fields"]["won_by"] for p in ps if p["measurement"] == "Conflict" and p["fields"]["won_by"]} for a, ps in history.items()}
    try:
        bus, time = _lane._lane(monkeypatch, _lane.variant(tmp_path, "head_on", _lane._HEAD_ON))
        bus.simulator.open()
        bus.simulator.step(_lane.NOW)
        for runtime in bus.runtimes.values():
            runtime.run(passes=1, poll_s=0)
        for _ in range(20):
            if len(won()) == 2 and all(won().values()):
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
    assert len(set().union(*won().values())) == 1, f"both agree who won: {won()}"
    history = recording(path)
    last = len(data("lane", history, {})["instants"]) - 1
    a, b = (_pane(world, last, history, (agent,)) for agent in ("courier_a", "courier_b"))
    fixed = {name: (x, y) for name, x, y in [*_marks(a, "data-fixed"), *_marks(b, "data-fixed")]}
    assert set(fixed) == {"van_a", "van_b"}
    seen = {name: (x, y) for name, x, y in [*_marks(a, "data-seen"), *_marks(b, "data-seen")] if name in fixed}
    assert seen == fixed, f"each sees the other where the other is fixed: {seen} against {fixed}"
    assert any(e.get("data-order") for pane in (a, b) for e in pane.iter()), "a plan is drawn"
    assert json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',
                                page(data("lane", history, {}), drawings(LANE)), re.S).group(1))["agents"] == ["courier_a", "courier_b"]
