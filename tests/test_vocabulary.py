"""A volume can be older than the vocabulary, and nothing used to notice.

This is the test that would have caught PR #85. Every other test here builds a fresh store from
the current files, so none of them can meet a belief base written by earlier code — which is
exactly why 102 terms moved namespace with both gates green while every deployed agent was one
restart from silently finding nothing.

So these author a store the old way and then open it the new way, which is the only shape of
test that can see the failure at all.

See knowledge/decisions/a-volume-can-be-older-than-the-vocabulary.md and issue #87.
"""

from __future__ import annotations

import pytest

from agent import genesis, vocabulary
from agent.ontology import AG, beliefs_graph
from agent.store import Store, bindings

from conftest import WORLDS_ROOT, genesis_store

# What `world/society/beliefs/fern.ttl` said before the sweep: every belief in the kernel
# namespace. Written out rather than generated, because a fixture that derived it from the
# current vocabulary would move whenever the vocabulary did and stop being the old world.
#
# `ag:bandLow` and `ag:bandHigh` were here and had to go, which is the one edit that principle
# does not cover: the terms they were renamed TO have since been DELETED, so a store holding
# them is now correctly unmigratable rather than merely old, and every migration test would fail
# on a term that is not what any of them is about. What that case looks like is tested directly,
# on a synthetic term, by `test_a_term_with_no_successor_is_refused_rather_than_dropped`.
BEFORE_THE_SWEEP = f"""
@prefix ag: <{AG}> .

ag:fern_agent
    ag:fastSleepS 30 ;
    ag:slowSleepS 600 ;
    ag:readingGraceS 45 ;
    ag:hasEndowment 100.0 ;
    ag:hasTarget 0.55 ;
    ag:litresPerFraction 2.0 ;
    ag:maxValuePerL 0.80 ;
    ag:metricsIntervalS 60 ;
    ag:reviewIntervalS 300 .
"""


def _aged_store():
    """A store whose public knowledge is current and whose beliefs are a vocabulary behind.

    Exactly the state a running agent is in after an image rebuild: `refresh_public` replaced
    the world and the T-Box from the ratified files, and the volume it was already holding did
    not move, because birth happens once.
    """
    st = genesis_store(world="simulation")
    st.put_graph(beliefs_graph("fern"), BEFORE_THE_SWEEP)
    return st


# --- the vocabulary agrees with itself -----------------------------------------------------

@pytest.mark.parametrize("world", ["simulation", "sensing"])
def test_a_shipped_world_is_current_by_construction(world):
    """Nothing shipped is stale, or the check would refuse every agent on every start.

    The one that matters most: a false positive here is not a warning, it is an outage.
    """
    assert vocabulary.stale(genesis_store(world=world)) == {}


def test_a_kernel_term_that_still_exists_is_not_a_rename():
    """`ag:localId` did not move, so no rename may claim it did.

    The map is built by local name, so a term the kernel still declares has to be excluded
    explicitly — otherwise a package that later declared its own `localId` would silently
    capture the kernel's.

    This was written about `ag:metricsIntervalS`, which then genuinely moved into
    `capabilities/reporting/`. The subject had to change; the assertion did not. Any term the
    kernel still declares serves, and `ag:localId` is the one least likely to move next.
    """
    settled, _ = vocabulary.renames(genesis_store(world="simulation"))
    assert AG + "localId" not in settled


def test_a_name_two_packages_share_is_contested_rather_than_guessed():
    """`i2c:DataPinRole` and `onewire:DataPinRole` are both real and both correct.

    A data pin means something different on each protocol, so `ag:DataPinRole` has no single
    answer and nothing here may pick one. It is reported only if a store actually uses it —
    neither was ever a kernel term, so refusing at load would have stopped every agent booting
    over a collision no volume can contain.
    """
    settled, contested = vocabulary.renames(genesis_store(world="simulation"))
    assert AG + "DataPinRole" in contested
    assert AG + "DataPinRole" not in settled
    assert len(contested[AG + "DataPinRole"]) == 2


# --- the defect itself ----------------------------------------------------------------------

def test_beliefs_a_vocabulary_behind_are_seen():
    """The whole of #87: the store holds values, and the code cannot read them."""
    st = _aged_store()
    found = vocabulary.stale(st)
    assert beliefs_graph("fern") in found, "a volume behind the vocabulary looked current"
    behind = found[beliefs_graph("fern")]
    assert AG + "hasTarget" in behind
    assert behind[AG + "hasTarget"].endswith("water#hasTarget")


