"""The history of the lane, viewed: the courier's road drawn by the courier's scene, and on it what coordination, planning and
execution decided, each drawn by its own package (`onboarding/history/`) from the rows its queries answer over a journal
and observations. Held on a journal written by the packages' own event classes and points written by hand, one of each
kind, rendered by the page's own components under Node with no browser; and on one walk that keeps each courier's
journal and records its observations through the head-on meeting, and replays it, the two couriers seen by each other
where each is fixed and agreeing who won. Every drawing is held to the contract by TypeScript's own check."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent.coordination.events import ASKED, FORESEEN, SAID, Concluded, Conflict, Held
from agent.coordination.holdings import Holding
from agent.execution.events import StepAnswered, StepTaken
from agent.journal import Journal, install as keep, literal, mint
from agent.planning.events import PlanPublished
from agent.speech.events import Heard, Said
from agent.series import HISTORY, install
from onboarding import reading
from onboarding.history import (data, drawings, entries, headless, kept, page, queries, recorder, recording, run_of,
                               thinned)

LANE = Path(__file__).resolve().parents[1]
REPO = LANE.parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
L, COURIER = "http://example.org/orexis/world/lane#", "http://example.org/orexis/courier#"
PLANNING, EXECUTION = "http://example.org/orexis/planning#", "http://example.org/orexis/execution#"
COORDINATION = "http://example.org/orexis/coordination#"
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


@pytest.fixture(scope="module")
def world():
    return reading.world(LANE)


def test_the_lane_is_drawn_by_the_courier_s_scene_and_by_each_package_s_own_layer():
    assert [p.relative_to(REPO).as_posix() for p in drawings(LANE)] == [
        "domains/courier/ui/index.tsx", "agent/coordination/ui/index.tsx", "agent/execution/ui/index.tsx", "agent/planning/ui/index.tsx",
        "agent/speech/ui/index.tsx"]


def test_every_drawing_holds_to_the_contract_the_core_states():
    """`npm run check`: TypeScript over the core and every scene and layer in the tree, strictly — a drawing that reads a
    prop the core does not hand it, or hands back what the contract does not take, fails here and not in a page."""
    checked = subprocess.run(["npx", "tsc", "--noEmit", "-p", "onboarding/history/tsconfig.json"], cwd=REPO, capture_output=True, text=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr


def _at(seconds: int) -> datetime:
    return NOW + timedelta(seconds=seconds)


def _observed(measurement, feature, sensor, value, t):
    return {"measurement": measurement, "tags": {"feature": feature, "sensor": sensor}, "fields": {"value": float(value)}, "time": _at(t)}


def _n(name: str) -> ox.NamedNode:
    return ox.NamedNode(L + name)


def _t(s, p, o) -> ox.Triple:
    return ox.Triple(s, p, o)


def _drive(step: str, plan: str, to_x: int, then: str | None = None) -> list[ox.Triple]:
    """A drive of van A to (`to_x`, 1), a step of `plan`, as a plan graph states it."""
    s = _n(step)
    out = [_t(s, ox.NamedNode(EXECUTION + "partOf"), _n(plan)), _t(s, ox.NamedNode(PLANNING + "fills"), ox.NamedNode(COURIER + "Drive")),
           _t(s, ox.NamedNode(COURIER + "van"), _n("van_a")), _t(s, ox.NamedNode(COURIER + "toX"), literal(to_x)),
           _t(s, ox.NamedNode(COURIER + "toY"), literal(1)), _t(s, ox.NamedNode(PLANNING + "spent"), literal(1.0))]
    return out + ([_t(s, ox.NamedNode(EXECUTION + "then"), _n(then))] if then else [])


def _act(step: str, plan: str, to_x: int) -> tuple[str, tuple]:
    act = L + step + ".act"
    said = (_t(ox.NamedNode(act), ox.NamedNode(EXECUTION + "of"), _n(step)),
            _t(ox.NamedNode(act), ox.NamedNode(EXECUTION + "taken"), literal(True)),
            *_drive(step, plan, to_x), _t(_n("intention"), ox.NamedNode(EXECUTION + "pursues"), _n("w")))
    return act, said


def _holding(thing: str, x: int, start=None, end=None, taken=False) -> Holding:
    return Holding(L + thing, ((COURIER + "x", literal(x)), (COURIER + "y", literal(1)), (str(_TYPE.value), ox.NamedNode(COURIER + "Van"))),
                   start, end, taken)


#  ONE AGENT'S RUN, an event of each kind in its journal and a point of each kind it observed: its van fixed at (0, 1)
#  and then (1, 1); van B heard two cells on, and then beyond the receiver's range; a plan of two drives, the first taken
#  and answered; van A asked with at (1, 1), van B said at (2, 1) and foreseen at two places, each for a window ending at
#  twenty seconds; and a conflict won.
_OBSERVED = [
    _observed("Column", "van_a", "fix_a_column", 0, 0), _observed("Row", "van_a", "fix_a_row", 1, 0),
    _observed("RelativeColumn", "contact_b", "receiver_b_column", 2, 0), _observed("RelativeRow", "contact_b", "receiver_b_row", 0, 0),
    _observed("Column", "van_a", "fix_a_column", 1, 30), _observed("Row", "van_a", "fix_a_row", 1, 30),
    _observed("RelativeColumn", "contact_b", "receiver_b_column", 5, 30), _observed("RelativeRow", "contact_b", "receiver_b_row", 0, 30)]
_PLAN = (_t(_n("p"), _TYPE, ox.NamedNode(PLANNING + "Plan")), _t(_n("p"), ox.NamedNode(PLANNING + "for"), _n("w")),
         *_drive("p.0", "p", 1, then="p.1"), *_drive("p.1", "p", 2))
_ACT = _act("p.0", "p", 1)
_EVENTS = [
    PlanPublished(L + "p", L + "w", at=_at(0), said=_PLAN),
    StepTaken(L + "p.0", _at(0), act=_ACT[0], said=_ACT[1]),
    Held(_at(0), FORESEEN, L + "courier_b", L + "c", (_holding("van_b.at.2.1", 2, _at(0), _at(20)), _holding("van_b.at.3.1", 3, _at(0), _at(20)))),
    Held(_at(0), ASKED, L + "courier_b", L + "c", (_holding("van_a", 1, _at(0), None, True),)),
    Held(_at(0), SAID, L + "courier_b", L + "c", (_holding("van_b", 2, None, _at(20)),)),
    Concluded(_at(0), (Conflict(L + "courier_a.courier_b.c", L + "courier_b", L + "c", True, True, 0, L + "courier_a"),)),
    StepAnswered(L + "p.0", _at(30), landed=True, act=_ACT[0], said=_ACT[1]),
    Held(_at(30), FORESEEN, L + "courier_b", L + "c"),
    Said(L + "q", (L + "courier_b",), _at(0), (COORDINATION + "QuestionGraph",), (_t(_n("q"), ox.NamedNode(COORDINATION + "asks"), _n("courier_a")),)),
    Heard(L + "a", _at(10), (COORDINATION + "AnswerGraph",)),
]


def _journal(events) -> Journal:
    journal = Journal()
    for event in events:
        journal.record(node := mint(), event.statements(node), event.at)
    return journal


def _drawn(world, journals=None, points=None):
    journals = journals or {"courier_a": _journal(_EVENTS).store}
    points = points if points is not None else {"courier_a": _OBSERVED}
    return data("lane", run_of(world, journals, points), queries(drawings(LANE)))


def _pane(world, at: int, journals=None, points=None, agents=("courier_a",)) -> ET.Element:
    return ET.fromstring(headless(_drawn(world, journals, points), drawings(LANE), pane=("road", list(agents), at)))


def _marks(svg: ET.Element, attribute: str) -> list[tuple]:
    return sorted((e.get(attribute), e.get("data-x"), e.get("data-y")) for e in svg.iter() if e.get(attribute) is not None)


def test_every_drawing_reads_its_own_queries_and_no_two_share_a_name():
    assert sorted(queries(drawings(LANE))) == ["Concluded", "Fixed", "Held", "Plan", "Seen", "Statements", "Step"]


def test_a_pane_draws_each_kind_of_row_where_the_courier_s_scene_places_it(world):
    first, then = _pane(world, 0), _pane(world, 2)          # at nought, and at thirty seconds
    assert _marks(first, "data-fixed") == [("van_a", "0", "1")]
    assert _marks(first, "data-seen") == [("van_b", "2", "1")], "van B two cells on from van A, drawn as van B"
    assert [e.get("data-order") for e in first.iter() if e.get("data-order")] == ["0"], \
        "planning's path: the drive taken at once is walked, the second is left"
    assert [e.get("data-flight") for e in first.iter() if e.get("data-flight")] == ["Drive"], "execution's step in flight"
    assert sorted((e.get("data-thing"), e.get("data-now")) for e in first.iter() if e.get("data-origin") == "foreseen") == [
        ("van_b.at.2.1", "true"), ("van_b.at.3.1", "true")], "coordination's foreseen places, while their window holds"
    assert sorted((e.get("data-origin"), e.get("data-thing")) for e in first.iter() if e.get("data-origin") in ("asked", "said")) == [
        ("asked", "van_a"), ("said", "van_b")], "what it asked with and what the peer said"
    assert [e.get("data-conflict") for e in first.iter() if e.get("data-conflict")] == ["courier_b"], "coordination's status"
    assert [e.get("data-exchange") for e in first.iter() if e.get("data-exchange")] == ["courier_a"], "speech's status"
    assert _marks(then, "data-fixed") == [("van_a", "1", "1")]
    assert _marks(then, "data-seen") == [], "an offset beyond the range its receiver declares sees nothing"
    assert [e.get("data-order") for e in then.iter() if e.get("data-order")] == ["0"], "the drive left is still the path"
    assert not [e for e in then.iter() if e.get("data-flight") or e.get("data-origin") == "foreseen"], "nothing in flight, nothing foreseen"
    assert sorted((e.get("data-origin"), e.get("data-now")) for e in then.iter() if e.get("data-origin")) == [
        ("asked", "true"), ("said", "false")], "the peer's word past its window, still laid, faint"


def test_the_log_says_each_thing_the_agent_did_in_the_words_of_the_package_that_did_it(world):
    lines = headless(_drawn(world), drawings(LANE), log_of=["courier_a"])
    assert not any(line.startswith(("Fixed", "Seen")) for line in lines), lines
    assert "published a plan for w: Drive(toX=1, toY=1, van=van_a) → Drive(toX=2, toY=1, van=van_a)" in lines, \
        "a figure the search wrote of a step is no value the action takes"
    assert "took Drive(toX=1, toY=1, van=van_a)" in lines and "Drive(toX=1, toY=1, van=van_a) landed" in lines
    assert "foreseen of courier_b: van_b.at.2.1 x=2 y=1, van_b.at.3.1 x=3 y=1" in lines
    assert "foreseen nothing of courier_b" in lines
    assert "conflict with courier_b over c: standing, silent, round 0, won by courier_a" in lines
    assert "said QuestionGraph to courier_b" in lines and "heard AnswerGraph" in lines, "speech's exchange, by the kind each says"


def test_two_agents_shown_together_are_each_drawn_in_their_own_colour_on_one_scene(world):
    """Courier B's run beside courier A's: its own van fixed at (3, 1), asking with it. Shown together, one scene holds
    both vans and each agent's layers, each mark in the colour of the agent that kept it; shown alone, the other's go."""
    b_points = [_observed("Column", "van_b", "fix_b_column", 3, 0), _observed("Row", "van_b", "fix_b_row", 1, 0)]
    b = _journal([Held(_at(0), ASKED, L + "courier_a", L + "c", (_holding("van_b", 3, None, None, True),))])
    journals = {"courier_a": _journal(_EVENTS).store, "courier_b": b.store}
    points = {"courier_a": _OBSERVED, "courier_b": b_points}
    together = _pane(world, 0, journals, points, ("courier_a", "courier_b"))
    alone = _pane(world, 0, journals, points, ("courier_b",))
    fixed = {e.get("data-fixed"): e.get("data-by") for e in together.iter() if e.get("data-fixed")}
    assert fixed == {"van_a": "courier_a", "van_b": "courier_b"}, "each van fixed by its own courier, on one scene"
    tints = {e.get("data-agent"): {r.get("stroke") for r in e.iter() if r.get("data-origin") == "asked"} for e in together.iter()
             if e.get("data-agent") and e.tag == "g" and any(r.get("data-origin") == "asked" for r in e.iter())}
    assert len(tints) == 2 and all(len(t) == 1 for t in tints.values()) and tints["courier_a"] != tints["courier_b"], tints
    assert {e.get("data-fixed") for e in alone.iter() if e.get("data-fixed")} == {"van_b"}, "shown alone, courier B's alone"


def test_a_journal_is_read_since_an_instant_entry_by_entry():
    journal = _journal(_EVENTS)
    assert {q.graph_name for q in entries(journal.store)} == set(journal.store.named_graphs())
    later = {q.graph_name for q in entries(journal.store, _at(10))}
    assert len(later) == 3, "the answer heard at ten seconds; the verdict and the empty set, said at thirty"


def test_a_reading_the_same_as_the_one_before_on_its_series_is_left_out_and_nothing_else_is():
    same = [_observed("Column", "van_a", "fix_a_column", 0, t) for t in (0, 10, 20)] + [_observed("Column", "van_a", "fix_a_column", 1, 30)]
    steps = [{"measurement": "Step", "tags": {"action": "Wait"}, "fields": {"taken": True}, "time": _at(t)} for t in (0, 10)]
    assert [(p["measurement"], p["time"]) for p in thinned(same + steps)] == [
        ("Column", _at(0)), ("Column", _at(30)), ("Step", _at(0)), ("Step", _at(10))]


def test_a_recording_keeps_each_agents_points_apart_and_reads_as_the_series_store_keeps_them(tmp_path):
    path = tmp_path / "walk.jsonl"
    point = {"measurement": "Column", "tags": {}, "fields": {"count": 1}, "time": NOW}
    recorder(path, "courier_a").write([point, {**point, "fields": {"count": 2}}])
    recorder(path, "courier_b").write([point])
    read = recording(path)
    assert {a: [p["fields"]["count"] for p in ps] for a, ps in read.items()} == {"courier_a": [1, 2], "courier_b": [1]}
    assert [p["fields"]["count"] for p in kept(read["courier_a"])] == [2], "one point per measurement, tag set and instant: the last"


def test_the_page_holds_everything_it_draws(world):
    html = page(_drawn(world), drawings(LANE))
    assert "lane history" in html and '"road"' in html and '"coordination"' in html
    assert not re.search(r'<script[^>]+src=|<link[^>]+href=', html), "no script or style from elsewhere"


def test_live_the_page_and_its_data_are_served_on_the_loopback_and_say_they_are_live(world, monkeypatch):
    """`orexis-history lane --live`: the page and `data.json`, each the run as the history view reads it now — here the journal
    of the run above, standing in for the agents' endpoints — and marked live, so the page asks again and follows."""
    import threading
    from urllib.request import urlopen

    import onboarding.history as history_module

    asked = []
    monkeypatch.setattr(history_module, "history", lambda w, since=None, *a, live=False, **k: (
        asked.append((w, since, live)) or {**_drawn(world), "live": live}, drawings(LANE)))
    live = history_module.server("lane", "10m", 0)
    threading.Thread(target=live.serve_forever, daemon=True).start()
    try:
        at = f"http://127.0.0.1:{live.server_address[1]}"
        said = json.loads(urlopen(at + "/data.json").read())
        assert said["live"] is True and said["agents"] == ["courier_a"] and len(said["instants"]) == 3
        assert b"lane live" in urlopen(at + "/").read()
        assert asked[0] == ("lane", "10m", True), "asked for the window, live"
    finally:
        live.shutdown()


