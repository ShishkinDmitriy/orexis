"""The sovereign's gate: what `orexis-validate` refuses that no shape can express.

Every other check in this project asks whether the world's own files hold together. These two
ask something the files cannot answer alone — whether the PACKAGES this checkout loads can
actually deliberate for the agents this world declares. Both became gates when the reflex was
deleted: each was a case where the search could not answer and handed the question to a second
road, and with the second road gone the honest place to catch them is before a society starts.

See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md.
"""

from __future__ import annotations

import pytest

from agent import genesis
from orexis_agent_deliberation.beliefs import Beliefs
from orexis_agent_deliberation.desire import Desires
from orexis_agent_progression.ontology import ACTIONS_GRAPH, ONTOLOGY_GRAPH
from onboarding.validate import deliberable, ids_are_unique

from conftest import genesis_store


def desires_of(st):
    """What `validate_world` hands the gate: one desire modality per agent with beliefs."""
    return {genesis.agent_id_of(p): Desires(Beliefs(st, genesis.agent_id_of(p)))
            for p in sorted(genesis.world_dir(_world(st)).glob(genesis.BELIEFS_GLOB))}


def _world(st) -> str:
    """Which world this store was built from — carried on the fixture, not asked of the store."""
    return st._orexis_world


def build(world: str, monkeypatch):
    monkeypatch.setenv("OREXIS_WORLD", world)
    st = genesis_store(world=world)
    st._orexis_world = world
    return st


# --- every shipped world passes it -------------------------------------------

@pytest.mark.parametrize("world", genesis.worlds())
def test_a_shipped_world_can_be_deliberated_for(world, monkeypatch):
    """The positive half, and the reason this is a test as well as a command.

    `orexis-validate <world>` is run by hand at the gates; this asks the same question of every
    world in the tree on every suite run, so a world that grows a lever nobody stated an effect
    for is caught by the same commit that grows it rather than by whoever next onboards.
    """
    st = build(world, monkeypatch)
    assert deliberable(st, desires_of(st)), \
        f"world/{world} holds an agent this build cannot deliberate for"


# --- and what it refuses -----------------------------------------------------

def test_a_lever_nothing_states_an_effect_for_is_refused(monkeypatch, caplog):
    """A means that puts a row on somebody's menu, and no package saying what it does.

    The search passes such a lever over — it cannot simulate what nothing describes — and then
    ranks the worlds it COULD build, which is a conclusion drawn from part of the menu. Fern
    buys its water: with Acquire's effect removed, a search over its menu sees Observe alone,
    finds correctly that looking does not wet soil, and reports that nothing helps. The plant
    stops bidding, and every module behaves exactly as written.

    The condition is created rather than found (#268 closed the last real one), by removing the
    shipped rule from the effect graph — which is how `tests/test_planning.py` reaches the same
    state from the runtime side.
    """
    st = build("simulation", monkeypatch)
    st.update("""DELETE { GRAPH <%s> { market:Acquiring sh:construct ?c } }
                 WHERE  { GRAPH <%s> { market:Acquiring sh:construct ?c } }"""
              % (ACTIONS_GRAPH, ACTIONS_GRAPH))

    assert not deliberable(st, desires_of(st)), \
        "a world whose water lever states no effect was allowed through"
    assert "Acquiring" in caplog.text and "what that DOES" in caplog.text, \
        "the refusal must name the lever — a gate that says only 'no' is a gate nobody can act on"


def test_a_stake_nothing_can_measure_is_refused(monkeypatch, caplog):
    """A want with no measure ranks every possible world alike, and a search over worlds that
    all score the same concludes — confidently — that nothing helps.

    Sensing declares its measure for the KIND `sosa:ObservableProperty`, so the way to hold a
    stake nothing measures is to hold one in a property that is not one. Untyping the property
    is the smallest fixture that produces it and it is not artificial: a domain package
    shipping a property it forgot to type would land exactly here, with every plant in the
    world silently unrankable.
    """
    st = build("simulation", monkeypatch)
    st.update("""DELETE { GRAPH <%s> { ?p a sosa:ObservableProperty } }
                 WHERE  { GRAPH <%s> { ?p a sosa:ObservableProperty } }"""
              % (ONTOLOGY_GRAPH, ONTOLOGY_GRAPH))

    assert not deliberable(st, desires_of(st)), \
        "a world whose stakes nothing can weigh was allowed through"
    assert "measure" in caplog.text, "the refusal must say which half of the gate refused"


def test_the_gate_asks_the_packages_and_never_builds_an_agent(monkeypatch):
    """Why the measure question is asked of a CLASS.

    An `Agent` refuses to construct without the series credentials `orexis-influx` mints — and
    onboarding mints them AFTER validating, so a gate that built one to interrogate it would
    require the thing it exists to run before. The class-level roll-call is what avoids that,
    and this is the assertion that says the road stays open: with no credentials in the
    environment at all, the gate still answers.
    """
    monkeypatch.delenv("INFLUX_BUCKET", raising=False)
    monkeypatch.delenv("INFLUX_TOKEN", raising=False)
    st = build("simulation", monkeypatch)
    assert deliberable(st, desires_of(st))


# --- an id is unique or it is not an id (#432) -------------------------------------------

def _clone_agent_under_the_same_id(st, agent_id: str) -> str:
    """Give the world a second `ag:Agent` answering to an id another one already holds."""
    from orexis_agent_progression.ontology import AG, WORLD_GRAPH

    twin = f"http://example.org/orexis/world/test#{agent_id}_twin"
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
      <{twin}> a <{AG}Agent> ; <{AG}localId> "{agent_id}" ;
               <{AG}hasCapability> <http://example.org/orexis/reporting#Storing> . }} }}""")
    return twin


def test_two_agents_may_not_answer_to_one_id(monkeypatch, caplog):
    """SHACL cannot ask this — `sh:maxCount 1` is cardinality per agent, and there is no
    cross-node uniqueness constraint — so the sovereign asks it where the world is entire.

    What rides on it is a shared broker principal, a shared bucket and a shared volume, since
    the id is the wire name for all three."""
    st = genesis_store(world="simulation")
    assert ids_are_unique(st), "the shipped world is the control, and it must pass"

    _clone_agent_under_the_same_id(st, "fern")
    with caplog.at_level("ERROR"):
        assert not ids_are_unique(st), "two agents share an id and the gate let it through"
    assert "fern" in caplog.text


def test_load_self_refuses_rather_than_picking_one(monkeypatch):
    """The same refusal at the other end, for a volume built before the gate existed.

    Rows arrive one per (agent x capability), so the failure this replaces was silent: the
    first node's uri and subject, holding BOTH agents' capabilities.
    """
    from agent.world import WorldError, load_self

    st = genesis_store(world="simulation")
    me = load_self(st.query, "fern")
    assert me.agent_id == "fern"

    _clone_agent_under_the_same_id(st, "fern")
    with pytest.raises(WorldError, match="answer to localId"):
        load_self(st.query, "fern")
