"""A world says which version it is, and can be caught claiming wrongly.

`ag:WorldVersion` was documented as an append-only chain and was one node with no predecessor,
no author and no timestamp — read in four places, written nowhere. So `world_version` in the
metrics, whose stated job is catching an agent still running a world since re-ratified, could
never differ. These hold the chain to being real.

See knowledge/decisions/a-version-is-a-snapshot.md.
"""

from __future__ import annotations

import shutil

import pytest

from agent import genesis, versions
from agent.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH
from agent.store import Store, bindings
from onboarding.ratify import ratify

from conftest import WORLDS_ROOT

USER = "http://example.org/agora/user/dimonina"
WORLDS = ["society", "simulation", "sensing"]


def _built(path):
    st = Store()
    genesis.refresh_public(st, path)
    return st


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    """A real world, copied somewhere it can be amended without touching the repository."""
    shutil.copytree(WORLDS_ROOT / "society", tmp_path / "society")
    monkeypatch.setattr(genesis, "WORLDS_ROOT", tmp_path)
    return tmp_path / "society"


# --- what a version covers -------------------------------------------------------------------

@pytest.mark.parametrize("world", WORLDS)
def test_every_world_is_ratified_and_says_what_it_covers(world):
    path = genesis.world_dir(world)
    assert versions.drift(_built(path).query, genesis.ratified_files(path)) is None


def test_the_hash_ignores_an_agents_opening_beliefs(scratch):
    """Beliefs never enter the world graph, and an agent's opening opinion is its own. Were they
    covered, editing fern's target would bump the version stamped on every other agent's
    observations — `ag:underWorldVersion` would move for a reason unrelated to what it records."""
    before = versions.content_hash(genesis.ratified_files(scratch))
    (scratch / "beliefs" / "fern.ttl").write_text(
        (scratch / "beliefs" / "fern.ttl").read_text() + "\n# a re-authored belief\n")
    assert versions.content_hash(genesis.ratified_files(scratch)) == before
    assert versions.drift(_built(scratch).query, genesis.ratified_files(scratch)) is None


def test_the_hash_does_not_cover_the_file_that_states_it(scratch):
    """The circularity this file layout exists to avoid: a fingerprint cannot cover the document
    that records the fingerprint, because writing it would change what it describes."""
    assert genesis.VERSIONS_FILE not in [p.name for p in genesis.ratified_files(scratch)]
    assert genesis.VERSIONS_FILE in [p.name for p in genesis.world_files(scratch)]


def test_a_version_travels_with_the_agent_but_the_stand_does_not(scratch):
    """Hardware is withheld because an agent must never learn which pin a probe is on. A version
    is neither secret nor large, and the agent must cite it on every observation it records."""
    given = [p.name for p in genesis.society_files(scratch)]
    assert genesis.VERSIONS_FILE in given
    assert "hardware.ttl" not in given


# --- the head is derived, never stated ---------------------------------------------------------

@pytest.mark.parametrize("world", WORLDS)
def test_the_current_version_is_derived_and_not_ratified(world):
    """Stating it would mean rewriting a line on every ratification, and an append-only chain
    must not require that. So it is computed, and lands with every other computed fact."""
    st = _built(genesis.world_dir(world))
    ratified = bindings(st.query(
        f"SELECT ?v WHERE {{ GRAPH <{WORLD_GRAPH}> {{ ?w ag:currentVersion ?v }} }}"))
    derived = bindings(st.query(
        f"SELECT ?v WHERE {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{ ?w ag:currentVersion ?v }} }}"))
    assert not ratified
    assert len(derived) == 1


def test_the_head_is_the_version_nothing_revises(scratch):
    ratify("society", user=USER)  # no change -> no version; the chain is still one long
    (scratch / "world.ttl").write_text((scratch / "world.ttl").read_text() + "\nag:note a ag:World .\n")
    assert ratify("society")

    st = _built(scratch)
    chain = versions.chain(st.query)
    assert [v["number"] for v in chain] == ["1", "2"]
    assert chain[1]["predecessor"].endswith("version_1")
    assert versions.current(st.query)["number"] == "2"


# --- ratifying ---------------------------------------------------------------------------------

def test_ratifying_an_unchanged_world_mints_nothing(scratch):
    """Otherwise the chain records when someone ran a command rather than when the world changed,
    and every reader comparing versions starts seeing differences that mean nothing."""
    assert ratify("society") is False
    assert len(versions.chain(_built(scratch).query)) == 1


def test_ratifying_records_who_and_inherits_the_last_hand(scratch):
    (scratch / "world.ttl").write_text((scratch / "world.ttl").read_text() + "\nag:note a ag:World .\n")
    assert ratify("society")
    assert versions.attribution(_built(scratch).query) == USER


def test_a_different_user_may_ratify_the_next_version(scratch):
    """The case a world attributed once, for ever, could never express."""
    alice = "http://example.org/agora/user/alice"
    (scratch / "world.ttl").write_text((scratch / "world.ttl").read_text() + "\nag:note a ag:World .\n")
    ratify("society", user=alice)
    assert versions.attribution(_built(scratch).query) == alice


def test_ratifying_only_appends(scratch):
    """Append-only in the literal sense: nothing already written is rewritten, which is what
    makes `git log versions.ttl` the history of who ratified what."""
    before = (scratch / genesis.VERSIONS_FILE).read_text()
    (scratch / "world.ttl").write_text((scratch / "world.ttl").read_text() + "\nag:note a ag:World .\n")
    ratify("society")
    assert (scratch / genesis.VERSIONS_FILE).read_text().startswith(before)


# --- the gate ----------------------------------------------------------------------------------

def test_editing_without_ratifying_fails_validation(scratch):
    """The failure this exists to catch, and it is discipline rather than design: someone amends
    a world and forgets, and every agent then reports a version its world no longer has."""
    from onboarding.validate import validate_world

    assert validate_world("society")
    (scratch / "world.ttl").write_text((scratch / "world.ttl").read_text() + "\nag:note a ag:World .\n")
    assert not validate_world("society")

    wrong = versions.drift(_built(scratch).query, genesis.ratified_files(scratch))
    assert "agora-ratify" in wrong, "the refusal must name the command that fixes it"


def test_an_agent_reads_a_version_that_can_actually_change(scratch, monkeypatch):
    """`metrics.py` reports `world_version` to catch an agent running a world since re-ratified.
    That was unreachable while nothing ever bumped it."""
    from agent.world import load_world

    assert int(load_world(_built(scratch).query).version) == 1
    (scratch / "world.ttl").write_text((scratch / "world.ttl").read_text() + "\nag:note a ag:World .\n")
    ratify("society")
    assert int(load_world(_built(scratch).query).version) == 2
