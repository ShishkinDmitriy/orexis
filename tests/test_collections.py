"""Every node an agent holds is in exactly one collection — the gate the split was missing.

THIS IS THE TEST THAT WOULD HAVE CAUGHT IT. The wants read asked `a orexis:Want` and `Desires` asked
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
from orexis_agent_deliberation.desires import Desires, find_desires
from orexis_agent_deliberation.wants import find_wants
from orexis_agent_progression.store import bindings

from conftest import genesis_store

#  One agent per shipped world that authors something to want, and they are deliberately
#  different shapes: three ratify a WANT directly — standing, authored, handed to a search —
#  and the fourth's are all deduced desires with wants derived under them at runtime.
WORLDS = [("tower", "mover"), ("courier", "courier"), ("hanoi", "hanoi"), ("loner", "gardener")]


def _held(world: str, agent_id: str):
    beliefs = Beliefs(genesis_store(world=world), agent_id)
    desires = Desires(beliefs)
    held = {r["w"] for r in bindings(desires.query(
        f"SELECT ?w WHERE {{ <{beliefs.agent_uri}> orexis:holds ?w . ?w a ?t . "
        f"FILTER(?t IN (orexis:Desire, orexis:Want)) }}"))}
    return held, {w.uri for w in find_wants(beliefs)}, {d.uri for d in find_desires(desires)}


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
def test_nothing_states_a_time_semantics_of_its_own(world, agent_id, monkeypatch):
    """The other half, asked of the vocabulary rather than of the collections.

    There were four bindings and a property to carry one, and every one of them said something
    already written down: the KIND is the type, the INTERVAL is the graph's period, the INSTANT
    is `orexis:holdsAt`, and the FAMILY — which is what a reader filtering on them actually
    wanted — is the graph's classification (#681). A node stating its own time semantics beside
    those is a second place for one fact, which is how a want and a desire came to disagree
    about which they were."""
    monkeypatch.setenv("OREXIS_WORLD", world)
    beliefs = Beliefs(genesis_store(world=world), agent_id)

    loose = bindings(Desires(beliefs).query(
        "SELECT ?n ?p WHERE { ?n ?p ?o . VALUES ?p { orexis:bindsWhen } }"))
    assert not loose, f"the binding is back: {[(r['n'], r['p']) for r in loose]}"
