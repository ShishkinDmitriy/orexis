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

from agent_old import genesis, vocabulary
from orexis_agent_progression.ontology import OREXIS, picks_graph, PROGRESSION
from orexis_agent_progression.store import Store, bindings

from conftest import WORLDS_ROOT, genesis_store
from orexis_agent_progression.ontology import PUBLIC

# What `world/society/beliefs/fern.ttl` said before the sweep: every belief in the kernel
# namespace. Written out rather than generated, because a fixture that derived it from the
# current vocabulary would move whenever the vocabulary did and stop being the old world.
#
# `orexis:bandLow`, `orexis:bandHigh` and `orexis:hasTarget` were here and had to go, which is the one edit
# that principle does not cover: the terms they were renamed TO have since been DELETED — the
# bands in favour of the deduced region, the target in favour of `sensing:aims`, which is a
# STRUCTURE and so not a rename at all — and a store holding them is now correctly unmigratable
# rather than merely old. Every migration test would fail on a term that is not what any of them
# is about. What that case looks like is tested directly, on a synthetic term, by
# `test_a_term_with_no_successor_is_refused_rather_than_dropped`.
BEFORE_THE_SWEEP = f"""
@prefix orexis: <{OREXIS}> .

orexis:fern_agent
    orexis:fastSleepS 30 ;
    orexis:slowSleepS 600 ;
    orexis:readingGraceS 45 ;
    orexis:hasEndowment 100.0 ;
    orexis:litresPerFraction 2.0 ;
    orexis:maxValuePerL 0.80 ;
    orexis:metricsIntervalS 60 ;
    orexis:reviewIntervalS 300 .
"""


def _aged_store():
    """A store whose public knowledge is current and whose beliefs are a vocabulary behind.

    Exactly the state a running agent is in after an image rebuild: `refresh_public` replaced
    the world and the T-Box from the ratified files, and the volume it was already holding did
    not move, because birth happens once.
    """
    st = genesis_store(world="simulation")
    st.put_graph(picks_graph("fern"), BEFORE_THE_SWEEP)
    return st


# --- the vocabulary agrees with itself -----------------------------------------------------

@pytest.mark.parametrize("world", ["simulation", "sensing"])
def test_a_shipped_world_is_current_by_construction(world):
    """Nothing shipped is stale, or the check would refuse every agent on every start.

    The one that matters most: a false positive here is not a warning, it is an outage.
    """
    assert vocabulary.stale(genesis_store(world=world)) == {}


def test_a_kernel_term_that_still_exists_is_not_a_rename():
    """`orexis:localId` did not move, so no rename may claim it did.

    The map is built by local name, so a term the kernel still declares has to be excluded
    explicitly — otherwise a package that later declared its own `localId` would silently
    capture the kernel's.

    This was written about `orexis:metricsIntervalS`, which then genuinely moved into
    `capabilities/reporting/`. The subject had to change; the assertion did not. Any term the
    kernel still declares serves, and `orexis:localId` is the one least likely to move next.
    """
    settled, _ = vocabulary.renames(genesis_store(world="simulation"))
    assert OREXIS + "localId" not in settled


def test_a_name_two_packages_share_is_contested_rather_than_guessed():
    """`i2c:DataPinRole` and `onewire:DataPinRole` are both real and both correct.

    A data pin means something different on each protocol, so `orexis:DataPinRole` has no single
    answer and nothing here may pick one. It is reported only if a store actually uses it —
    neither was ever a kernel term, so refusing at load would have stopped every agent booting
    over a collision no volume can contain.
    """
    settled, contested = vocabulary.renames(genesis_store(world="simulation"))
    assert OREXIS + "DataPinRole" in contested
    assert OREXIS + "DataPinRole" not in settled
    assert len(contested[OREXIS + "DataPinRole"]) == 2


# --- the defect itself ----------------------------------------------------------------------

def test_beliefs_a_vocabulary_behind_are_seen():
    """The whole of #87: the store holds values, and the code cannot read them."""
    st = _aged_store()
    found = vocabulary.stale(st)
    assert picks_graph("fern") in found, "a volume behind the vocabulary looked current"
    behind = found[picks_graph("fern")]
    assert OREXIS + "slowSleepS" in behind
    assert behind[OREXIS + "slowSleepS"].endswith("sensing#slowSleepS")


