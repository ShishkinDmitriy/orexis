"""Tower of Hanoi in the 0.2.0 runtime: the world boots from the files beside this test, the mover
plans the tower, and the runtime stops `planned` once the plan is published — the mover is a planner
and no executor, so the plan is its output and nothing walks it (#928). The tower stays as posed;
a plan walked to a solved world is the courier's to show (`world/courier/tests/`)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.ontology import STATE

WANT = "http://example.org/orexis/planning#WantGraph"   # planning's word; the Planner is all planning exports
from agent.runtime import PLANNED, Runtime, boot
from agent.store import graphs_of, rows

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
HANOI = "http://example.org/orexis/hanoi#"
PLAN = "http://example.org/orexis#PlanGraph"

#  THE DISKS HOME, read off the state by kind: a published plan's steps state the same rows in the
#  graphs they predict in, and a prediction of a disk on C is not a disk on C.
_HOME_Q = """PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:StateGraph }
  GRAPH ?g { ?d (hanoi:on)+ hanoi:PegC } }"""
#  THE PUBLISHED PLAN'S STEPS, each with the step after it and what it moves where, and what the plan
#  spent — read off the belief base, where a plan published is, by its kind.
_STEPS_Q = """PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT ?plan ?spent ?step ?next ?disk ?onto WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?plan a orexis:PlanGraph }
  GRAPH ?plan { ?plan planning:spent ?spent . ?step a execution:Step ; hanoi:disk ?disk ; hanoi:onto ?onto .
                OPTIONAL { ?step execution:then ?next } } }"""
#  WHAT THE WANT'S ESTIMATE READ AT THE PRESENT GROUND, in the imaginarium the search left.
_ESTIMATE_Q = """
SELECT ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:weighs ?g ; planning:remaining ?left .
               ?g a planning:GroundGraph } }"""
#  THE TEXTBOOK SOLUTION of three disks from peg A to peg C, the smallest disk first.
TEXTBOOK = [("disk_1", "PegC"), ("disk_2", "PegB"), ("disk_1", "PegB"), ("disk_3", "PegC"),
            ("disk_1", "PegA"), ("disk_2", "PegC"), ("disk_1", "PegC")]


def _home(store) -> int:
    return int(rows(store, _HOME_Q, ())[0]["n"])


def _plan(store) -> tuple[float, list[tuple[str, str]]]:
    """The one plan published: what it spent, and its moves as (disk, peg), walked from its head."""
    found = rows(store, _STEPS_Q, ())
    assert len({r["plan"] for r in found}) == 1, "one plan published"
    after = {r["step"]: r.get("next") for r in found}
    move = {r["step"]: (r["disk"].rsplit("#", 1)[-1], r["onto"].rsplit("#", 1)[-1]) for r in found}
    (head,) = set(after) - set(after.values())
    moves, step = [], head
    while step is not None:
        moves.append(move[step])
        step = after[step]
    return float(found[0]["spent"]), moves


def _ticking(monkeypatch) -> None:
    """One timeline that moves on a second at every read, as a running agent's does — a pass at the
    same instant as the last re-lays the present under the last one's name and a search cut short
    would start over."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))


def test_the_boot_says_what_each_graph_is():
    beliefs = boot(WORLD, "hanoi")
    assert len(graphs_of(beliefs, WANT)) == 1 and len(graphs_of(beliefs, STATE)) == 1
    assert _home(beliefs) == 0, "three disks on peg A"
    (scopes,) = rows(beliefs, "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?g { ?s a planning:Scope } }", ())
    assert int(scopes["n"]) >= 1, "scope_actions ran at boot"


def test_the_mover_loads_planning_and_nothing_else():
    """Declared a planner in its self graph, and nothing else (#928): no executor, since the plan is
    its output, and no deliberator, its world shipping no rules — so neither execution's ontology nor
    belief's, sensing's and its three rules, prediction's, speech's or the MQTT transport's is in the
    store, and the runtime makes planning's part alone. That no module of the others but a term
    module is imported is asked of a whole process, in agent/tests/test_roles.py."""
    import pyoxigraph as ox

    from agent.runtime import packages_of

    beliefs = boot(WORLD, "hanoi")
    assert packages_of(beliefs) == ("planning",)
    agent = WORLD.parents[1] / "agent"
    absent = [agent / "execution" / "ontology.ttl", agent / "belief" / "ontology.ttl",
              agent / "sensing" / "ontology.ttl", agent / "sensing" / "rules.ttl",
              agent / "prediction" / "ontology.ttl", agent / "speech" / "ontology.ttl",
              agent / "transport" / "mqtt" / "ontology.ttl"]
    present = [agent / "ontology.ttl", agent / "planning" / "ontology.ttl"]
    assert all(p.exists() for p in absent + present), "a document this test names has moved"
    held = {p: bool(list(beliefs.quads_for_pattern(ox.NamedNode(p.as_uri()), None, None))) for p in absent + present}
    assert not any(held[p] for p in absent), [p.name for p in absent if held[p]]
    assert all(held[p] for p in present), "the probe sees a document the mover does read"
    assert set(Runtime(beliefs, "hanoi").parts) == {"planning"}