def test_what_the_agent_would_have_read_instead_is_nothing():
    """Why it has to be refused rather than warned about.

    Not an error anywhere — an empty result. The agent starts, finds no target, and bids on a
    desire it cannot see. Asserted here so the refusal has a measured reason rather than a
    plausible one.
    """
    st = _aged_store()
    rows = bindings(st.query(
        "SELECT ?v WHERE { GRAPH <%s> { ?a water:hasTarget ?v } }" % beliefs_graph("fern")))
    assert rows == [], "this test's premise is gone — the old spelling now answers"


def test_boot_refuses_and_says_which_terms():
    """Loud, and naming them. A message that says only *something is wrong* costs the reader
    the same hour the silence would have."""
    st = _aged_store()
    with pytest.raises(SystemExit) as exc:
        vocabulary.check(st)
    message = str(exc.value)
    assert "hasTarget" in message and "water#hasTarget" in message
    assert "AGORA_MIGRATE_BELIEFS" in message


# --- and the way forward --------------------------------------------------------------------

def test_migration_keeps_the_value_and_changes_only_the_spelling():
    """The point of not using `rebirth`: 0.55 was this agent's, and it stays 0.55.

    `rebirth` would return it to what the sovereign authored, which for an agent that had
    revised itself is the history worth keeping.
    """
    st = _aged_store()
    vocabulary.check(st, migrating=True)
    rows = bindings(st.query(
        "SELECT ?v WHERE { GRAPH <%s> { ?a water:hasTarget ?v } }" % beliefs_graph("fern")))
    assert [r["v"] for r in rows] == ["0.55"]
    assert vocabulary.stale(st) == {}


def test_migration_moves_every_belief_not_only_the_one_looked_at():
    """A store half in one vocabulary is worse than one honestly stuck."""
    st = _aged_store()
    vocabulary.check(st, migrating=True)
    for query in ("perception:slowSleepS 600", "market:hasEndowment 100",
                  "review:reviewIntervalS 300", "water:hasTarget 0.55"):
        predicate, value = query.split()
        rows = bindings(st.query(
            "SELECT ?v WHERE { GRAPH <%s> { ?a %s ?v } }" % (beliefs_graph("fern"), predicate)))
        assert rows and rows[0]["v"].startswith(value.rstrip("0").rstrip(".")), predicate


def test_a_term_with_no_successor_is_refused_rather_than_dropped():
    """Deletion is not renaming, and guessing at it would lose a value silently."""
    st = _aged_store()
    st.update("INSERT DATA { GRAPH <%s> { <%sfern_agent> <%sabolishedS> 7 } }"
              % (beliefs_graph("fern"), AG, AG))
    with pytest.raises(SystemExit) as exc:
        vocabulary.check(st, migrating=True)
    assert "abolishedS" in str(exc.value)
    assert "no term of that name remains" in str(exc.value)


def test_public_graphs_are_never_the_agents_to_migrate():
    """They are replaced from the ratified files on every start, so a stale term in one would
    mean the files are wrong — and rewriting it here would hide that."""
    st = _aged_store()
    before = {g: len(st.get_graph(g)) for g in st.public_graphs()}
    vocabulary.check(st, migrating=True)
    assert {g: len(st.get_graph(g)) for g in st.public_graphs()} == before


# --- the boot path, end to end --------------------------------------------------------------

def test_an_aged_volume_refuses_to_open(tmp_path, monkeypatch):
    """The persistent case, which is the only one that ever happens in production.

    Written to disk and reopened, because the failure is about a volume surviving a restart —
    an in-memory store cannot be older than the code that made it.
    """
    monkeypatch.delenv("AGORA_MIGRATE_BELIEFS", raising=False)
    path = str(tmp_path / "beliefs")
    world = WORLDS_ROOT / "simulation"

    genesis.open_belief_base(world, "fern", path)  # born, current
    aged = Store(path)
    aged.put_graph(beliefs_graph("fern"), BEFORE_THE_SWEEP)  # and then the code moved on
    del aged

    with pytest.raises(SystemExit, match="hasTarget"):
        genesis.open_belief_base(world, "fern", path)


def test_and_opens_when_asked_to_migrate(tmp_path, monkeypatch):
    path = str(tmp_path / "beliefs")
    world = WORLDS_ROOT / "simulation"

    genesis.open_belief_base(world, "fern", path)
    aged = Store(path)
    aged.put_graph(beliefs_graph("fern"), BEFORE_THE_SWEEP)
    del aged

    monkeypatch.setenv("AGORA_MIGRATE_BELIEFS", "1")
    st = genesis.open_belief_base(world, "fern", path)
    rows = bindings(st.query(
        "SELECT ?v WHERE { GRAPH <%s> { ?a water:hasTarget ?v } }" % beliefs_graph("fern")))
    assert [r["v"] for r in rows] == ["0.55"]
