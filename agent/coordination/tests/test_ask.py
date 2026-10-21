"""`ask`: an agent asks a peer it believes in range what a constraint both may hold reads, saying its own
holdings — once per change of them, and of nobody it does not believe in range."""

from __future__ import annotations

from agent.coordination.ask import ask
from agent.coordination.holdings import _heard, holdings
from agent.coordination.ontology import question_graph
from agent.speech.said import said

L = "http://example.org/orexis/world/lane#"
A, B, VAN_A, VAN_B = L + "courier_a", L + "courier_b", L + "van_a", L + "van_b"
TWO_VANS = "http://example.org/orexis/courier#no_two_vans_at_one_position"


def test_nobody_out_of_range_is_asked(walker):
    lane = walker(lambda lane: True)
    assert holdings(lane.store(A), TWO_VANS, lane.at), "A has somewhere to go"
    assert ask(lane.store(A), A, lane.at) == [], "and B, six cells off, is believed nowhere"


def test_a_peer_in_range_is_asked_with_the_askers_holdings_and_not_again_until_they_change(meeting, copied):
    store = copied(meeting.store(A))
    for _, document in ask(store, A, meeting.at):
        said(store, A, document)                  # what changed since the pass, said as the part says it
    assert set(_heard(store, question_graph(A, B, TWO_VANS))) == set(holdings(store, TWO_VANS, meeting.at)), \
        "the question carries the asker's holdings"
    assert ask(store, A, meeting.at) == [], "and nothing is asked again while they stand"
    assert _heard(meeting.store(B), question_graph(A, B, TWO_VANS)), "B heard A's question, and only B was asked"
