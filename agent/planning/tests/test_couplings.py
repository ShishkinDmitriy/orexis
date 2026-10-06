"""What a holder's constraints can make collide, read over the reach from the present — tested where
the read lives, on the courier's own words: two vans and two parcels on one grid, and on two.

The derivation's cases (`derive_wants/two_parcels_a_constraint_joins_are_one_want.trig` and
`two_parcels_on_disjoint_grids_are_two_wants.trig`) hold what the derivation MINTS from the answer;
what is held here is the answer itself, and the one finding the design stands on: that a constraint
read over the public graphs alone, as a scope's atoms are, cannot tell a shared grid from two.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.ontology import PUBLIC
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


def test_two_parcels_whose_vans_share_a_grid_are_joined_and_nothing_else_is_left_behind(laid):
    """The aversion over the reach yields a row per cell both vans can reach, so the vans and the
    cells are one part; each parcel is bound with both vans by the pick the reach admits; the two
    parcels are joined. The reach's working graph is gone when the answer is given."""
    store = laid("two_parcels_a_constraint_joins_are_one_want")
    coupled = couplings(store, T + "keeper", _present(store), NOW)
    assert coupled is not None and not coupled.anything
    assert len(coupled.parts) == 1 and {T + "van_a", T + "van_b"} <= coupled.parts[0], coupled.parts
    assert {T + "van_a", T + "van_b"} <= coupled.bound[T + "parcel_a"], "either van can pick parcel A"
    assert coupled.joins(T + "parcel_a", T + "parcel_b") and coupled.joins(T + "parcel_b", T + "parcel_a")
    assert REACH_GRAPH not in graph_names(store), "the reach is a working graph taken away before the answer"


def test_two_parcels_on_disjoint_grids_are_not_joined(laid):
    """No cell both vans can reach, so the aversion yields no row over the reach and nothing is
    joined; each parcel is bound with its own van alone."""
    store = laid("two_parcels_on_disjoint_grids_are_two_wants")
    coupled = couplings(store, T + "keeper", _present(store), NOW)
    assert coupled is not None and coupled.parts == []
    assert coupled.bound[T + "parcel_a"] & {T + "van_a", T + "van_b"} == {T + "van_a"}
    assert coupled.bound[T + "parcel_b"] & {T + "van_a", T + "van_b"} == {T + "van_b"}
    assert not coupled.joins(T + "parcel_a", T + "parcel_b")


def test_a_holder_with_no_constraint_couples_nothing_and_pays_no_reach(laid):
    """A desire is no constraint, in either polarity: the two-parcels case that states none answers
    None before any reach is computed."""
    store = laid("two_parcels_two_estimates")
    assert couplings(store, T + "keeper", _present(store), NOW) is None


def test_over_the_public_graphs_alone_the_aversion_is_grid_blind(laid):
    """THE FINDING THE DESIGN STANDS ON. Asked the way a scope's atoms are — every pattern optional
    over the public graphs — the aversion joins van A to van B with the cell unbound, on one grid
    and on two alike, since which cells a van can stand on is the drive's FILTER over coordinates
    and the public half of a text is its patterns. So the constraint is read over the reach."""
    select = """PREFIX courier: <http://example.org/orexis/courier#>
        SELECT $this ?value WHERE { $this a courier:Van ; courier:at ?value . ?other a courier:Van ; courier:at ?value . FILTER(?other != $this) }"""
    patterns = footprint._patterns(select)
    text = "SELECT DISTINCT * WHERE { " + " ".join(
        f"OPTIONAL {{ {footprint._n3(s)} {footprint._n3(p)} {footprint._n3(o)} . }}" for s, p, o in patterns) + " }"
    seen = []
    for name in ("two_parcels_a_constraint_joins_are_one_want", "two_parcels_on_disjoint_grids_are_two_wants"):
        store = laid(name)
        found = store.query(text, prefixes=NAMESPACES, default_graph=[ox.NamedNode(g) for g in graphs_of(store, PUBLIC)])
        seen.append(sorted((str(s["this"].value), str(s["other"].value), s["value"]) for s in found if s["this"] and s["other"]))
    assert seen[0] == seen[1] and len(seen[0]) == 4 and all(value is None for *_, value in seen[0]), seen
