"""The briefing over the translator's test world: who the agent is, what the chat lets the model read — the self graph
where it reads it, and the vocabularies by name — and the status apart, as the block that changes with every
reading."""

from __future__ import annotations

from pathlib import Path

from agent.runtime import boot
from agent.translation.briefing import briefing

WORLD = Path(__file__).parent / "world"
O = "http://example.org/orexis#"
SEEKER = "http://example.org/orexis/world/viewing#seeker"


def test_a_chat_reading_the_beliefs_is_briefed_with_the_self_graph_and_the_vocabularies_by_name():
    who, now = briefing(boot(WORLD, "seeker"), SEEKER, (O + "BeliefGraph",), " - speech (93 lines)", "nothing to say yet")
    assert who.startswith("YOU SPEAK FOR seeker.")
    assert "WHAT THIS CHAT LETS YOU READ: every graph of BeliefGraph" in who and " - speech (93 lines)" in who
    assert now == "WHAT IT HOLDS NOW:\n\nnothing to say yet", "the status is not cached with the rest"


def test_a_chat_reading_nothing_is_briefed_with_who_the_agent_is_alone():
    who, _ = briefing(boot(WORLD, "seeker"), SEEKER, (), "", "")
    assert who.startswith("YOU SPEAK FOR seeker.") and "beyond the questions offered as tools" in who
    assert "orexis:Self" not in who and "WHAT THIS CHAT LETS YOU READ" not in who


def test_the_self_graph_is_in_it_where_the_chat_reads_it():
    store = boot(WORLD, "seeker")
    assert "orexis:Self" in briefing(store, SEEKER, (O + "Graph",), "", "")[0]
    assert briefing(store, SEEKER, (O + "Graph",), "", "")[0] == briefing(store, SEEKER, (O + "Graph",), "", "")[0], \
        "the same text for the same beliefs, or the provider caches nothing"


def test_where_the_chat_reads_the_self_graph_each_role_the_agent_plays_is_said_in_its_packages_words():
    who, _ = briefing(boot(WORLD, "seeker"), SEEKER, (O + "Graph",), "", "")
    assert "THE ROLES IT PLAYS:\n - " in who and "\n - Translator: An agent that speaks with people in the chats it is in" in who, who
    assert "THE ROLES IT PLAYS" not in briefing(boot(WORLD, "seeker"), SEEKER, (), "", "")[0]