def test_the_plan_is_the_seven_textbook_moves_at_a_cost_the_estimate_does_not_exceed(monkeypatch):
    """One pass at sixty-four candidates finds the plan and publishes it, and the runtime stops
    `planned`: seven moves, in the order the textbook gives, spending seven — and the want's estimate
    at the present ground, the disks astray, three, never more. Nothing walks it, so the tower is
    where it was posed, and a second run finds nothing to do and publishes nothing new."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=64)
    assert runtime.run(passes=20, poll_s=0) == PLANNED     # bounded: an ending lost reads `unfinished`, not a hang
    spent, moves = _plan(runtime.beliefs)
    assert moves == TEXTBOOK and spent == 7.0
    (im,) = runtime.parts["planning"].planner.imaginaria.values()
    (estimate,) = [float(r["left"]) for r in rows(im, _ESTIMATE_Q, ())]
    assert estimate == 3.0 and estimate <= spent, "an estimate never overstates what the plan cost"
    assert _home(runtime.beliefs) == 0, "a plan published moves no disk"
    published = graphs_of(runtime.beliefs, PLAN)
    assert runtime.run(passes=20, poll_s=0) == PLANNED and graphs_of(runtime.beliefs, PLAN) == published


def test_a_budget_that_cuts_the_search_short_is_finished_by_the_passes_after(monkeypatch):
    """Twenty candidates a pass: two passes hand nothing down, the third publishes the plan after ten
    more, and the passes together are the one-shot search — the same seven moves."""
    _ticking(monkeypatch)
    runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=20)
    heard = []
    runtime.parts["planning"].planner.searched.connect(heard.append)
    assert runtime.run(passes=12, poll_s=0) == PLANNED
    assert [(s.outcome, s.weighed) for s in heard] == [("Exhausted", 20), ("Exhausted", 20), ("Satisfied", 10)]
    assert _plan(runtime.beliefs) == (7.0, TEXTBOOK)


def test_a_window_a_pass_writes_the_planners_levels_and_the_runtimes_own_and_nothing_of_execution(monkeypatch):
    """The levels, each as it last stood in a window, and here a window a pass (#826, amended). The
    one package the mover's role loads says what it holds — the first pass's search cut short,
    `exhausted`, with the cone it left in the imaginarium: twenty worlds, twenty-one weighings, three
    still on the frontier; the runtime adds its own, the store's size and the uptime on its pass.
    Neither execution nor sensing nor belief is loaded, so no intention, no act, no silence and no
    revision is said: a package's metrics are where the package is. The executor's figures of a
    walked plan are the courier's (`world/courier/tests/`)."""
    windows = _metered(monkeypatch, interval_s=0)
    first = {p["measurement"]: p for p in windows[0]}
    assert {"pass", "planner", "imaginarium", "search", "reroot"} <= set(first), sorted(first)
    assert first["imaginarium"]["fields"] == {"worlds": 20, "weighings": 21, "open": 3, "met": 0,
                                              "satisfied": 0, "exhausted": 1, "no_candidate": 0}
    assert first["imaginarium"]["tags"]["scope"]
    every = {p["measurement"] for w in windows for p in w}
    assert not every & {"intentions", "intention", "act", "silence", "revisions"}, sorted(every)
    passes = [p["fields"] for w in windows for p in w if p["measurement"] == "pass"]
    assert len(passes) == 3 and all(p["count"] == 1 and p["duration_s_max"] > 0 for p in passes)
    assert all(0 < p["quads"] and p["uptime_s"] > 0 for p in passes)
    phases = [k for k in passes[0] if k.endswith("_s_sum") and k != "duration_s_sum"]
    assert phases and all(sum(p.get(k, 0) for k in phases) <= p["duration_s_sum"] for p in passes), \
        "the parts are of the pass"


def _metered(monkeypatch, *, interval_s: float):
    """Three disks at twenty candidates a pass, with a metrics sink loaded and who speaks said as
    `main` says it, the window `interval_s` long — nought writes one a pass, and anything longer
    than the run writes one at the end, as a stop does: every window written."""
    from agent.metrics import window as metrics
    from agent.runtime import world_name
    from agent.series import METRICS, Sink, install

    _ticking(monkeypatch)
    writes = []
    install(METRICS, Sink(METRICS, "hanoi-hanoi-metrics", lambda bucket, record: writes.append(list(record))))
    metrics.configure(interval_s=interval_s)
    metrics.identify(world=world_name(WORLD), agent="hanoi")
    try:
        runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=20)
        assert runtime.run(passes=12, poll_s=0) == PLANNED
        runtime.stop()                                   # as a stop does: the last window written
    finally:
        install(METRICS, None)
        metrics.reset()
        metrics.identify()
    return [w for w in writes if w]


