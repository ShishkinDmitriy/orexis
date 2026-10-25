"""What coordination says happened, as history points: the holdings it asked with, laid as said or foreseen, and its
conflicts — each a set said whole, replacing the one before (`agent/coordination/events.py`)."""

from __future__ import annotations

from pathlib import Path

from agent.conftest import ME, NOW
from agent.coordination.conclude import _conflicts
from agent.coordination.events import FORESEEN, Concluded, Conflict, Held
from agent.coordination.lay import _laid, lay

LAY = Path(__file__).parent / "lay"
_PEER, _NO_TWO_VANS = "http://example.org/test#peer", "http://example.org/test#no_two_vans"


def test_what_a_silent_peer_is_foreseen_at_is_said_as_a_point_per_place_and_one_saying_how_many(snapshots):
    store = snapshots.stand_in(LAY / "silent_and_never_answering_the_keeper_lays_where_the_peers_van_may_be_two_drives_on.trig")
    lay(store, ME, NOW)
    ((key, (said, foreseen)),) = _laid(store, ME).items()
    assert (key, said, len(foreseen)) == ((_PEER, _NO_TWO_VANS), [], 11), "eleven places foreseen, none said"
    points = Held(NOW, FORESEEN, *key, tuple(foreseen)).point()
    head, places = points[0], points[1:]
    assert head == {"measurement": "Holdings", "tags": {"origin": "foreseen", "peer": "peer", "constraint": "no_two_vans"},
                    "fields": {"count": 11}, "time": NOW}
    assert {(p["fields"]["x"], p["fields"]["y"]) for p in places} == {
        (4.0, 0.0), (4.0, 1.0), (4.0, 2.0), (5.0, -1.0), (5.0, 0.0), (5.0, 2.0), (5.0, 3.0), (6.0, 0.0), (6.0, 1.0), (6.0, 2.0), (7.0, 1.0)}
    assert {p["tags"]["n"] for p in places} == {str(n) for n in range(11)}, "a place per tag set, so none overwrites another"
    assert all(p["fields"]["until"] == "2026-01-01T12:02:00+00:00" and p["fields"]["type"] == "Van" for p in places)


def test_an_empty_set_is_said_too():
    assert Held(NOW, FORESEEN, _PEER, _NO_TWO_VANS).point() == [
        {"measurement": "Holdings", "tags": {"origin": "foreseen", "peer": "peer", "constraint": "no_two_vans"},
         "fields": {"count": 0}, "time": NOW}]


def test_a_conflict_is_said_with_its_peer_its_constraint_and_how_it_stands(snapshots):
    store = snapshots.stand_in(LAY / "silent_and_never_answering_the_keeper_lays_where_the_peers_van_may_be_two_drives_on.trig")
    (conflict,) = _conflicts(store, ME)
    assert conflict == Conflict(_PEER, _NO_TWO_VANS, standing=True, silent=True, round=0)
    assert Concluded(NOW, (conflict,)).point() == [
        {"measurement": "Conflicts", "tags": {}, "fields": {"count": 1}, "time": NOW},
        {"measurement": "Conflict", "tags": {"peer": "peer", "constraint": "no_two_vans"},
         "fields": {"standing": True, "silent": True, "round": 0, "won_by": ""}, "time": NOW}]
