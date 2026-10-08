"""The runtime runs until nothing is left to pursue: an agent holding only wants stops when each
is reached, and one holding a desire never does, since a desire asks at every instant."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.runtime import UNFINISHED, Runtime, boot

ROOT = Path(__file__).resolve().parents[2]
HANOI = ROOT / "world" / "hanoi"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _as_a_desire(tmp_path: Path) -> Path:
    """Hanoi's world with its want authored as a DESIRE — the same met-test, held for ever."""
    world = tmp_path / "hanoi_desired"
    world.mkdir()
    domain = (ROOT / "domains" / "hanoi" / "ontology.ttl").as_uri()
    (world / "world.ttl").write_text((HANOI / "world.ttl").read_text().replace("<../../domains/hanoi/ontology.ttl>", f"<{domain}>"))
    (world / "state.ttl").write_text((HANOI / "state.ttl").read_text())
    (world / "desires.ttl").write_text((HANOI / "wants.ttl").read_text()
                                       .replace("planning:WantGraph", "planning:DesireGraph").replace("a planning:Want ;", "a planning:Desire ;"))
    (world / "beliefs").mkdir()
    (world / "beliefs" / "hanoi.self.ttl").write_text((HANOI / "beliefs" / "hanoi.self.ttl").read_text())
    return world


def test_an_agent_holding_a_desire_keeps_running_once_it_is_met(tmp_path, monkeypatch):
    """The tower is solved, the want the desire minted is withdrawn — and the runtime does not
    exit: a desire is universal, so the agent waits for the world to move."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(_as_a_desire(tmp_path), "hanoi"), "hanoi", budget=64)
    assert runtime.run(passes=6, poll_s=0) == UNFINISHED
    assert runtime.parts["planning"].planner.standing() == [] and runtime.parts["execution"].executor.walking() == [], "met, and waiting"


def test_a_graph_of_a_kind_the_agent_does_not_declare_is_passed_over(tmp_path):
    """A kind says who reads a document, and the agent reads only the kinds its vocabulary puts
    beneath `orexis:Graph`: a document of another reader's kind — or of a kind misspelled — puts
    neither its quads nor a row about it into the store, where it once went in as the agent's own."""
    import pyoxigraph as ox

    world = _as_a_desire(tmp_path)
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
