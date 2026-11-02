"""The briefing over the translator's test world: the self graph and the common beliefs as Turtle with the store's
prefixes, the vocabularies' comments among them, and the status apart, as the block that changes with every
reading."""

from __future__ import annotations

from pathlib import Path

from agent.runtime import boot
from agent.translation.briefing import briefing

WORLD = Path(__file__).parent / "world"


def test_the_world_and_the_self_are_one_block_and_what_it_holds_now_another():
    world, now = briefing(boot(WORLD, "seeker"), "seeker at 2026-11-01 09:00 UTC\nnothing to say yet")
    assert world.startswith("WHO YOU SPEAK FOR") and "THE WORLD AS IT BELIEVES IT" in world
    assert "@prefix orexis:" in world and "orexis:Self" in world, "the store's prefixes, and the self graph"
    assert "flat_12" in world and "rdfs:comment" in world, "the world's things, and what its terms mean"
    assert "nothing to say yet" not in world, "the status is not cached with the world"
    assert now == "WHAT IT HOLDS NOW:\n\nseeker at 2026-11-01 09:00 UTC\nnothing to say yet"


def test_the_briefing_is_the_same_text_for_the_same_beliefs():
    store = boot(WORLD, "seeker")
    assert briefing(store, "")[0] == briefing(store, "")[0], "or the provider caches nothing"
