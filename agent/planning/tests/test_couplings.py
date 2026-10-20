"""What a holder's constraints can make collide — tested where the read lives, on the courier's own
words: two vans and two parcels on one infinite grid.

The derivation's case (`derive_wants/two_parcels_a_constraint_joins_are_one_want.trig`) holds what the
derivation MINTS from the answer; what is held here is the answer itself. Since the grid is infinite a
drive writes a position its precondition computed, which is reachable anywhere, so the constraint over a
van's position couples everything before any reach is run (the-grid-is-infinite-and-a-position-is-two-
coordinates); the reach stays for worlds whose places are finite terms, and the finding the design stood
on — that a constraint read over the common beliefs alone, as a scope's atoms are, cannot tell a shared
grid from two — is kept as the reason the reach was the read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.ontology import BELIEF
from agent.planning import footprint
from agent.planning.couplings import REACH_GRAPH, couplings
from agent.planning.lay_ground import lay_ground
from agent.store import NAMESPACES, graph_names, graphs_of, rows

CASES = Path(__file__).parent / "derive_wants"
T = "http://example.org/test#"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
_GROUND_Q = "SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph } }"


def _present(store):
    (ground,) = [r["g"] for r in rows(store, _GROUND_Q, ())]
    return ground


@pytest.fixture
def laid(snapshots, monkeypatch):
    """A derivation case with its one ground laid, which is where the reach begins."""
    monkeypatch.setattr(clock, "now", lambda: NOW)

    def build(name: str):
        store = snapshots.stand_in(CASES / f"{name}.trig")
        lay_ground(store, NOW)
        return store
    return build


def test_a_drive_to_a_computed_position_couples_everything_and_runs_no_reach(laid):
    """A drive's effect writes the column and the row its precondition computed, so the reach would not
    close: the holder's constraints couple every instance, the safe side, and no working graph is made."""
    store = laid("two_parcels_a_constraint_joins_are_one_want")
    coupled = couplings(store, T + "keeper", _present(store), NOW)
    assert coupled is not None and coupled.anything
    assert coupled.joins(T + "parcel_a", T + "parcel_b") and coupled.joins(T + "parcel_b", T + "parcel_a")
    assert REACH_GRAPH not in graph_names(store), "no reach is run over a value reachable anywhere"


def test_a_holder_with_no_constraint_couples_nothing_and_pays_no_reach(laid):
    """A desire is no constraint, in either polarity: the two-parcels case that states none answers
    None before any reach is computed."""
    store = laid("two_parcels_two_estimates")
    assert couplings(store, T + "keeper", _present(store), NOW) is None


def test_over_the_beliefs_nobody_owns_alone_the_aversion_is_grid_blind(laid):
    """THE FINDING THE REACH STOOD ON. Asked the way a scope's atoms are — every pattern optional over
    the common beliefs — the aversion joins van A to van B with the position unbound, since where a van
    can stand is the drive's arithmetic and the half of a text the world answers is its patterns. So a
    constraint's footprint was read over the reach, and is read as everything where the reach cannot close."""
    select = """PREFIX courier: <http://example.org/orexis/courier#>
        SELECT $this ?value WHERE { $this a courier:Van ; courier:x ?x ; courier:y ?y . ?value a courier:Van ; courier:x ?x ; courier:y ?y . FILTER(?value != $this) }"""
    patterns = footprint._patterns(select)
    text = "SELECT DISTINCT * WHERE { " + " ".join(
        f"OPTIONAL {{ {footprint._n3(s)} {footprint._n3(p)} {footprint._n3(o)} . }}" for s, p, o in patterns) + " }"
    store = laid("two_parcels_a_constraint_joins_are_one_want")
    found = store.query(text, prefixes=NAMESPACES, default_graph=[ox.NamedNode(g) for g in graphs_of(store, BELIEF, common=True)])
    seen = sorted((str(s["this"].value), str(s["value"].value), s["x"], s["y"]) for s in found if s["this"] and s["value"])
    assert len(seen) == 4 and all(x is None and y is None for *_, x, y in seen), seen