def test_what_the_agent_would_have_read_instead_is_nothing():
    """Why it has to be refused rather than warned about.

    Not an error anywhere — an empty result. The agent starts, finds no cadence, and watches on
    a rhythm it cannot see. Asserted here so the refusal has a measured reason rather than a
    plausible one.
    """
    st = _aged_store()
    rows = bindings(st.query(
        "SELECT ?v WHERE { GRAPH <%s> { ?a sensing:slowSleepS ?v } }" % picks_graph("fern"), st.graphs_of(PUBLIC)))
    assert rows == [], "this test's premise is gone — the old spelling now answers"


def test_boot_refuses_and_says_which_terms():
    """Loud, and naming them. A message that says only *something is wrong* costs the reader
    the same hour the silence would have."""
    st = _aged_store()
    with pytest.raises(SystemExit) as exc:
        vocabulary.check(st)
    message = str(exc.value)
    assert "slowSleepS" in message and "sensing#slowSleepS" in message
    assert "OREXIS_MIGRATE_BELIEFS" in message


# --- and the way forward --------------------------------------------------------------------

def test_migration_keeps_the_value_and_changes_only_the_spelling():
    """The point of not using `rebirth`: 600 was this agent's, and it stays 600.

    `rebirth` would return it to what the sovereign authored, which for an agent that had
    revised itself is the history worth keeping.
    """
    st = _aged_store()
    vocabulary.check(st, migrating=True)
    rows = bindings(st.query(
        "SELECT ?v WHERE { GRAPH <%s> { ?a sensing:slowSleepS ?v } }" % picks_graph("fern"), st.graphs_of(PUBLIC)))
    assert [r["v"] for r in rows] == ["600"]
    assert vocabulary.stale(st) == {}


def test_migration_moves_every_belief_not_only_the_one_looked_at():
    """A store half in one vocabulary is worse than one honestly stuck."""
    st = _aged_store()
    vocabulary.check(st, migrating=True)
    for query in ("sensing:slowSleepS 600", "market:hasEndowment 100",
                  "review:reviewIntervalS 300", "water:litresPerFraction 2.0"):
        predicate, value = query.split()
        rows = bindings(st.query(
            "SELECT ?v WHERE { GRAPH <%s> { ?a %s ?v } }" % (picks_graph("fern"), predicate), st.graphs_of(PUBLIC)))
        assert rows and rows[0]["v"].startswith(value.rstrip("0").rstrip(".")), predicate


def test_a_term_with_no_successor_is_refused_rather_than_dropped():
    """Deletion is not renaming, and guessing at it would lose a value silently."""
    st = _aged_store()
    st.update("INSERT DATA { GRAPH <%s> { <%sfern_agent> <%sabolishedS> 7 } }"
              % (picks_graph("fern"), OREXIS, OREXIS))
    with pytest.raises(SystemExit) as exc:
        vocabulary.check(st, migrating=True)
    assert "abolishedS" in str(exc.value)
    assert "no term of that name remains" in str(exc.value)


def test_public_graphs_are_never_the_agents_to_migrate():
    """They are replaced from the ratified files on every start, so a stale term in one would
    mean the files are wrong — and rewriting it here would hide that."""
    st = _aged_store()
    before = {g: len(st.get_graph(g)) for g in st.graphs_of(PUBLIC)}
    vocabulary.check(st, migrating=True)
    assert {g: len(st.get_graph(g)) for g in st.graphs_of(PUBLIC)} == before


# --- the boot path, end to end --------------------------------------------------------------

def test_an_aged_volume_refuses_to_open(tmp_path, monkeypatch):
    """The persistent case, which is the only one that ever happens in production.

    Written to disk and reopened, because the failure is about a volume surviving a restart —
    an in-memory store cannot be older than the code that made it.
    """
    monkeypatch.delenv("OREXIS_MIGRATE_BELIEFS", raising=False)
    path = str(tmp_path / "beliefs")
    world = WORLDS_ROOT / "simulation"

    genesis.open_belief_base(world, "fern", path)  # born, current
    aged = Store(genesis._belief_room(path))
    aged.put_graph(picks_graph("fern"), BEFORE_THE_SWEEP)  # and then the code moved on
    del aged

    with pytest.raises(SystemExit, match="slowSleepS"):
        genesis.open_belief_base(world, "fern", path)


