"""What coordination says happened, as events in the journal: the holdings it asked with, laid as said or foreseen,
and its conflicts — each a set said whole, replacing the one before (`agent/coordination/events.py`)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from agent.conftest import ME, NOW
from agent.coordination.conclude import _conflicts
from agent.coordination.events import FORESEEN, Concluded, Held
from agent.coordination.lay import _laid, lay
from agent.journal import Journal, mint

LAY = Path(__file__).parent / "lay"
_PEER, _NO_TWO_VANS = "http://example.org/test#peer", "http://example.org/test#no_two_vans"
_PREFIXES = """PREFIX coordination: <http://example.org/orexis/coordination#> PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX t: <http://example.org/test#> PREFIX courier: <http://example.org/orexis/courier#>"""


def _kept(event) -> Journal:
    journal, node = Journal(), mint()
    journal.record(node, event.statements(node), event.at)
    return journal


def _rows(journal: Journal, text: str) -> list[dict]:
    found = journal.store.query(_PREFIXES + text, use_default_graph_as_union=True)
    return [{v.value: (r[v].value if r[v] is not None else None) for v in found.variables} for r in found]


def test_what_a_silent_peer_is_foreseen_at_is_an_event_with_a_holding_per_place(snapshots):
    store = snapshots.stand_in(LAY / "silent_and_never_answering_the_keeper_lays_where_the_peers_van_may_be_two_drives_on.trig")
    lay(store, ME, NOW)
    ((key, (said, foreseen)),) = _laid(store, ME).items()
    assert (key, said, len(foreseen)) == ((_PEER, _NO_TWO_VANS), [], 11), "eleven places foreseen, none said"
    journal = _kept(Held(NOW, FORESEEN, *key, tuple(foreseen)))
    places = _rows(journal, """
SELECT ?x ?y ?until ?thing ?at WHERE { ?e a coordination:Foreseen ; prov:atTime ?at ; coordination:peer t:peer ;
  coordination:over t:no_two_vans ; coordination:holding ?h . ?h coordination:of ?thing ; coordination:until ?until ;
  coordination:taken false ; courier:x ?x ; courier:y ?y }""")
    assert {(float(p["x"]), float(p["y"])) for p in places} == {
        (4.0, 0.0), (4.0, 1.0), (4.0, 2.0), (5.0, -1.0), (5.0, 0.0), (5.0, 2.0), (5.0, 3.0), (6.0, 0.0), (6.0, 1.0), (6.0, 2.0), (7.0, 1.0)}
    assert {datetime.fromisoformat(p["until"]) for p in places} == {NOW + timedelta(minutes=2)}
    assert {datetime.fromisoformat(p["at"]) for p in places} == {NOW}
    assert {r["k"] for p in places for r in _rows(journal, f"SELECT ?k WHERE {{ <{p['thing']}> a ?k }}")} == {
        "http://example.org/orexis/courier#Van"}, "what each thing is, is said of the thing"
    assert not _rows(journal, "SELECT ?h WHERE { ?h a coordination:Holding , courier:Van }"), "and never of a holding"


def test_an_empty_set_is_said_too():
    journal = _kept(Held(NOW, FORESEEN, _PEER, _NO_TWO_VANS))
    assert _rows(journal, "SELECT ?e WHERE { ?e a coordination:Foreseen FILTER NOT EXISTS { ?e coordination:holding ?h } }") != []


def test_a_conflict_is_said_under_its_own_name_with_its_peer_its_constraint_and_how_it_stands(snapshots):
    store = snapshots.stand_in(LAY / "silent_and_never_answering_the_keeper_lays_where_the_peers_van_may_be_two_drives_on.trig")
    (conflict,) = _conflicts(store, ME)
    assert (conflict.peer, conflict.constraint, conflict.standing, conflict.silent, conflict.round, conflict.won_by) == (
        _PEER, _NO_TWO_VANS, True, True, 0, None)
    journal = _kept(Concluded(NOW, (conflict,)))
    assert _rows(journal, """
SELECT ?c ?standing ?silent ?round WHERE { ?e a coordination:Concluded ; coordination:conflict ?c .
  ?c a coordination:Conflict ; coordination:with t:peer ; coordination:over t:no_two_vans ;
     coordination:standing ?standing ; coordination:silent ?silent ; coordination:round ?round }""") == [
        {"c": conflict.conflict, "standing": "true", "silent": "true", "round": "0"}]
