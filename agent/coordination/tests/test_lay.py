"""`lay`: what an agent lays of a peer's holdings as forecasts of the peer's thing — at each instant everything
the peer may hold; all of it while the draw stands undecided or lost, the step in flight alone once won, and
none the agent's own constraints refuse beside what it believes now."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox

from agent.coordination.holdings import Holding, holdings
from agent.coordination.lay import _refused, _timeline, lay
from agent.coordination.ontology import laid_root
from agent.store import PREFIXES

L = "http://example.org/orexis/world/lane#"
A, B, VAN_A, VAN_B = L + "courier_a", L + "courier_b", L + "van_a", L + "van_b"
TWO_VANS = "http://example.org/orexis/courier#no_two_vans_at_one_position"

X = "http://example.org/orexis/courier#x"
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
_INT = ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer")


def _x(n: int):
    return (X, ox.Literal(str(n), datatype=_INT))


def _s(seconds: int) -> datetime:
    return T0 + timedelta(seconds=seconds)


def test_between_its_earliest_landing_and_its_latest_a_step_holds_both_its_cells():
    held = [Holding(VAN_B, (_x(1),), None, _s(60)), Holding(VAN_B, (_x(2),), _s(30), _s(120)),
            Holding(VAN_B, (_x(3),), _s(90), None)]
    assert _timeline(held) == [Holding(VAN_B, (_x(1), _x(2)), _s(30), _s(60)), Holding(VAN_B, (_x(2),), _s(60), _s(90)),
                               Holding(VAN_B, (_x(2), _x(3)), _s(90), _s(120)), Holding(VAN_B, (_x(3),), _s(120), None)]
    assert _timeline(held[:1]) == [], "before the first change, the peer is what sensing says"


def _laid(store, me) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for r in store.query(PREFIXES + f'SELECT DISTINCT ?g ?s WHERE {{ GRAPH ?g {{ ?s ?p ?o }} FILTER(STRSTARTS(STR(?g), "{laid_root(me)}")) }}'):
        out.setdefault(r["g"].value, set()).add(r["s"].value)
    return out


def test_the_loser_lays_the_winners_holdings_and_the_winner_the_losers_step_in_flight_alone(meeting, copied):
    loser, winner = _laid(meeting.store(A), A), _laid(meeting.store(B), B)
    assert loser and all(things == {VAN_B} for things in loser.values()), loser
    assert all(things == {VAN_A} for things in winner.values()), winner
    assert len(winner) <= 2 and len(winner) <= len(loser), "the step in flight's band and what it lands at, no more"
    assert lay(copied(meeting.store(A)), A, meeting.at) == [], "and laid again unchanged, nothing is written"


def test_a_holding_the_agents_own_constraints_refuse_is_not_laid(meeting):
    """B laid on A's own cell would stand two vans at one position in every ground from then on, so every
    world of A's would be impossible: refused. Three cells west of it is laid."""
    store = meeting.store(A)
    mine = holdings(store, TWO_VANS, meeting.at)[0]
    on_me = Holding(VAN_B, mine.values, meeting.at + timedelta(seconds=30), None)
    assert _refused(store, on_me, meeting.at)
    off = Holding(VAN_B, tuple((p, ox.Literal(str(int(v.value) - 3), datatype=_INT)) if p == X else (p, v) for p, v in mine.values),
                  meeting.at + timedelta(seconds=30), None)
    assert not _refused(store, off, meeting.at)

