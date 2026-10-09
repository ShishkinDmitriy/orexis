"""The runtime runs until nothing is left to pursue: an agent holding only wants stops when each
is reached — or, where it walks no plan, when each has a plan published — and one holding a desire
never does, since a desire asks at every instant."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.runtime import MET, PLANNED, UNFINISHED, Runtime, boot
from agent.store import graphs_of

ROOT = Path(__file__).resolve().parents[2]
HANOI = ROOT / "world" / "hanoi"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
EXECUTOR = "http://example.org/orexis/execution#Executor"
PLAN = "http://example.org/orexis#PlanGraph"


def _hanoi(tmp_path: Path, *, desired: bool = False, walks: bool = False) -> Path:
    """Hanoi's world, its mover a planner as shipped — and, `walks`, an executor beside, so the same
    plan is walked to a solved tower; `desired`, its want authored as a DESIRE, the same met-test held
    for ever."""
    world = tmp_path / "hanoi"
    world.mkdir()
    domain = (ROOT / "domains" / "hanoi" / "ontology.ttl").as_uri()
    (world / "world.ttl").write_text((HANOI / "world.ttl").read_text().replace("<../../domains/hanoi/ontology.ttl>", f"<{domain}>"))
    (world / "state.ttl").write_text((HANOI / "state.ttl").read_text())
    wants = (HANOI / "wants.ttl").read_text()
    if desired:
        (world / "desires.ttl").write_text(wants.replace("planning:WantGraph", "planning:DesireGraph")
                                           .replace("a planning:Want ;", "a planning:Desire ;"))
    else:
        (world / "wants.ttl").write_text(wants)
    self_graph = (HANOI / "beliefs" / "hanoi.self.ttl").read_text()
    assert ":hanoi a orexis:Self , planning:Planner ." in self_graph, "the shipped mover is a planner alone"
    (world / "beliefs").mkdir()
    (world / "beliefs" / "hanoi.self.ttl").write_text(
        self_graph.replace(":hanoi a orexis:Self , planning:Planner .", f":hanoi a orexis:Self , planning:Planner , <{EXECUTOR}> .")
        if walks else self_graph)
    return world


def _ticking(monkeypatch) -> None:
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))


@pytest.mark.parametrize("walks, ending", [(False, PLANNED), (True, MET)], ids=["a planner alone", "a planner and an executor"])
def test_an_agent_holding_wants_alone_ends_planned_where_nothing_walks_its_plan_and_met_where_something_does(
        tmp_path, monkeypatch, walks, ending):
    """THE ENDING IS THE ROLES' (#928). One world, one want, one plan of seven moves: declared a
    planner alone, the mover publishes it and lets go `planned`, the tower as posed; declared an
    executor too, the same plan is adopted and walked, and the mover lets go `met` — never `planned`,
    since the plan published is walked by something and the want stands until it is reached."""
    _ticking(monkeypatch)
    runtime = Runtime(boot(_hanoi(tmp_path, walks=walks), "hanoi"), "hanoi", budget=64)
    assert runtime.run(passes=20, poll_s=0) == ending
    assert ("execution" in runtime.parts) is walks
    planner = runtime.parts["planning"].planner
    if walks:
        assert planner.standing() == [] and planner.walking() == set(), "reached, and nothing walked"
    else:
        assert len(graphs_of(runtime.beliefs, PLAN)) == 1 and set(planner.standing()) == planner.walking(), \
            "the want stands, walked by the one plan published"


def test_the_process_exits_nought_on_planned_as_on_met(monkeypatch):
    """`planned` is the mover doing all it was declared for, so its container exits as one that met
    its wants does, at the budget its stance sets."""
    import signal

    from agent import runtime as runtime_module

    _ticking(monkeypatch)
    monkeypatch.setattr(runtime_module.series, "load", lambda: ())     # no series, whatever the environment says
    before = signal.getsignal(signal.SIGTERM)
    try:
        assert runtime_module.main([str(HANOI), "hanoi", "--passes", "20"]) == 0
    finally:
        signal.signal(signal.SIGTERM, before)


@pytest.mark.parametrize("walks", [False, True], ids=["a planner alone", "a planner and an executor"])
def test_an_agent_holding_a_desire_keeps_running(tmp_path, monkeypatch, walks):
    """A desire is universal, so it holds the agent whatever its roles. Walked, the tower is solved and
    the want the desire minted withdrawn, and the runtime waits for the world to move; planned alone,
    the plan is published and nothing walks it, and the runtime still does not let go `planned`."""
    _ticking(monkeypatch)
    runtime = Runtime(boot(_hanoi(tmp_path, desired=True, walks=walks), "hanoi"), "hanoi", budget=64)
    assert runtime.run(passes=6, poll_s=0) == UNFINISHED
    planner = runtime.parts["planning"].planner
    if walks:
        assert planner.standing() == [] and runtime.parts["execution"].executor.walking() == [], "met, and waiting"
    else:
        assert planner.standing() and set(planner.standing()) <= planner.walking(), "planned, and waiting"


def test_a_graph_of_a_kind_the_agent_does_not_declare_is_passed_over(tmp_path):
    """A kind says who reads a document, and the agent reads only the kinds its vocabulary puts
    beneath `orexis:Graph`: a document of another reader's kind — or of a kind misspelled — puts
    neither its quads nor a row about it into the store, where it once went in as the agent's own."""
    import pyoxigraph as ox

    world = _hanoi(tmp_path, desired=True)
    (world / "elsewhere.ttl").write_text("<> a <http://example.org/elsewhere#SomeoneElsesGraph> .\n"
                                         "<http://example.org/elsewhere#pin> <http://example.org/elsewhere#gpio> 34 .\n")
    store = boot(world, "hanoi")
    name = ox.NamedNode((world / "elsewhere.ttl").resolve().as_uri())
    assert list(store.quads_for_pattern(None, None, None, name)) == []
    assert list(store.quads_for_pattern(name, None, None)) == [], "no row says the graph exists"
    assert list(store.quads_for_pattern(None, None, None, ox.NamedNode((world / "state.ttl").resolve().as_uri()))), \
        "a graph of a kind it does declare is read beside it"


def test_the_boot_reads_every_document_of_the_world_and_asks_none_by_its_name(tmp_path):
    """Every document beside the world, under `secrets/` and under `beliefs/` is read, whatever it is
    called and whoever it is for: whose a graph is, is what it says (agent/tests/test_self.py), so
    no reader picks a file by an agent's id."""
    from agent.runtime import documents
    (tmp_path / "world.ttl").write_text("")
    (tmp_path / "beliefs").mkdir()
    (tmp_path / "secrets").mkdir()
    for name in ("beliefs/rose.ttl", "beliefs/fern.trig", "beliefs/rose.txt", "secrets/place.ttl"):
        (tmp_path / name).write_text("")
    read = [p.relative_to(tmp_path).as_posix() for p in documents(tmp_path) if tmp_path in p.parents]
    assert read == ["world.ttl", "secrets/place.ttl", "beliefs/fern.trig", "beliefs/rose.ttl"]
