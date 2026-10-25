"""The draw domain's texts, as shipped (`domains/draw/`), held to what #923 asks of a draw by commit and reveal:
a reveal is not taken before the peer's commitment is heard; a reveal said for another draw — another round,
another round's number, another pair — decides nothing for the standing one; and over thousands of draws the
lower name wins about half, both agents concluding the same winner whichever is the self. And a silent peer's
draw is a lot drawn alone: won as the agent's own secret says, about half the time, and of no conflict that is
not silent.

The texts are read off the documents and not restated here, so a change to the domain is what these hold."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent.coordination.ontology import conflict_of, conflicts_graph, draw_of
from agent.ontology import BELIEF, SELF_GRAPH
from agent.store import PREFIXES, construct, graphs_of, rows

L = "http://example.org/orexis/world/lane#"
A, B, C = L + "courier_a", L + "courier_b", L + "courier_c"
TWO_VANS = "http://example.org/orexis/courier#no_two_vans_at_one_position"
DRAW = "http://example.org/orexis/draw#"
DOMAIN = Path(__file__).resolve().parents[3] / "domains" / "draw"
_TEXTS = "http://example.org/test#draw"
_DATA = "http://example.org/test#data"


def _text(select: str) -> str:
    """One text of the draw domain's documents, by the query that finds it."""
    store = ox.Store()
    for name in ("actions.ttl", "rules.ttl"):
        store.load((DOMAIN / name).read_bytes(), format=ox.RdfFormat.TURTLE, to_graph=ox.NamedNode(_TEXTS),
                   base_iri=(DOMAIN / name).as_uri())
    (found,) = rows(store, select, (), graph=_TEXTS)
    return found["t"]


def _precondition() -> str:
    return _text(f"SELECT ?t WHERE {{ GRAPH $graph {{ <{DRAW}Revealing> planning:precondition ?t }} }}")


def _outcome(name: str = "winner") -> str:
    return _text(f"SELECT ?t WHERE {{ GRAPH $graph {{ <{DRAW}{name}> a coordination:Outcome ; sh:construct ?t }} }}")


def _read(store: ox.Store):
    return [*graphs_of(store, BELIEF), *graphs_of(store, BELIEF, common=True), *graphs_of(store, SELF_GRAPH)]


def test_a_reveal_is_not_taken_before_the_peers_commitment_is_heard(meeting, copied):
    """Shown first, a number would let the peer choose its own after: the Revealing action's precondition
    admits a peer only once the draw has both commitments."""
    store = copied(meeting.store(A))
    text = _precondition()
    assert rows(store, text, _read(store)) == [], "decided, the draw is revealed in by nobody"
    store.update(PREFIXES + f"DELETE WHERE {{ GRAPH <{conflicts_graph(A)}> {{ ?d coordination:wonBy ?w }} }}")
    store.update(PREFIXES + f"DELETE WHERE {{ GRAPH ?g {{ ?d <{DRAW}revealedBy> <{A}> }} }}")
    assert [r["peer"] for r in rows(store, text, _read(store))] == [B], "both committed and A not yet revealed: A reveals"
    store.update(PREFIXES + f"DELETE WHERE {{ GRAPH ?g {{ ?d <{DRAW}committedBy> <{B}> }} }}")
    assert rows(store, text, _read(store)) == [], "B's commitment not heard: A does not reveal"


def _number(secret: str, draw: str) -> str:
    return hashlib.sha256(f"{secret}|{draw}".encode()).hexdigest()


def _hash(draw: str, number: str) -> str:
    return hashlib.sha256(f"{draw}|{number}".encode()).hexdigest()


def _draws(me: str, secret: str, peer: str, peers: str, draws: list[str], reveals: dict[str, str] | None = None) -> ox.Store:
    """A store in which `me` holds `secret`, both have committed to every draw of `draws` and the peer has
    revealed each — its number for the draw, or what `reveals` says instead — as the domain's extractions
    believe the documents."""
    store = ox.Store()
    g = ox.NamedNode(_DATA)
    facts = [f"<{me}> a orexis:Self ; coordination:secret \"{secret}\" ."]
    for d in draws:
        number = _number(peers, d)
        facts.append(f"<{d}/commitment/me> a <{DRAW}Commitment> ; <{DRAW}of> <{d}> ; <{DRAW}by> <{me}> ; "
                     f"<{DRAW}hash> \"{_hash(d, _number(secret, d))}\" .")
        facts.append(f"<{d}/commitment/peer> a <{DRAW}Commitment> ; <{DRAW}of> <{d}> ; <{DRAW}by> <{peer}> ; "
                     f"<{DRAW}hash> \"{_hash(d, number)}\" .")
        of, said = (reveals or {}).get(d, (d, number))
        facts.append(f"<{d}/reveal/peer> a <{DRAW}Reveal> ; <{DRAW}of> <{of}> ; <{DRAW}by> <{peer}> ; <{DRAW}number> \"{said}\" .")
    store.update(PREFIXES + f"INSERT DATA {{ GRAPH <{g.value}> {{ {' '.join(facts)} }} }}")
    return store


