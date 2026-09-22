"""Scopes: which predicates are joined by what the shipped rules actually do (#565).

Two wants in different scopes cannot contradict, because no action of one writes a fact
the other reads — which is what would make it safe to plan them apart, one cone each, and to
concatenate their plans. This file measures whether any shipped want is in that position. It is
not: every world's vocabulary is ONE scope. The measurement is the point, and it is why
one cone per scope has nothing yet to split.
"""

from __future__ import annotations

import pytest

from conftest import genesis_store
from orexis_agent_deliberation import relevance as R
from orexis_agent_deliberation.scope_actions import scopes, spans
from orexis_agent_deliberation.planner import Planner
from orexis_agent_progression.ontology import PUBLIC

WORLDS = ("loner", "simulation", "courier", "hanoi")


def _parts(store):
    return scopes(R.actions_of(store.reader(PUBLIC)), R.rule_edges())


@pytest.mark.parametrize("world", WORLDS)
def test_every_shipped_world_is_one_scope(world):
    """The measured claim, before any mechanism rests on it: nothing a shipped world does
    separates its vocabulary. Ninety-odd predicates, one scope — whether the derivations
    are counted or the actions are taken alone, since the actions alone already join the
    market's plumbing to sensing's readings through the observation every effect predicts.

    A world that broke this would be the first one worth planning as several cones, and would
    turn item 3 of #565 from a hypothesis into a measurement."""
    store = genesis_store(world=world)
    parts = _parts(store)
    assert len(parts) == 1, [sorted(p)[:4] for p in parts]
    assert len(parts[0]) > 50, "and it is the whole vocabulary, not a lone pair"
    actions_alone = scopes(R.actions_of(store.reader(PUBLIC)))
    assert len(actions_alone) == 1, "the actions join it without the derivations' help"


@pytest.mark.parametrize("world", ("loner", "simulation", "courier"))
def test_every_shipped_want_falls_inside_one_scope(world, monkeypatch):
    """The claim as each WANT sees it: a want's view — what it reads, plus what the actions
    relevant to it read and write — lies inside one scope, so its plan is one cone. True
    for every want every shipped agent holds, and true trivially while the vocabulary is one
    scope; the test below is what keeps this one honest."""
    monkeypatch.setenv("OREXIS_WORLD", world)
    store = genesis_store(world=world)
    parts = _parts(store)
    #  WHOEVER THE WORLD AUTHORED, asked of the files rather than listed: a roll-call that
    #  stops matching measures nothing and says nothing, which is the failure this repo's own
    #  conftest exists to catch.
    from agent import genesis
    monkeypatch.setenv("INFLUX_BUCKET", "test-scopes")
    monkeypatch.setenv("INFLUX_TOKEN", "test-token-scopes")
    agents = sorted(p.stem for p in (genesis.world_dir(world) / "beliefs").glob("*.ttl"))
    assert agents, f"{world} authored no agent — the glob stopped matching"
    seen = 0
    for agent_id in agents:
        #  A PLAIN AGENT, not the wired builder: a world whose agent holds no bus has no
        #  transport module for the builder's conveniences to find, and nothing here speaks
        #  to a wire — only to `considering` and the planner's view.
        from agent import runtime
        st = genesis_store(world=world)
        genesis.classify_kernel_graphs(st, agent_id)
        agent = runtime.Agent(agent_id, st=st)
        planner = Planner(agent, agent.me)
        for want in agent.wants():
            planner._begin(want)
            view = planner._view_of(want)
            seen += 1
            assert spans(view, parts) == 1, \
                f"{agent_id}'s {want.uri.rsplit('#', 1)[-1]} spans several scopes"
            planner.reset()
    assert seen, "no want was measured — the roll-call stopped matching"


def test_a_vocabulary_nothing_joins_falls_apart():
    """The teeth. The claim above passes on every shipped world and would pass just as loudly
    if this computation returned one scope for everything, so it is asked of two actions
    that share no predicate at all: two scopes, and a view of one of them spans one."""
    actions = {"urn:a": (frozenset({"urn:reads:x"}), frozenset({"urn:writes:x"})),
               "urn:b": (frozenset({"urn:reads:y"}), frozenset({"urn:writes:y"}))}
    parts = scopes(actions)
    assert len(parts) == 2
    assert {frozenset({"urn:reads:x", "urn:writes:x"}), frozenset({"urn:reads:y", "urn:writes:y"})} \
        == set(parts)
    assert spans(frozenset({"urn:reads:x"}), parts) == 1
    assert spans(frozenset({"urn:reads:x", "urn:writes:y"}), parts) == 2, \
        "a want reading both halves would be planned as two cones"


def test_one_action_across_two_halves_joins_them():
    """And what a coupling looks like: a heater that reads the climate and writes the soil.
    The greenhouse's case, in miniature — two vocabularies are two scopes until one lever
    touches both, which is why independence is proven here and never read off namespaces."""
    actions = {"urn:a": (frozenset({"urn:climate"}), frozenset({"urn:climate"})),
               "urn:b": (frozenset({"urn:soil"}), frozenset({"urn:soil"}))}
    assert len(scopes(actions)) == 2
    coupled = dict(actions, **{"urn:heater": (frozenset({"urn:climate"}), frozenset({"urn:soil"}))})
    assert len(scopes(coupled)) == 1, "one lever across both makes one scope"


def test_an_unreadable_lever_joins_everything():
    """A lever whose reads or writes could not be read from its text might touch any predicate,
    so it cannot be proven not to touch both halves. It joins them, which is the safe direction:
    a scope wrongly split would let two plans contradict each other."""
    actions = {"urn:a": (frozenset({"urn:x"}), frozenset({"urn:x"})),
               "urn:b": (frozenset({"urn:y"}), frozenset({"urn:y"}))}
    assert len(scopes(actions)) == 2
    with_blind = dict(actions, **{"urn:blind": (frozenset({"urn:x"}), R.ANYTHING)})
    assert len(scopes(with_blind)) == 1
    assert spans(R.ANYTHING, scopes(actions)) == 2, "and an unreadable view spans all of them"
