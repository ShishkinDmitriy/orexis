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
                                       .replace("orexis:WantGraph", "orexis:DesireGraph").replace("a orexis:Want ;", "a orexis:Desire ;"))
    return world


def test_an_agent_holding_a_desire_keeps_running_once_it_is_met(tmp_path, monkeypatch):
    """The tower is solved, the want the desire minted is withdrawn — and the runtime does not
    exit: a desire is universal, so the agent waits for the world to move."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(_as_a_desire(tmp_path), "hanoi"), "hanoi", budget=64)
    assert runtime.run(passes=6, poll_s=0) == UNFINISHED
    assert runtime.planner.standing() == [] and runtime.executor.walking() == [], "met, and waiting"


def test_an_agent_reads_its_own_beliefs_file_and_no_other_agents(tmp_path):
    """A world of several agents states each one's desires under `beliefs/<id>`: the boot reads the
    world's own files and the agent's, never a peer's."""
    from agent.runtime import documents
    (tmp_path / "world.ttl").write_text("")
    (tmp_path / "beliefs").mkdir()
    for name in ("rose.ttl", "fern.ttl", "rose.txt"):
        (tmp_path / "beliefs" / name).write_text("")
    read = [p.relative_to(tmp_path).as_posix() for p in documents(tmp_path, "rose") if tmp_path in p.parents]
    assert read == ["world.ttl", "beliefs/rose.ttl"]
    assert [p for p in documents(tmp_path) if tmp_path in p.parents] == [tmp_path / "world.ttl"], \
        "what the world says to nobody in particular — the operator's tools — is its own files alone"
