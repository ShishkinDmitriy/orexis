"""`weigh`, one case per file, held to a PATCH of the store it leaves.

A case in `weigh/` is an imaginarium with something still to be weighed. The test weighs
whatever `unweighed` lists — every desire in every ground, every want in the present, every
candidate leaving a world its want has weighed — which is what a pass would weigh next.
`<case>.diff` is the weighings: the verdict, the violation rows, whether the world is on the
frontier, and for a candidate passed over, which world it repeats.
"""

from __future__ import annotations

import json

from pathlib import Path

import pytest

from agent import clock
from agent.planning.unweighed import unweighed
from agent.planning.weigh import weigh
from agent.store import rows

CASES_DIR = Path(__file__).parent / "weigh"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

#  THE FILTERS STAND AT THE TOP OF THE WHERE, not inside the catalogue's group: a FILTER
#  inside a group cannot see a variable bound outside it, so inside `GRAPH ?cat` the `?for`
#  the union bound was unbound, NOT EXISTS matched any weighing at all, and a store holding
#  one had nothing left to weigh. The trap AGENTS.md records for UNION and BIND, met here.
@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_weigh_writes_the_weighings_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    weighed = [weigh(store, pair["for"], pair["about"]) for pair in unweighed(store)]
    assert weighed, f"{case.name} has nothing left to weigh"
    snapshots.held_to_diff(case, request, "weigh", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 3, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)


# --- the estimate --------------------------------------------------------------------------

BENCH = Path(__file__).parent / "bench"

_REMAINING_Q = """
SELECT ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?x a planning:Weighing ; planning:for $want ; planning:weighs ?g ; planning:remaining ?left .
               ?g a planning:GroundGraph } }"""


def _weighed_in_the_ground(snapshots, text: str | None = None):
    """Two-disk hanoi with its want weighed in the present ground; `text` replaces the
    estimate's select where given. The want, and the store."""
    from agent.planning.derive_wants import derive_wants
    from agent.planning.find_wants import find_wants
    from agent.planning.lay_ground import lay_ground
    from agent.planning.prepare_ground import prepare_ground
    import pyoxigraph as ox
    beliefs = snapshots.stand_in(BENCH / "two_disk_hanoi.trig")
    if text is not None:
        beliefs.update(f"""DELETE {{ GRAPH ?g {{ ?n <http://www.w3.org/ns/shacl#select> ?old }} }}
                           INSERT {{ GRAPH ?g {{ ?n <http://www.w3.org/ns/shacl#select> {json.dumps(text)} }} }}
                           WHERE  {{ GRAPH ?g {{ ?d <http://example.org/orexis/planning#estimates> ?n . ?n <http://www.w3.org/ns/shacl#select> ?old }} }}""")
    store = prepare_ground(beliefs, ox.Store())
    lay_ground(store, snapshots.NOW)
    for pair in unweighed(store):
        weigh(store, pair["for"], pair["about"])
    derive_wants(store, snapshots.NOW)
    (want,) = find_wants(store, snapshots.NOW)
    for pair in unweighed(store, for_=want):
        weigh(store, want, pair["about"])
    return want, store


def test_a_wants_weighing_carries_what_its_desires_estimate_reads_there(monkeypatch, snapshots):
    """The desire owns the term: `planning:estimates` on the desire the want was derived from
    points at the package's select, and the weighing of the want in the ground says what it
    read — two disks astray, two moves at least."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    want, store = _weighed_in_the_ground(snapshots)
    (found,) = rows(store, _REMAINING_Q, (), want=want)
    assert float(found["left"]) == 2.0


def test_an_estimate_that_will_not_run_writes_no_remaining(monkeypatch, snapshots):
    """None is not nought: a broken declaration read as arrived would crown a plan that
    achieved nothing, so the weighing carries no figure and the frontier reads uniform-cost."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    want, store = _weighed_in_the_ground(snapshots, text="SELECT ?estimate WHERE { ?x }")
    assert rows(store, _REMAINING_Q, (), want=want) == []
