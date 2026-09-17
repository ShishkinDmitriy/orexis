"""Every node an agent holds is in exactly one collection — the gate the split was missing.

THIS IS THE TEST THAT WOULD HAVE CAUGHT IT. `Wants` asked `a orexis:Want` and `Desires` asked
`orexis:bindsWhen orexis:Always`, which are two different partitions assumed to be one — so a
node typed a desire and bound `AtEnd` fell between them, and three of the four shipped worlds
had their single desire, the whole point of the world, in NEITHER. Nothing failed, because
falling out of a collection is an empty result and an empty result is not an error.

The invariant is one sentence and does not care how the kinds are told apart: whatever an agent
holds, exactly one collection answers for it. See
knowledge/decisions/a-kind-is-a-type-not-a-binding.md.
"""

from __future__ import annotations

import pytest

from orexis_agent_deliberation.beliefs import Beliefs
from orexis_agent_deliberation.desires import Desires
from orexis_agent_deliberation.wants import Wants
from orexis_agent_progression.store import bindings

from conftest import genesis_store

#  One agent per shipped world that authors something to want, and they are deliberately
#  different shapes: three ratify a WANT directly — standing, authored, handed to a search —
#  and the fourth's are all deduced desires with wants derived under them at runtime.
WORLDS = [("tower", "mover"), ("courier", "courier"), ("hanoi", "hanoi"), ("loner", "gardener")]


def _held(world: str, agent_id: str):
    beliefs = Beliefs(genesis_store(world=world), agent_id)
    desires, wants = Desires(beliefs), Wants(beliefs, beliefs.agent_uri, agent_id)
    held = {r["w"] for r in bindings(desires.query_union(
        f"SELECT ?w WHERE {{ <{beliefs.agent_uri}> orexis:holds ?w . ?w a ?t . "
        f"FILTER(?t IN (orexis:Desire, orexis:Want)) }}"))}
    return held, {w.uri for w in wants.find_all()}, {d.uri for d in desires.find_all()}


@pytest.mark.parametrize("world,agent_id", WORLDS)
def test_everything_held_is_in_exactly_one_collection(world, agent_id, monkeypatch):
    monkeypatch.setenv("OREXIS_WORLD", world)
    held, wants, desires = _held(world, agent_id)
    assert held, f"{world}/{agent_id} holds nothing to want — the case would pass vacuously"

    orphans = held - wants - desires
    assert not orphans, (
        f"{world}/{agent_id}: held by the agent and answered for by NEITHER collection: "
        f"{sorted(orphans)} — which is how three worlds lost their only desire")
    both = held & wants & desires
    assert not both, (
        f"{world}/{agent_id}: in BOTH collections: {sorted(both)} — the kinds are disjoint, so "
        f"a node in both means a writer stated two types or the subclass axis is back")


@pytest.mark.parametrize("world,agent_id", WORLDS)
def test_a_desire_states_no_binding_and_a_want_states_one(world, agent_id, monkeypatch):
    """The other half, asked of the vocabulary rather than of the collections. A desire holds at
    every instant, so a binding on one is a type's job in a property's clothes — which is what
    let a node be a desire by type and a want by binding at once."""
    monkeypatch.setenv("OREXIS_WORLD", world)
    beliefs = Beliefs(genesis_store(world=world), agent_id)

    loose = bindings(Desires(beliefs).query_union(
        "SELECT ?d WHERE { ?d a orexis:Desire ; orexis:bindsWhen ?b }"))
    assert not loose, f"a desire states when it binds: {[r['d'] for r in loose]}"

    unbound = bindings(Desires(beliefs).query_union(
        f"SELECT ?w WHERE {{ <{beliefs.agent_uri}> orexis:holds ?w . ?w a orexis:Want . "
        f"FILTER NOT EXISTS {{ ?w orexis:bindsWhen ?b }} }}"))
    assert not unbound, f"a want defaults its binding: {[r['w'] for r in unbound]}"
