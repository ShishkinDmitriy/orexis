"""`answer`: a peer's question is answered only under a constraint the answerer holds too, and only with the
answerer's own holdings that meet the asked ones — never anything else of its plan."""

from __future__ import annotations

from agent.coordination.answer import answer
from agent.coordination.holdings import _heard, _violates, holdings
from agent.coordination.ontology import question_graph
from agent.store import PREFIXES

L = "http://example.org/orexis/world/lane#"
A, B, VAN_A, VAN_B = L + "courier_a", L + "courier_b", L + "van_a", L + "van_b"
TWO_VANS = "http://example.org/orexis/courier#no_two_vans_at_one_position"


def test_an_answer_carries_only_the_answerers_holdings_that_meet_the_asked_ones(walker):
    question = question_graph(A, B, TWO_VANS)
    lane = walker(lambda lane: _heard(lane.store(B), question) and holdings(lane.store(B), TWO_VANS, lane.at))
    store = lane.store(B)
    asked, mine = _heard(store, question), holdings(store, TWO_VANS, lane.at)
    to, document = answer(store, B, question, lane.at)
    assert to == A
    told = _heard(document, next(iter(document.named_graphs())).value)
    assert told, "head on, B's plan meets A's"
    assert set(told) <= set(mine), "only B's own holdings"
    assert all(any(_violates(store, TWO_VANS, h, q) for q in asked) for h in told), \
        "each meets one asked, and the rest of B's plan stays B's"


def test_a_question_under_a_constraint_the_answerer_does_not_hold_gets_no_answer(meeting, copied):
    store = copied(meeting.store(B))
    store.update(PREFIXES + f"DELETE WHERE {{ GRAPH ?g {{ <{B}> planning:holds <{TWO_VANS}> }} }}")
    assert answer(store, B, question_graph(A, B, TWO_VANS), meeting.at) is None


def test_the_agents_own_question_is_no_peers(meeting, copied):
    assert answer(copied(meeting.store(A)), A, question_graph(A, B, TWO_VANS), meeting.at) is None, \
        "said, not heard"
