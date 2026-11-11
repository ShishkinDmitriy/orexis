"""The history of the lane, viewed: the courier's road drawn by the courier's scene, and on it what coordination, planning and
execution decided, each drawn by its own package (`onboarding/history/`) from the rows its queries answer over a journal
and observations. Held on a journal kept under `journals/`, one event of each kind, and points written by hand, rendered by the page's
own components under Node with no browser. Every drawing is held to the contract by TypeScript's own check."""

from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

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
        "domains/courier/ui/index.tsx", "orexis-coordination/ui/index.tsx", "orexis-execution/ui/index.tsx", "orexis-planning/ui/index.tsx",
        "orexis-speech/ui/index.tsx"]


def test_every_drawing_holds_to_the_contract_the_core_states():
    """`npm run check`: TypeScript over the core and every scene and layer in the tree, strictly — a drawing that reads a
    prop the core does not hand it, or hands back what the contract does not take, fails here and not in a page."""
    checked = subprocess.run(["npx", "tsc", "--noEmit", "-p", "onboarding/history/tsconfig.json"], cwd=REPO, capture_output=True, text=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr


def _at(seconds: int) -> datetime:
    return NOW + timedelta(seconds=seconds)


def _observed(measurement, feature, sensor, value, t):
    return {"measurement": measurement, "tags": {"feature": feature, "sensor": sensor}, "fields": {"value": float(value)}, "time": _at(t)}


#  ONE AGENT'S RUN, an event of each kind in its journal and a point of each kind it observed: its van fixed at (0, 1)
#  and then (1, 1); van B heard two cells on, and then beyond the receiver's range; a plan of two drives, the first taken
#  and answered; van A asked with at (1, 1), van B said at (2, 1) and foreseen at two places, each for a window ending at
#  twenty seconds; and a conflict won.
_OBSERVED = [
    _observed("Column", "van_a", "fix_a_column", 0, 0), _observed("Row", "van_a", "fix_a_row", 1, 0),
    _observed("RelativeColumn", "contact_b", "receiver_b_column", 2, 0), _observed("RelativeRow", "contact_b", "receiver_b_row", 0, 0),
    _observed("Column", "van_a", "fix_a_column", 1, 30), _observed("Row", "van_a", "fix_a_row", 1, 30),
    _observed("RelativeColumn", "contact_b", "receiver_b_column", 5, 30), _observed("RelativeRow", "contact_b", "receiver_b_row", 0, 30)]


def _journal(agent: str) -> ox.Store:
    """The journal `agent` kept, as `journals/` holds it: the entries the binary's journal writes, one named graph each."""
    store = ox.Store()
    store.load(path=str(Path(__file__).parent / "journals" / f"{agent}.nq"), format=ox.RdfFormat.N_QUADS)
    return store


def _drawn(world, journals=None, points=None):
    journals = journals or {"courier_a": _journal("courier_a")}
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
    journals = {"courier_a": _journal("courier_a"), "courier_b": _journal("courier_b")}
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
    journal = _journal("courier_a")
    assert {q.graph_name for q in entries(journal)} == set(journal.named_graphs())
    later = {q.graph_name for q in entries(journal, _at(10))}
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

