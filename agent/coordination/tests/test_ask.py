"""`ask`: an agent asks a peer it believes in range what a constraint both may hold reads, saying its own
holdings — once per change of them, and of nobody it does not believe in range."""

from __future__ import annotations

from datetime import timedelta

from agent.coordination.ask import ask
from agent.coordination.holdings import _heard, holdings
from agent.coordination.ontology import question_graph
from agent.speech.said import said
from agent.store import PREFIXES, forget_graph

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


def test_a_question_that_has_lapsed_is_asked_again(meeting, copied):
    """A's patience stated as two seconds: its question holds two seconds, and is asked again after, while
    what A believes of the lane still holds — so a peer that hears it holding knows A is still asking."""
    store = copied(meeting.store(A))
    store.update(PREFIXES + f"""INSERT {{ GRAPH ?g {{ <{A}> coordination:patienceS 2 }} }}
                               WHERE {{ GRAPH ?g {{ <{A}> a orexis:Self }} }}""")
    forget_graph(store, question_graph(A, B, TWO_VANS))      # what A asked in the run, which holds a minute
    for _, document in ask(store, A, meeting.at):
        said(store, A, document)
    assert ask(store, A, meeting.at + timedelta(seconds=1)) == [], "within its period, nothing new"
    assert [peer for peer, _ in ask(store, A, meeting.at + timedelta(seconds=3))] == [B], "lapsed, asked again"
    assert _heard(meeting.store(B), question_graph(A, B, TWO_VANS)), "B heard A's question, and only B was asked"