def test_and_opens_when_asked_to_migrate(tmp_path, monkeypatch):
    path = str(tmp_path / "beliefs")
    world = WORLDS_ROOT / "simulation"

    genesis.open_belief_base(world, "fern", path)
    aged = Store(genesis._belief_room(path))
    aged.put_graph(picks_graph("fern"), BEFORE_THE_SWEEP)
    del aged

    monkeypatch.setenv("OREXIS_MIGRATE_BELIEFS", "1")
    st = genesis.open_belief_base(world, "fern", path)
    rows = bindings(st.query(
        "SELECT ?v WHERE { GRAPH <%s> { ?a sensing:slowSleepS ?v } }" % picks_graph("fern"), st.graphs_of(PUBLIC)))
    assert [r["v"] for r in rows] == ["600"]


def test_a_package_to_package_move_is_migrated_by_the_same_lookup():
    """The sensing rename is the case the kernel-only map could not see: every volume authored
    AFTER the great sweep holds `perception:slowSleepS` — an old spelling that never was a
    kernel one. The successor is found by local name whatever namespace the old spelling wore,
    so a term may move house twice and a volume from either era still follows."""
    st = genesis_store(world="simulation")
    st.put_graph(picks_graph("fern"), f"""
@prefix old: <http://example.org/orexis/perception#> .
@prefix orexis: <{OREXIS}> .

orexis:fern_agent old:fastSleepS 30 ; old:slowSleepS 600 ; old:readingGraceS 45 .
""")
    found = vocabulary.stale(st)
    assert picks_graph("fern") in found, "a post-sweep volume looked current"
    vocabulary.check(st, migrating=True)
    rows = bindings(st.query(
        "SELECT ?v WHERE { GRAPH <%s> { ?a sensing:slowSleepS ?v } }" % picks_graph("fern"), st.graphs_of(PUBLIC)))
    assert [r["v"] for r in rows] == ["600"]
    assert vocabulary.stale(st) == {}


# --- a move is data, and litter is dropped (found by the first live migration) ------------

def test_a_term_that_changed_namespace_and_name_still_migrates(tmp_path):
    """`renames` infers a successor by LOCAL NAME, which answers the historical direction —
    a term leaving `orexis:` for the package it belongs to — and answers nothing when the move
    goes the other way or renames as it goes. Both happened when the mind's states became
    kernel words: `desire:desires` became `orexis:holds` (no candidate at all) and
    `intention:outcome` had two candidates by local name with nothing able to choose. So a
    MOVE is data — a decision made once, written down, and preferred over the inference."""
    st = genesis_store(world="simulation")
    st.put_graph(picks_graph("fern"), f"""
@prefix old: <http://example.org/orexis/desire#> .
@prefix older: <http://example.org/orexis/intention#> .
<http://example.org/orexis/world/simulation#fern_agent>
    old:desires <http://example.org/orexis#r> ;
    older:outcome "dropped" .""")
    found = vocabulary.stale(st)
    successors = found[picks_graph("fern")]
    assert successors["http://example.org/orexis/desire#desires"] == OREXIS + "holds"
    assert successors["http://example.org/orexis/intention#outcome"] == PROGRESSION + "outcome"


def test_a_graph_nothing_declares_any_more_is_dropped(tmp_path, monkeypatch):
    """The ghost this found on the bench: a PUBLIC graph is replaced on every start by
    whatever declares it, so one that stops being declared is never cleared by anyone — it
    sits in the volume for ever holding facts in a spelling the code no longer speaks. The
    old `graph/desire` was exactly that after the bounds graph was named, and the first
    migration refused to guess what its `desire:desires` triples meant."""
    from agent_old import genesis

    st = genesis_store(world="simulation")
    ghost = "http://example.org/orexis/graph/desire"
    st.put_graph(ghost, "<http://x#a> <http://example.org/orexis/desire#desires> <http://x#b> .")
    assert ghost in st.graph_names()

    dropped = genesis.drop_ghost_graphs(st, "fern")
    assert ghost in dropped and ghost not in st.graph_names()
    # and nothing owned or declared went with it
    assert picks_graph("fern") not in dropped
    assert all(g not in dropped for g in st.graphs_of(PUBLIC))
