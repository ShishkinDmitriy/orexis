"""An agent re-picking a belief — the room it has, the guards, and what it remembers.

Nothing is mocked. The store is a real belief base, the shapes are the real shapes, the rule is
the SPARQL the perception package ships, and the path is the one a deployed agent runs when it
arises. See knowledge/decisions/a-belief-is-a-pick-within-a-range.md.
"""

from __future__ import annotations

import pytest

from agent import genesis
from agent.ontology import (SENSED_GRAPH, WORLD_GRAPH, beliefs_graph, evidence_graph,
                            revisions_graph, term)
from agent.review import Range, world_ranges
from agent.store import bindings
from agent.summary import RING, Summaries

from conftest import WORLDS_ROOT, build_agent, genesis_store

SLOW = term("slowSleepS")
AUTHORED = 600.0   # fern's first pick
COMMITTED = 600.0  # and the floor it commits to
CEILING = 900.0    # the constitutional ceiling it may relax to


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", monkeypatch=monkeypatch)


def feed(agent, values, sensor=None):
    """Put readings through the ingest path, then close the window as an arising would."""
    sensor = sensor or agent.subscribing().sensors[0]
    for value in values:
        agent.reviewer.summaries.record(sensor.subject, sensor.observes, value)
    agent.reviewer.summaries.roll()
    agent.reviewer.publish_evidence(agent.reviewer.ranges())
    return agent.reviewer


def window(agent) -> int:
    rows = bindings(agent.store.query(
        "SELECT ?n WHERE { GRAPH ?g { ag:PerceptionCapability ag:reviewWindow ?n } }"))
    return int(rows[0]["n"])


# --- what may move, and how far ------------------------------------------------------------

def test_a_revisable_term_is_discovered_from_the_t_box_not_from_python(fern):
    """No registry and no import: the reviewer asks the merged ontology what may be re-picked,
    so a capability nobody here has read is reviewable on the same terms as this one."""
    assert SLOW in world_ranges(fern.store.query)


def test_the_world_range_comes_from_the_constitution(fern):
    room = world_ranges(fern.store.query)[SLOW]
    assert (room.floor, room.ceiling) == (10.0, 900.0)


def test_the_agents_own_commitment_narrows_it(fern):
    """The author's job is to constrain, not to guess. 10..900 is what any agent may do; 600..900
    is what this one will."""
    assert (fern.reviewer.ranges()[SLOW].floor,
            fern.reviewer.ranges()[SLOW].ceiling) == (COMMITTED, CEILING)


def test_the_first_pick_is_not_a_bound(fern):
    """The whole correction. What genesis wrote is a value inside the range, not an end of it —
    so a review may move below it when its own commitment allows."""
    assert fern.reviewer.current(SLOW) == AUTHORED
    room = fern.reviewer.ranges()[SLOW]
    assert room.floor <= AUTHORED <= room.ceiling


def test_a_commitment_leaving_no_room_fixes_the_figure():
    """How an author says 'not up for review' — by leaving nowhere to go, rather than a flag."""
    assert Range(SLOW, 900.0, 900.0).fixed
    assert not Range(SLOW, 600.0, 900.0).fixed


def test_a_commitment_never_widens_what_the_world_allows(fern):
    """A commitment is intersected, so one looser than the constitution is the constitution."""
    fern.store.update(f"""
DELETE {{ GRAPH <{beliefs_graph('fern')}> {{ ?c ag:notAbove ?a }} }}
INSERT {{ GRAPH <{beliefs_graph('fern')}> {{ ?c ag:notAbove 99999 }} }}
WHERE  {{ GRAPH <{beliefs_graph('fern')}> {{ ?c ag:onTerm <{SLOW}> ; ag:notAbove ?a }} }}""")
    assert fern.reviewer.ranges()[SLOW].ceiling == CEILING


# --- what the shipped rule concludes ---------------------------------------------------------

def test_a_thin_window_proposes_nothing(fern):
    """Two identical readings are a coincidence. A rule with nothing to say returns no rows —
    an unsatisfied pattern rather than a sentinel."""
    feed(fern, [0.5] * 3)
    assert fern.reviewer.proposals() == []


def test_a_steady_probe_relaxes_toward_the_ceiling(fern):
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    assert fern.reviewer.proposals() == [(SLOW, CEILING)]


def test_a_frozen_probe_tightens_instead_of_relaxing(fern):
    """The case the obvious rule gets exactly backwards: an instrument that has not moved to the
    last bit is likelier broken than the world it measures is perfectly still."""
    feed(fern, [0.412] * (window(fern) + 2))
    assert fern.reviewer.proposals() == [(SLOW, COMMITTED)]


