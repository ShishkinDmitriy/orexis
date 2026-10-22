"""`conclude`: each agent concludes its conflicts itself, from the answers it said and heard — one per pair and
constraint, named alike by both; standing while the peer is in range; its draw decided by the outcome a world's
rules ship, restarted a round on past its patience, and the peer silent past the rounds the agent states."""

from __future__ import annotations

from datetime import datetime, timedelta

from agent.coordination.conclude import conclude
from agent.coordination.ontology import conflict_of, conflicts_graph, draw_of, question_graph
from agent.store import PREFIXES, rows

L = "http://example.org/orexis/world/lane#"
A, B, VAN_A, VAN_B = L + "courier_a", L + "courier_b", L + "van_a", L + "van_b"
TWO_VANS = "http://example.org/orexis/courier#no_two_vans_at_one_position"

_CONFLICTS_Q = """SELECT ?c ?peer ?constraint ?round ?standing ?silent ?draw ?w WHERE { GRAPH $graph {
  ?c a coordination:Conflict ; coordination:with ?peer ; coordination:over ?constraint ; coordination:round ?round ;
     coordination:draw ?draw . OPTIONAL { ?c coordination:standing ?standing } OPTIONAL { ?c coordination:silent ?silent }
  OPTIONAL { ?draw coordination:wonBy ?w } } }"""


def _conflicts(store, me):
    return {r["c"]: r for r in rows(store, _CONFLICTS_Q, (), graph=conflicts_graph(me))}


def test_each_concludes_the_one_conflict_itself_named_alike_and_both_conclude_one_winner(meeting):
    a, b = _conflicts(meeting.store(A), A), _conflicts(meeting.store(B), B)
    c = conflict_of(A, B, TWO_VANS)
    assert c == conflict_of(B, A, TWO_VANS) and c in a and c in b, (a, b)
    assert (a[c]["peer"], b[c]["peer"], a[c]["constraint"]) == (B, A, TWO_VANS)
    assert a[c]["standing"] == b[c]["standing"] == "true"
    assert a[c]["draw"] == b[c]["draw"] == draw_of(c, int(a[c]["round"]))
    assert a[c]["w"] == b[c]["w"] == B, "B goes first, by the numbers the two secrets give"


def _undecided(store, me):
    """`store` with no winner believed: the reveals heard taken out, and what was concluded of them."""
    store.update(PREFIXES + """DELETE WHERE { GRAPH ?g { ?r a <http://example.org/orexis/draw#Reveal> ; ?p ?o } }""")
    store.update(PREFIXES + f"DELETE WHERE {{ GRAPH <{conflicts_graph(me)}> {{ ?d coordination:wonBy ?w }} }}")
    return store


def test_a_reveal_that_does_not_hash_to_its_commitment_decides_nothing(meeting, copied):
    store = copied(meeting.store(A))
    store.update(PREFIXES + """
DELETE { GRAPH ?g { ?r <http://example.org/orexis/draw#number> ?n } }
INSERT { GRAPH ?g { ?r <http://example.org/orexis/draw#number> "forged" } }
WHERE  { GRAPH ?g { ?r a <http://example.org/orexis/draw#Reveal> ; <http://example.org/orexis/draw#by> <%s> ;
                       <http://example.org/orexis/draw#number> ?n } }""" % B)
    store.update(PREFIXES + f"DELETE WHERE {{ GRAPH <{conflicts_graph(A)}> {{ ?d coordination:wonBy ?w }} }}")
    conclude(store, A, meeting.at)
    assert _conflicts(store, A)[conflict_of(A, B, TWO_VANS)].get("w") is None


def test_an_undecided_draw_restarts_a_round_on_past_the_patience_and_the_peer_is_silent_past_the_rounds(meeting, copied):
    """A's patience stated as two seconds, so the rounds pass while what A believes of the lane still holds."""
    store = _undecided(copied(meeting.store(A)), A)
    store.update(PREFIXES + f"""INSERT {{ GRAPH ?g {{ <{A}> coordination:patienceS 2 }} }}
                               WHERE {{ GRAPH ?g {{ <{A}> a orexis:Self }} }}""")
    c = conflict_of(A, B, TWO_VANS)
    conclude(store, A, meeting.at)
    start = int(_conflicts(store, A)[c]["round"])
    conclude(store, A, meeting.at + timedelta(seconds=1))
    assert int(_conflicts(store, A)[c]["round"]) == start, "within the patience, the round stands"
    at = meeting.at
    for n in range(1, 4 - start):
        at += timedelta(seconds=3)
        conclude(store, A, at)
        assert int(_conflicts(store, A)[c]["round"]) == start + n
    assert _conflicts(store, A)[c].get("silent") == "true", "three rounds, and B is taken as silent"


def test_a_peer_unseen_stands_in_the_conflict_while_it_asks_and_leaves_it_when_it_stops(meeting, copied):
    """B, believing van A nowhere, keeps the conflict while A's question holds: A's asking says A is there,
    and an agent that does not see its peer is drawn in by the peer's word. Past the question, neither seen
    nor asking, A is out of it."""
    store = copied(meeting.store(B))
    for axis in ("x", "y"):
        store.update(PREFIXES + f"DELETE WHERE {{ GRAPH ?g {{ <{VAN_A}> <http://example.org/orexis/courier#{axis}> ?v }} }}")
    (lapses,) = [r["end"] for r in rows(store, _PERIOD_Q, (), graph=question_graph(A, B, TWO_VANS))]
    conclude(store, B, meeting.at)
    assert _conflicts(store, B)[conflict_of(A, B, TWO_VANS)].get("standing") == "true", "A is still asking"
    conclude(store, B, datetime.fromisoformat(lapses) + timedelta(seconds=1))
    assert _conflicts(store, B)[conflict_of(A, B, TWO_VANS)].get("standing") is None, "and then it is not"


_PERIOD_Q = """SELECT ?end WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $graph dcterms:temporal/orexis:end ?end } }"""
