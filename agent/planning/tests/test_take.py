"""`take`, one case per file, held to a PATCH of the store it leaves.

A case in `take/` is an imaginarium whose ground has been admitted: the candidates stand as
edges from it and no world has been forked. The test takes every candidate that has reached no
world, in the order they were minted, and `<case>.diff` is what that made: one world per
candidate, forked with the action's effect applied, and its row — what it spent, when it is,
its mint number (the candidate's, which names it), its hash, and the candidate that made it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import clock
from agent.store import Memo, graphs_of, quads, rows
from agent.planning.admit import admit
from agent.planning.ontology import POSSIBLE_GRAPH
from agent.planning.take import take

CASES_DIR = Path(__file__).parent / "take"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

_UNTAKEN_Q = """
SELECT ?cand WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?cand a planning:Candidate ; planning:minted ?m .
               FILTER NOT EXISTS { ?w planning:by ?cand } } }
ORDER BY ?m"""

#  EVERY CANDIDATE AND THE WORLD IT MADE, with what each is called and numbered.
_EDGES_Q = """
SELECT ?cand ?m ?w ?wm WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?cand a planning:Candidate ; planning:minted ?m .
               OPTIONAL { ?w planning:by ?cand ; planning:minted ?wm } } }
ORDER BY ?m"""

_PRESENT_Q = """
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph } } LIMIT 1"""


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_take_forks_the_worlds_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    taken = [take(store, r["cand"], snapshots.ME) for r in rows(store, _UNTAKEN_Q, ())]
    assert taken, f"{case.name} admits no candidate to take"
    snapshots.held_to_diff(case, request, "take", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 2, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)


ADMIT_CASES = Path(__file__).parent / "admit"


def test_siblings_differing_in_one_value_never_share_a_graph(monkeypatch, snapshots):
    """The property a world's name used to carry and once failed to carry (#486): one action
    filled two ways — the one lever, each of two tanks — is two candidates, and taking both
    makes two worlds in two graphs, each holding its own tank's level. The names are mint
    numbers now, the world's its candidate's, and what tells the siblings apart is that nothing
    in the store is shared between them."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(ADMIT_CASES / "one_lever_two_tanks.trig")
    (present,) = rows(store, _PRESENT_Q, ())
    admit(store, present["g"], snapshots.ME)
    for r in rows(store, _UNTAKEN_Q, ()):
        assert take(store, r["cand"], snapshots.ME)
    edges = rows(store, _EDGES_Q, ())
    assert len(edges) == 2 and all(e.get("w") for e in edges), edges
    worlds = [e["w"] for e in edges]
    assert len(set(worlds)) == 2 and set(worlds) == set(graphs_of(store, POSSIBLE_GRAPH))
    assert [e["m"] for e in edges] == [e["wm"] for e in edges], "a world carries its candidate's number"
    held = [frozenset(str(q) for q in quads(store, w)) for w in worlds]
    assert held[0] and held[1] and held[0] != held[1], "two fillings, two worlds, each its own facts"


def test_a_second_pass_over_one_store_mints_above_everything_it_holds(monkeypatch, snapshots):
    """The counter is the store's: a pass reads the highest number any candidate or world carries
    and mints above it, so a world kept across passes — the cone `reroot` hands to the ground —
    is never named again. Two memos stand for two passes: the second admits a world the first
    made, and the candidates it writes and the worlds they make carry numbers above every one
    the first wrote, under names nothing had."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(ADMIT_CASES / "one_lever_two_tanks.trig")
    (present,) = rows(store, _PRESENT_Q, ())
    first = Memo()
    admit(store, present["g"], snapshots.ME, memo=first)
    for r in rows(store, _UNTAKEN_Q, ()):
        take(store, r["cand"], snapshots.ME, memo=first)
    before = rows(store, _EDGES_Q, ())
    names = {e["cand"] for e in before} | {e["w"] for e in before}
    second = Memo()
    admit(store, before[0]["w"], snapshots.ME, memo=second)
    for r in rows(store, _UNTAKEN_Q, ()):
        take(store, r["cand"], snapshots.ME, memo=second)
    after = rows(store, _EDGES_Q, ())
    new = [e for e in after if e["cand"] not in names]
    assert new and all(e.get("w") for e in new), "the world the first pass made admits the lever again"
    assert min(int(e["m"]) for e in new) > max(int(e["m"]) for e in before)
    assert len({e["cand"] for e in after} | {e["w"] for e in after}) == 2 * len(after), \
        "every candidate and every world under a name of its own"