def test_a_moving_probe_tightens(fern):
    feed(fern, [0.3, 0.7] * (window(fern) // 2 + 1))
    assert fern.reviewer.proposals() == [(SLOW, COMMITTED)]


# --- the asymmetry, tested on the rule's own aggregation ---------------------------------------

def _evidence(agent, spreads):
    """Seed one Evidence node per spread, as several sensors would produce.

    Written straight into the evidence graph because no ratified world gives one agent two
    sensors yet — this exercises the shipped rule's aggregation rather than a stand-in for it.
    """
    agent.reviewer.publish_evidence(agent.reviewer.ranges())
    n = window(agent) + 2
    agent.store.update("INSERT DATA { GRAPH <%s> { %s } }" % (
        evidence_graph(agent.id),
        "".join(f'[] a ag:Evidence ; ag:sampleSpread "{s:.6f}"^^xsd:decimal ; '
                f'ag:sampleCount {n} . ' for s in spreads)))


def test_relaxing_needs_every_sensor_to_agree(fern):
    _evidence(fern, [0.001, 0.001])
    assert fern.reviewer.proposals() == [(SLOW, CEILING)]


def test_one_moving_sensor_is_enough_to_tighten(fern):
    """The cost of watching a still pot too closely is some battery; the cost of the reverse is
    a dead plant. So relaxing needs unanimity and tightening needs one dissenter."""
    _evidence(fern, [0.001, 0.9])
    assert fern.reviewer.proposals() == [(SLOW, COMMITTED)]


def test_one_frozen_sensor_is_enough_to_tighten(fern):
    _evidence(fern, [0.001, 0.0])
    assert fern.reviewer.proposals() == [(SLOW, COMMITTED)]


# --- applying, refusing, reverting -------------------------------------------------------------

def test_a_revision_moves_the_belief_and_the_module_takes_it_up(fern):
    subscribing = fern.subscribing()
    assert subscribing.beliefs.slow_sleep_s == AUTHORED

    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewer.review()

    assert fern.reviewer.current(SLOW) == CEILING
    # Re-read, not patched: the module holds a frozen dataclass and must have refreshed it.
    assert subscribing.beliefs.slow_sleep_s == CEILING


def test_a_value_outside_the_range_is_refused_not_clamped(fern):
    """A rule proposing out of range is wrong about something, and quietly correcting it would
    hide that."""
    room = fern.reviewer.ranges()[SLOW]
    assert not fern.reviewer.settle(room, 2000.0)
    assert fern.reviewer.current(SLOW) == AUTHORED
    assert fern.reviewer.refused == 1


def test_a_revision_the_shapes_refuse_is_put_back(fern):
    """Legitimacy is the boot check re-run, so a belief the agent could not have started with is
    one it cannot reach by changing its mind either."""
    from agent.validate import validate_agent

    assert not fern.reviewer.settle(Range(SLOW, 0.0, 5.0), 1.0)  # under the constitutional floor
    assert fern.reviewer.current(SLOW) == AUTHORED
    assert fern.reviewer.refused == 1
    # And it is still startable, which is what reverting exists to preserve.
    validate_agent(fern.store, fern.id, fern.me.uri, fern.me.capabilities)


# --- memory, which is also the schedule ---------------------------------------------------------

def test_a_decision_to_change_nothing_is_recorded(fern):
    """Without it the same question is re-argued at every arising, and the agent can never
    notice it has declined eleven times and the problem is elsewhere."""
    feed(fern, [0.412] * (window(fern) + 2))  # frozen -> proposes what it already holds
    fern.reviewer.review()
    assert fern.reviewer.declined == 1
    assert [r["outcome"] for r in _decisions(fern)] == ["declined"]


def test_a_settled_term_is_not_re_argued_before_it_is_due(fern):
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewer.review()
    taken = fern.reviewer.revisions
    assert taken == 1

    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewer.review()
    assert fern.reviewer.revisions == taken  # still due later, so nothing was re-decided
    assert len(_decisions(fern)) == 1


def test_every_decision_says_why_and_when_to_look_again(fern):
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewer.review()
    recorded = _decisions(fern)[0]
    assert recorded["term"] == SLOW
    assert float(recorded["from"]) == AUTHORED and float(recorded["to"]) == CEILING
    assert recorded["why"] and recorded["due"] > recorded["at"]


def test_the_next_arising_is_never_sooner_than_the_stated_floor(fern):
    assert fern.reviewer.interval_s == 300  # what fern's beliefs state
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewer.review()
    assert fern.reviewer.next_wake_s() >= 300


# --- the write boundary ----------------------------------------------------------------------

def test_a_review_writes_only_its_own_beliefs_and_never_the_world_or_the_record(fern):
    """The graph types made load-bearing. A review reads the world as constraint and `:sensed`
    as evidence, and changes neither — which is what the tripartite split is FOR."""
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    before = (fern.store.get_graph(WORLD_GRAPH), fern.store.get_graph(SENSED_GRAPH))

    fern.reviewer.review()

    assert fern.reviewer.current(SLOW) == CEILING, "it should have changed something"
    assert (fern.store.get_graph(WORLD_GRAPH), fern.store.get_graph(SENSED_GRAPH)) == before


def test_a_review_touches_no_other_agents_beliefs(fern):
    """It cannot reach one — but the fixture births every agent in the world, so unlike a
    deployed store this one actually contains somebody else's to reach for."""
    other = fern.store.get_graph(beliefs_graph("tomato"))
    feed(fern, [0.500, 0.502] * (window(fern) // 2 + 1))
    fern.reviewer.review()
    assert fern.store.get_graph(beliefs_graph("tomato")) == other


def _decisions(agent) -> list[dict]:
    return bindings(agent.store.query(f"""
SELECT ?term ?from ?to ?why ?outcome ?at ?due WHERE {{ GRAPH <{revisions_graph(agent.id)}> {{
  ?r a ag:Revision ; ag:revisedTerm ?term ; ag:fromValue ?from ; ag:toValue ?to ;
     ag:becauseOf ?why ; ag:outcome ?outcome ; ag:atTime ?at ; ag:dueAt ?due }} }}"""))


def test_an_agent_that_states_no_interval_never_arises(monkeypatch):
    """Absence is the decision. Nothing is scheduled, so nothing can drift."""
    store = genesis_store()
    store.update("DELETE WHERE { GRAPH <%s> { ?s ag:reviewIntervalS ?o } }" % beliefs_graph("fern"))
    agent = build_agent("fern", st=store, monkeypatch=monkeypatch)
    assert agent.reviewer.interval_s == 0
    agent.reviewer.start()
    assert agent.reviewer._timer is None
