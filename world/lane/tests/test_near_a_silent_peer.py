"""The courier's constraint that no van stands near a silent peer's van, as shipped (`domains/courier/constraints.ttl`),
asked of a store that holds only what it reads: two cells between the agent's van and the peer's, three while the
lot the agent drew alone this round was lost, and nothing at all of a peer that is not silent or a van nobody it is
in a conflict with acts for. No walk: the text is read off the document, so a change to the domain is what this holds."""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from agent.store import PREFIXES, rows

DOMAIN = Path(__file__).resolve().parents[3] / "domains" / "courier"
C = "http://example.org/orexis/courier#"
T = "http://example.org/test#"
_TEXTS, _DATA = T + "texts", T + "data"


def _select() -> str:
    store = ox.Store()
    store.load((DOMAIN / "constraints.ttl").read_bytes(), format=ox.RdfFormat.TURTLE, to_graph=ox.NamedNode(_TEXTS),
               base_iri=(DOMAIN / "constraints.ttl").as_uri())
    (found,) = rows(store, f"SELECT ?t WHERE {{ GRAPH $graph {{ <{C}no_van_near_a_silent_peers_van> planning:unmetWhen ?s . ?s sh:select ?t }} }}",
                    (), graph=_TEXTS)
    return found["t"]


def _too_near(mine: tuple[int, int], theirs: tuple[int, int], silent: bool = True, lost: bool = False,
              acted_for: bool = True) -> bool:
    """Whether the constraint reads a violation with the keeper's van at `mine` and the peer's at `theirs`."""
    facts = [f"<{T}keeper> a orexis:Self ; orexis:actsFor <{T}van_k> .",
             f"<{T}van_k> a <{C}Van> ; <{C}x> {mine[0]} ; <{C}y> {mine[1]} .",
             f"<{T}van_p> a <{C}Van> ; <{C}x> {theirs[0]} ; <{C}y> {theirs[1]} .",
             f"<{T}conflict> a coordination:Conflict ; coordination:with <{T}peer> ; coordination:draw <{T}draw> ; "
             f"coordination:standing true" + (" ; coordination:silent true ." if silent else " .")]
    if acted_for:
        facts.append(f"<{T}peer> orexis:actsFor <{T}van_p> .")
    if lost:
        facts.append(f"<{T}draw> coordination:wonBy <{T}peer> .")
    store = ox.Store()
    store.update(PREFIXES + f"INSERT DATA {{ GRAPH <{_DATA}> {{ {' '.join(facts)} }} }}")
    return bool(rows(store, _select(), [_DATA]))


@pytest.mark.parametrize("theirs, near", [((4, 1), True), ((5, 1), True), ((4, 2), True), ((6, 1), False), ((5, 2), False)],
                         ids=["beside", "a_cell_between", "a_cell_between_diagonally", "two_cells_between", "two_cells_between_diagonally"])
def test_a_van_with_less_than_two_cells_between_it_and_a_silent_peers_van_violates(theirs, near):
    """A van moves a cell a drive, and what the agent believes of the peer's van may be a drive behind while the
    peer lands another during the agent's own: two cells between are what neither can close."""
    assert _too_near((3, 1), theirs) == near


def test_where_the_lot_was_lost_a_van_keeps_three_cells_between():
    """The agent lost this round's lot: two cells between are not enough, so its present is a violation and only
    a world that drives away is possible — it backs off. Three cells between is far enough."""
    assert _too_near((3, 1), (6, 1), lost=True), "two cells between, the lot lost: too near"
    assert not _too_near((2, 1), (6, 1), lost=True), "three cells between"


def test_a_peer_that_is_not_silent_and_a_van_no_peer_acts_for_are_nothing_to_it():
    """A peer that answers says where its van will be, so this constraint is none of its business; and a van
    standing for nobody the agent is in a conflict with — a parked van — is the other constraints'."""
    assert not _too_near((3, 1), (4, 1), silent=False)
    assert not _too_near((3, 1), (4, 1), acted_for=False)