# ------------------------------------------------------------------ a walk, recorded and replayed

_spec = importlib.util.spec_from_file_location("lane_harness", Path(__file__).with_name("test_lane.py"))
_lane = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lane)


@pytest.mark.walk
def test_the_head_on_meeting_is_recorded_and_replayed_with_each_courier_seeing_the_other_and_both_agreeing_who_won(
        monkeypatch, tmp_path, world):
    """The lane's two couriers driving at each other, each keeping a journal and recording its observations, walked until
    both have concluded who won their draw; replayed at the last instant, each pane holds its own van as fixed and the
    other as seen where the other is fixed, and the conflict won by the same courier in both."""
    path = tmp_path / "head_on.jsonl"
    journals = {courier: Journal(now=lambda: NOW) for courier in ("courier_a", "courier_b")}
    for courier, journal in journals.items():
        install(HISTORY, recorder(path, courier), courier)
        keep(journal, courier)

    def won() -> dict[str, set]:
        return {a: {r["w"].value for r in j.store.query(
            "SELECT ?w WHERE { ?c <http://example.org/orexis/coordination#wonBy> ?w }", use_default_graph_as_union=True)}
            for a, j in journals.items()}
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
            keep(None, courier)
    assert len(set().union(*won().values())) == 1, f"both agree who won: {won()}"
    spoken = {(r["k"].value.rsplit("#", 1)[-1], r["t"].value.rsplit("#", 1)[-1]) for j in journals.values() for r in j.store.query(
        "SELECT ?k ?t WHERE { ?e a ?k ; <http://example.org/orexis/speech#statement> ?g . ?g a ?t }",
        use_default_graph_as_union=True)}
    assert {(k, t) for k in ("Said", "Heard") for t in ("QuestionGraph", "AnswerGraph", "CommitmentGraph", "RevealGraph")} <= spoken, \
        f"the exchange, said by one and heard by the other, each kind of it: {sorted(spoken)}"
    stores, points = {a: j.store for a, j in journals.items()}, recording(path)
    last = len(_drawn(world, stores, points)["instants"]) - 1
    a, b = (_pane(world, last, stores, points, (agent,)) for agent in ("courier_a", "courier_b"))
    fixed = {name: (x, y) for name, x, y in [*_marks(a, "data-fixed"), *_marks(b, "data-fixed")]}
    assert set(fixed) == {"van_a", "van_b"}
    seen = {name: (x, y) for name, x, y in [*_marks(a, "data-seen"), *_marks(b, "data-seen")] if name in fixed}
    assert seen == fixed, f"each sees the other where the other is fixed: {seen} against {fixed}"
    assert any(e.get("data-order") for pane in (a, b) for e in pane.iter()), "a plan is drawn"
    assert json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',
                                page(_drawn(world, stores, points), drawings(LANE)), re.S).group(1))["agents"] == ["courier_a", "courier_b"]
