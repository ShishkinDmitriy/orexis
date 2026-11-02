"""The chats an agent is in, read off its world, and whether words name an agent."""

from __future__ import annotations

from pathlib import Path

from agent.runtime import boot
from agent.translation.chat import chats_of, named

WORLD = Path(__file__).parent / "world"
V = "http://example.org/orexis/world/viewing#"
SEEKER = V + "seeker"


def test_the_agent_reads_its_chats_off_the_world_each_with_its_channel_and_who_is_in_it():
    chats = {c.iri.rsplit("#", 1)[1]: c for c in chats_of(boot(WORLD, "seeker"))}
    assert set(chats) == {"seeker_and_anna", "seeker_and_boris", "seeker_and_clara", "household"}
    assert chats["seeker_and_clara"].channel == V + "clara_telegram" and chats["seeker_and_clara"].people == ((V + "clara", "Clara"),)
    household = chats["household"]
    assert household.people == ((V + "anna", "Anna"), (V + "clara", "Clara"))
    assert household.agents == ((V + "keeper", ("keeper", "Kim")), (SEEKER, ("seeker",))), \
        "an agent answers to its local id, its IRI's local name and the name it goes by"
    assert chats["seeker_and_clara"].person(None) == (V + "clara", "Clara"), "a chat's one person writes where the channel tells none"
    assert household.person(None) is None and household.person(V + "boris") is None, "and in a group nobody unnamed, nor a stranger"


def test_an_agent_is_named_by_a_word_of_its_own():
    assert named("seeker, how is it going?", ("seeker",)) and named("ask the Seeker", ("seeker",))
    assert not named("the seekers are out", ("seeker",)) and not named("house-seeker", ("seeker",))


def test_a_chat_says_the_kinds_of_graph_its_model_may_read_and_one_saying_none_reads_none():
    chats = {c.iri.rsplit("#", 1)[1]: c for c in chats_of(boot(WORLD, "seeker"))}
    assert chats["seeker_and_clara"].reads == ("http://example.org/orexis#BeliefGraph",)
    assert chats["household"].reads == () and chats["seeker_and_anna"].reads == ()
