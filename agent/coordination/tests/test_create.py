"""`create`: coordination's part — linked to speech's, through which it says what it asks and answers; started,
it answers a question as it is heard."""

from __future__ import annotations

import pyoxigraph as ox

from agent.coordination.holdings import _heard
from agent.coordination.ontology import answer_graph, question_graph

L = "http://example.org/orexis/world/lane#"
A, B, VAN_A, VAN_B = L + "courier_a", L + "courier_b", L + "van_a", L + "van_b"
TWO_VANS = "http://example.org/orexis/courier#no_two_vans_at_one_position"


def test_the_part_says_through_speechs_part(meeting):
    runtime = meeting.bus.runtimes["courier_a"]
    assert runtime.parts["coordination"].speech is runtime.parts["speech"]


def test_a_question_heard_is_answered_as_it_arrives(meeting):
    b = meeting.store(B)
    assert _heard(b, question_graph(A, B, TWO_VANS)), "B heard A's question"
    assert list(b.quads_for_pattern(None, None, None, ox.NamedNode(answer_graph(B, A, TWO_VANS)))), \
        "and said its answer"
