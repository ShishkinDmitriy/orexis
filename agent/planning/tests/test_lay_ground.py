"""`lay_ground`, one case per file, held to a PATCH of the store it lays the grounds INTO.

The same belief bases `prepare_ground/` fills a second store from, laid in place: the present
as a ground of its own, and one more per boundary a prediction makes, each forked from the one
before with the prediction's retraction run and its facts added, classified with the stretch
it holds over and hashed — and a boundary whose ground hashes like the one before it laid as
no ground at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pyoxigraph as ox

from agent import clock
from agent.planning.lay_ground import lay_ground
from agent.store import add_quads, catalogue_of, rows

CASES_DIR = Path(__file__).parent / "lay_ground"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_lay_ground_lays_the_grounds_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    lay_ground(store, snapshots.NOW)
    snapshots.held_to_diff(case, request, "lay_ground", snapshots.snapshot_of(store))


def test_a_period_is_told_by_the_whole_ground_and_its_hash_is_taken_within_what_is_read(monkeypatch, snapshots):
    """The level drops at half past and the temperature rises at one: three grounds. Laid where
    the level alone is read they are three grounds still — a boundary is a period by everything
    the ground holds — and the last two carry ONE hash, since the temperature is not where a
    world stands there. Folding them by what is read was built and struck: a want
    minted for a foreseen crossing came to be weighed in the present and its intention ended
    before its step was due (#858, `lay_ground`)."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    case = CASES_DIR / "two_stretches_in_one_scope_are_two_grounds.trig"
    store = snapshots.stand_in(case)
    grounds = lay_ground(store, snapshots.NOW, frozenset({"http://example.org/test#level"}))
    assert len(grounds) == 3
    hashes = [rows(store, "SELECT ?h WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . "
                          f"<{g}> orexis:hash ?h }} }}")[0]["h"] for g in grounds]
    assert hashes[0] != hashes[1], "the level dropped, which is read"
    assert hashes[1] == hashes[2], "the temperature rose, which is not"


_T = "http://example.org/test#"
_OPENING = f"""
PREFIX : <{_T}>
PREFIX orexis: <http://example.org/orexis#>
PREFIX planning: <http://example.org/orexis/planning#>
PREFIX belief: <http://example.org/orexis/belief#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
INSERT DATA {{ GRAPH :actions {{
  :open a orexis:Action ; orexis:takes :tank ;
    planning:effect [ a planning:Effect ; sh:rule [ a belief:Transition ; belief:update \"\"\"PREFIX : <{_T}>
      DELETE {{ $tank :lid :closed }} INSERT {{ ?tank :lid :open }} WHERE {{ $tank :lid :closed . BIND($tank AS ?tank) }}\"\"\" ] ] .
}} }}"""


def _held(store) -> dict[str, frozenset]:
    """What every graph but the catalogue holds, by name: the content, since a row is metadata."""
    cat = catalogue_of(store)
    out: dict[str, set] = {}
    for q in store.quads_for_pattern(None, None, None, None):
        if q.graph_name != ox.NamedNode(cat):
            out.setdefault(q.graph_name.value, set()).add(ox.Triple(q.subject, q.predicate, q.object))
    return {g: frozenset(t) for g, t in out.items()}


def test_an_action_added_makes_what_it_writes_changeable_and_nothing_else(monkeypatch, snapshots):
    """The world says a tank's lid is closed, and no action writes a lid: it is read beside every world
    and no ground holds it. An action that opens a lid is added and the grounds are laid again in the
    same store: the lid moves out of the world into the world's changeable graph and into the ground, and
    every other graph holds what it held — the cut is what the writers say, and the cut standing from the
    first laying is taken back and made again because the patterns changed (#953)."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(Path(__file__).parent / "plans" / "a_low_tank_is_filled.trig")
    world, lid = _T + "world", ox.Triple(ox.NamedNode(_T + "tank1"), ox.NamedNode(_T + "lid"), ox.NamedNode(_T + "closed"))
    add_quads(store, [ox.Quad(lid.subject, lid.predicate, lid.object, ox.NamedNode(world))])
    (ground,) = lay_ground(store, snapshots.NOW)
    before = _held(store)
    assert lid in before[world] and lid not in before[ground], "no writer writes a lid"

    store.update(_OPENING)
    assert lay_ground(store, snapshots.NOW) == [ground]
    after = _held(store)

    piece = world + ".changeable"
    assert piece not in before and after[piece] == {lid}, "the lid is cut into the world's changeable graph"
    assert after[world] == before[world] - {lid}, "and out of the world"
    assert after[ground] == before[ground] | {lid}, "and the present is laid with it"
    actions = _T + "actions"
    assert after[actions] > before[actions], "the action was added"
    untouched = set(before) - {world, ground, actions}
    assert untouched and set(after) - {piece} == set(before)
    assert {g: after[g] for g in untouched} == {g: before[g] for g in untouched}, "nothing else changed"


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