def _won(store: ox.Store) -> dict[str, str]:
    return {t.subject.value: t.object.value for t in construct(store, _outcome(), [_DATA])}


SECRET_A, SECRET_B = "1" * 64, "2" * 64
CONFLICT = conflict_of(A, B, TWO_VANS)
D0, D1 = draw_of(CONFLICT, 0), draw_of(CONFLICT, 1)
ELSEWHERE = draw_of(conflict_of(A, C, TWO_VANS), 0)


@pytest.mark.parametrize("reveal", [
    pytest.param((D1, _number(SECRET_B, D1)), id="another_round"),
    pytest.param((D0, _number(SECRET_B, D1)), id="another_rounds_number"),
    pytest.param((ELSEWHERE, _number(SECRET_B, ELSEWHERE)), id="another_pair"),
])
def test_a_reveal_for_another_draw_decides_nothing_for_the_standing_one(reveal):
    """A reveal is `draw:of` one draw, and its number hashes to the commitment of that draw alone: said into
    another round, carrying another round's number, or said of another pair's conflict, it decides nothing
    of the standing draw (replay), where the reveal for it decides it."""
    assert D0 in _won(_draws(A, SECRET_A, B, SECRET_B, [D0])), "the reveal for the draw decides it"
    assert D0 not in _won(_draws(A, SECRET_A, B, SECRET_B, [D0], reveals={D0: reveal}))


def test_over_thousands_of_draws_the_lower_name_wins_about_half_and_both_selves_conclude_alike():
    """Four thousand rounds of one conflict, each its own draw: the lower name wins about half, and the
    winner of each is the same whichever agent is the self, so swapping self and peer changes nothing."""
    draws = [draw_of(CONFLICT, n) for n in range(4000)]
    as_a = _won(_draws(A, SECRET_A, B, SECRET_B, draws))
    as_b = _won(_draws(B, SECRET_B, A, SECRET_A, draws))
    assert len(as_a) == len(draws) == len(as_b), "every draw decided"
    assert as_a == as_b, "the same winner from either side"
    share = sum(1 for w in as_a.values() if w == A) / len(draws)
    assert 0.46 < share < 0.54, f"the lower name won {share:.3f} of the draws"


def _silent(me: str, secret: str, peer: str, draws: list[str], silent: bool = True) -> ox.Store:
    """A store in which `me` holds `secret` and a conflict with `peer` per draw of `draws`, silent or not, and
    nothing said by anybody."""
    store = ox.Store()
    facts = [f"<{me}> a orexis:Self ; coordination:secret \"{secret}\" ."]
    for n, d in enumerate(draws):
        facts.append(f"<{CONFLICT}/{n}> a coordination:Conflict ; coordination:with <{peer}> ; coordination:draw <{d}>"
                     + (" ; coordination:silent true ." if silent else " ."))
    store.update(PREFIXES + f"INSERT DATA {{ GRAPH <{_DATA}> {{ {' '.join(facts)} }} }}")
    return store


def _lot(store: ox.Store) -> dict[str, str]:
    return {t.subject.value: t.object.value for t in construct(store, _outcome("lot"), [_DATA])}


def test_a_silent_peers_draw_is_won_as_the_agents_own_secret_says_and_no_other_draw_is():
    """Nobody reveals to a peer that is silent, so its draw is a lot the agent draws alone: the first digit of a
    hash of its secret and the draw's name, odd for the agent. A conflict that is not silent is the commitments'
    and reveals' to decide, and the lot says nothing of it."""
    digit = hashlib.sha256(f"{SECRET_A}|lot|{D0}".encode()).hexdigest()[0]
    assert _lot(_silent(A, SECRET_A, B, [D0])) == {D0: A if digit in "13579bdf" else B}
    assert _lot(_silent(A, SECRET_A, B, [D0], silent=False)) == {}


def test_over_thousands_of_rounds_a_lot_drawn_alone_backs_off_about_half_the_time():
    """Four thousand rounds of one silent conflict, a lot drawn afresh each: the agent loses — and so backs off —
    about half, whoever the peer is, since nothing of the peer's is in it."""
    draws = [draw_of(CONFLICT, n) for n in range(4000)]
    as_a = _lot(_silent(A, SECRET_A, B, draws))
    assert len(as_a) == len(draws), "every round decided"
    assert as_a == {d: (A if w == A else B) for d, w in _lot(_silent(A, SECRET_A, C, draws)).items()}, \
        "the same lots against another peer"
    share = sum(1 for w in as_a.values() if w == B) / len(draws)
    assert 0.46 < share < 0.54, f"A backed off in {share:.3f} of the rounds"
