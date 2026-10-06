"""The courier in the 0.2.0 runtime: the world boots from the files beside this test, the driver
plans and takes its own drives, and the runtime stops when the parcel stands at its door."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.ontology import STATE

WANT = "http://example.org/orexis/planning#WantGraph"   # planning's word; the Planner is all planning exports
from agent.planning.planner import Planner
from agent.runtime import MET, Runtime, boot
from agent.store import graphs_of, rows

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

_WHERE_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?cell WHERE { ?parcel a courier:Parcel ; courier:at ?cell }"""
_ACTS_Q = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a a execution:Act } }"
#  WHAT THE WANT'S ESTIMATE READ IN THE PRESENT GROUND, beside what the plan the search found spent.
_ESTIMATE_AGAINST_COST_Q = """
SELECT ?want ?left ?spent WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?want ; planning:weighs ?g ;
    planning:remaining ?left . ?g a planning:GroundGraph }
  GRAPH ?p { ?p a planning:Plan ; planning:for ?want ; planning:outcome planning:Satisfied ; planning:spent ?spent } }"""


def _parcel_at(store) -> list[str]:
    return [r["cell"].rsplit("#", 1)[-1] for r in rows(store, _WHERE_Q, graphs_of(store, STATE, "http://example.org/orexis#WorldGraph"))]


def _acts(runtime) -> int:
    return int(rows(runtime.parts["execution"].executor.intentions, _ACTS_Q, ())[0]["n"])


def test_the_boot_says_what_each_graph_is():
    beliefs = boot(WORLD, "courier")
    assert len(graphs_of(beliefs, WANT)) == 1 and len(graphs_of(beliefs, STATE)) == 1
    assert _parcel_at(beliefs) == ["c1_2"], "the parcel stands where the delivery was posed"


def _ticking(monkeypatch, seconds: float = 1.0) -> None:
    """One timeline that moves on by `seconds` at every read, as a running agent's clock does. A
    DRIVE LANDS HALF A MINUTE AFTER IT IS TAKEN (#901, `domains/courier/actions.ttl`), and the
    executor looks for the van at the next cell from then; held at one instant, the clock would
    never reach it and the run would never end — a clock that does not tick is a test's mistake."""
    ticks = iter(range(1, 1_000_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=seconds * next(ticks)))


def test_the_parcel_is_delivered_in_eight_steps_and_the_runtime_stops(monkeypatch):
    """Three drives, the pick, three drives, the drop: the cheapest delivery, found by a search
    the drives-owed estimate guides — and walked a drive at a time, each landing half a minute
    after it is taken, so the run is passes until the last lands and the want is reached."""
    _ticking(monkeypatch)
    runtime = Runtime(boot(WORLD, "courier"), "courier", budget=128)
    assert runtime.run(poll_s=0) == MET
    assert _acts(runtime) == 8 and _parcel_at(runtime.beliefs) == ["c3_3"]
    assert runtime.run(poll_s=0) == MET and _acts(runtime) == 8, "met stays met, and nothing moves again"


def test_the_wants_estimate_at_the_present_never_exceeds_what_the_plan_cost(monkeypatch):
    """THE ONE PROMISE AN ESTIMATE MAKES, as a gate (#898): `courier:drivesOwed` read at the present
    ground is at most what the eight-step plan spent. An estimate that overstates lets a pass end
    with a dearer plan than exists, and nothing in the suite held one to the promise before — the
    domain's comment stated it and eyes checked. The figure here is tight, eight against eight: three
    drives to the parcel, the pick, three drives to the door and the drop, each certain and each
    counted once, where the drives alone read six."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    planner = Planner(boot(WORLD, "courier"), "courier", budget=128)
    planner.plan(NOW)
    (im,) = planner.imaginaria.values()
    judged = [(float(r["left"]), float(r["spent"])) for r in rows(im, _ESTIMATE_AGAINST_COST_Q, ())]
    assert len(judged) == 1, f"the one want, its estimate and its plan: {judged}"
    assert all(left <= spent for left, spent in judged), f"an estimate never overstates what the plan cost: {judged}"
    assert judged == [(8.0, 8.0)], f"and here it is tight: {judged}"


def test_a_budget_that_cuts_the_search_short_is_finished_by_the_passes_after(monkeypatch):
    """Sixteen candidates a pass cannot reach the far corner in one pass; the passes together
    are the one-shot search. The clock ticks, as a running agent's does, and the passes are
    enough for the search and then for six drives to land, half a minute each."""
    _ticking(monkeypatch)
    runtime = Runtime(boot(WORLD, "courier"), "courier", budget=16)
    assert runtime.run(passes=200, poll_s=0) == MET
    assert _acts(runtime) == 8


def test_a_lived_in_volume_keeps_the_agents_state_and_reloads_the_worlds(monkeypatch):
    _ticking(monkeypatch)
    beliefs = boot(WORLD, "courier")
    Runtime(beliefs, "courier", budget=128).run(poll_s=0)
    boot(WORLD, "courier", beliefs)                   # a restart on the same volume
    assert _parcel_at(beliefs) == ["c3_3"], "the delivered parcel is the agent's belief, not the file's"
    assert len(graphs_of(beliefs, STATE)) == 1
    assert graphs_of(beliefs, WANT) == [], "the want was reached and withdrawn, and a restart does not bring it back"