def test_every_search_and_the_publishing_are_tallied_into_one_window_and_never_by_the_want(monkeypatch):
    """The events of the same run, in the one window a stop writes (#826, amended): two searches that
    each weighed their twenty candidates and gave up, and a third that found the seven moves, kept
    apart by how they ended; one plan published, after three passes of searching, whose plan cost what
    the estimate at the ground said or more; a reroot and a planner pass each pass. Every point is
    tagged with the world and the agent, and the want — minted per instance — is on none of them.
    Hanoi's want is authored, so no desire tags it."""
    (window,) = _metered(monkeypatch, interval_s=3600)
    by = {}
    for p in window:
        by.setdefault(p["measurement"], []).append(p)
    searches = {s["tags"]["outcome"]: s["fields"] for s in by["search"]}
    (published,) = by["published"]
    assert searches["Exhausted"]["count"] == 2 and searches["Exhausted"]["weighed_sum"] == 40.0
    assert searches["Satisfied"]["count"] == 1 and searches["Exhausted"]["budget_max"] == 20.0
    fields = published["fields"]
    assert fields["count"] == 1 and fields["passes_max"] == 3.0 and fields["replan"] == 0
    assert fields["cost_max"] == 7.0 and 0 <= fields["estimate_max"] <= fields["cost_max"]
    assert fields["wall_s_max"] >= sum(s["duration_s_sum"] for s in searches.values()) > 0
    (passed,) = by["pass"]
    assert passed["fields"]["count"] == 3
    assert sum(p["fields"]["count"] for p in by["reroot"]) == by["planner"][0]["fields"]["count"] == passed["fields"]["count"]
    assert "desire" not in published["tags"], "an authored want was derived under no desire"
    for p in window:                                       # the levels as well as the counts
        assert p["tags"]["world"] == "hanoi" and p["tags"]["agent"] == "hanoi", p
        assert "every_disk_home" not in {*p["tags"].values(), *map(str, p["fields"].values())}, p
        assert "want" not in p["tags"] and "want" not in p["fields"], p
    #  COST: a point per measurement and tag set a window, never one per weighing or per pass.
    assert len(window) < 20


def test_a_lived_in_volume_keeps_the_plan_and_does_not_search_again(monkeypatch):
    """A restart on the same volume: the plan published is the agent's own belief and stays, the
    want with it — published is not reached, so nothing withdrew it — and the run after the restart
    finds the want walked by the plan it already has, searches nothing and stops `planned` again."""
    _ticking(monkeypatch)
    beliefs = boot(WORLD, "hanoi")
    assert Runtime(beliefs, "hanoi", budget=64).run(passes=20, poll_s=0) == PLANNED
    published = graphs_of(beliefs, PLAN)
    boot(WORLD, "hanoi", beliefs)                     # a restart on the same volume
    assert graphs_of(beliefs, PLAN) == published and len(published) == 1, "the plan is the agent's, not the file's"
    assert len(graphs_of(beliefs, WANT)) == 1 and _home(beliefs) == 0
    runtime = Runtime(beliefs, "hanoi", budget=64)
    heard = []
    runtime.parts["planning"].planner.searched.connect(heard.append)
    assert runtime.run(passes=20, poll_s=0) == PLANNED
    assert heard == [], "the want is walked by the plan it has, and nothing searches it again"
    assert graphs_of(beliefs, PLAN) == published and _plan(beliefs) == (7.0, TEXTBOOK)
