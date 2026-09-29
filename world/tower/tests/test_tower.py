"""The tower: hanoi's puzzle on the courier's grid, planned one level inside the other.

The world combines two domains and one rule set saying what a disk is on from where it stands.
The mover plans hanoi's Moves; each Move, when its turn comes, is refined into a want the
courier's actions reach — nothing declares the hierarchy, the rules are where it is found
(knowledge/domain/planning/refinement.md). The gate runs it on TWO disks, the world's third taken out of
the booted beliefs, since three cost two and a half minutes on the Pi; the world as authored is
the three-disk demonstration.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.ontology import STATE
from agent.runtime import MET, Runtime, boot
from agent.store import forget_graph, graphs_of, revisions_of, rows, update

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
TOWER = "http://example.org/orexis/world/tower#"

_ON_Q = """PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT ?d ?below WHERE { GRAPH ?g { ?d hanoi:on ?below } } ORDER BY ?d"""
_AT_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?x ?cell WHERE { GRAPH ?g { ?x courier:at ?cell } } ORDER BY ?x"""
_REFINED_Q = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a execution:refinedBy ?w } }"


def _local(iri: str) -> str:
    return iri.rsplit("#", 1)[-1]


def _two_disks(beliefs) -> None:
    """The world less its large disk, and the conclusions drawn of the three taken back, so the
    runtime revises the state again at its start."""
    update(beliefs, f"DELETE WHERE {{ GRAPH ?g {{ <{TOWER}disk_3> ?p ?o }} }}")
    for graph in revisions_of(beliefs, *graphs_of(beliefs, STATE)):
        forget_graph(beliefs, graph)


def test_the_runtime_concludes_what_each_disk_is_on_from_where_it_stands(monkeypatch):
    """At its start, before any pass: the state is revised by the tower's rules, so the puzzle's
    words stand beside the grid's without either domain's file stating them."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    runtime = Runtime(boot(WORLD, "mover"), "mover")
    on = {(_local(r["d"]), _local(r["below"])) for r in rows(runtime.beliefs, _ON_Q, ())}
    assert on == {("disk_1", "disk_2"), ("disk_2", "disk_3"), ("disk_3", "PegA")}


def test_the_puzzle_is_planned_above_and_carried_out_by_the_van_below(monkeypatch):
    ticks = iter(range(1, 100_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    beliefs = boot(WORLD, "mover")
    _two_disks(beliefs)
    runtime = Runtime(beliefs, "mover", budget=256)
    assert runtime.run(passes=30, poll_s=0) == MET
    at = {_local(r["x"]): _local(r["cell"]) for r in rows(runtime.beliefs, _AT_Q, ())
          if r["x"].startswith(TOWER)}
    assert at["disk_1"] == at["disk_2"] == "c1_2", "both disks on peg C's cell"
    on = {(_local(r["d"]), _local(r["below"])) for r in rows(runtime.beliefs, _ON_Q, ())}
    assert on == {("disk_1", "disk_2"), ("disk_2", "PegC")}, "and stacked in order"
    refined = int(rows(runtime.started["execution"].intentions, _REFINED_Q, ())[0]["n"])
    assert refined == 3, "each of the three moves was kept below, and none was taken as fictive"
