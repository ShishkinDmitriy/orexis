"""Deliberation: the whether, extracted — and provably no longer the bidder's.

Phase 4 of knowledge/decisions/an-intention-is-an-amortised-deliberation.md, and the end of the
roadmap it opened. The welded chain (below the aim → pursue; cannot see → look) is now the
Reflex member of a family, asked for through `agent.provider` — so the round tests hold
untouched, and the one NEW thing to prove is the seam itself: silence the deliberator and a
thirsty bidder with a fresh reading in hand submits nothing, because the whether genuinely
moved. That test is the property an LLM member will stand on.
"""

from __future__ import annotations

import pytest

from agent.world import load_self
from packages.capability.deliberation import menu_of
from packages.capability.deliberation.module import ACQUIRE, OBSERVE
from packages.capability.deliberation.terms import REFLEX

from conftest import MOISTURE, TEMPERATURE, build_agent, genesis_store


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


def decider_of(agent):
    return next(m for m in agent.modules if m.name == "deliberation")


def market_of(agent):
    return agent.me.markets[0]


# --- who decides, and who has nothing to decide -----------------------------

def test_a_stake_and_a_lever_grant_reflex():
    """The same premise as keeping, deliberately: deciding and committing are meaningful under
    exactly the same conditions. They stay two capabilities because the replaceable parts
    differ — how commitments are kept could change without changing how decisions are reached,
    and the other way round is the case the family exists for."""
    q = genesis_store().query
    assert REFLEX in load_self(q, "fern").capabilities
    assert REFLEX not in load_self(q, "supplier").capabilities
    assert REFLEX not in load_self(genesis_store(world="sensing").query, "fern").capabilities


# --- the reflex, which is the old chain verbatim ----------------------------

def test_not_seeing_means_look(make):
    assert decider_of(make("fern")).propose(MOISTURE, None) == OBSERVE


def test_below_the_aim_means_pursue_and_above_means_nothing(make):
    """Fern aims at 0.55. The whole reflex is the gap's sign against the AIM — the pick, not
    the region's edge, because pursuing only past the band would leave the agent permanently
    short of where it decided to sit."""
    decider = decider_of(make("fern"))
    assert decider.propose(MOISTURE, 0.10) == ACQUIRE
    assert decider.propose(MOISTURE, 0.54) == ACQUIRE
    assert decider.propose(MOISTURE, 0.55) is None
    assert decider.propose(MOISTURE, 0.80) is None


def test_a_property_with_no_aim_is_not_pursued(make):
    """Fern holds a temperature region and picked no temperature aim: an agent that picked no
    point has decided not to steer that property, and the reflex honours the decision rather
    than inventing a point to pursue toward. None is a decision, not an absence of one."""
    assert decider_of(make("fern")).propose(TEMPERATURE, 5.0) is None


# --- the seam is load-bearing: the whether is not the bidder's --------------

def test_silencing_the_deliberator_silences_the_bidder(make, monkeypatch):
    """The proof of the extraction, and the property a model member stands on.

    A thirsty fern with a fresh reading in hand — everything the old welded bidder needed to
    bid — submits NOTHING when its deliberator says nothing, because the whether genuinely
    moved out of the bidder. Before this phase, no test could have made this fail.
    """
    fern = make("fern", genesis_store({"fern": 0.10}))
    market = market_of(fern)
    monkeypatch.setattr(decider_of(fern), "propose", lambda prop, value: None)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.sent.to(f"{market.bid_topic}/fern") == []


def test_the_deliberator_choosing_not_to_look_is_honoured(make, monkeypatch):
    """The other whether: with no fresh reading, the reflex says look — and a member that said
    otherwise (a model judging the last reading close enough to certain) is obeyed, not
    second-guessed. The bidder neither senses nor waits; the round simply passes."""
    fern = make("fern")  # no reading at all
    market = market_of(fern)
    monkeypatch.setattr(decider_of(fern), "propose", lambda prop, value: None)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.bidding().pending is None
    # and no observe intention was adopted — nothing committed to a wait nobody is waiting on
    keeper = next(m for m in fern.modules if m.name == "intention")
    assert keeper.standing() == []


def test_with_the_reflex_in_place_the_round_runs_exactly_as_before(make):
    """The extraction carries the old behaviour: thirsty bids, sated cedes. The round tests
    hold this in the large; this is the same fact stated where the seam lives."""
    thirsty = make("fern", genesis_store({"fern": 0.10}))
    thirsty.deliver(market_of(thirsty).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert len(thirsty.sent.to(f"{market_of(thirsty).bid_topic}/fern")) == 1

    sated = make("fern", genesis_store({"fern": 0.80}))
    sated.deliver(market_of(sated).offer_topic, {"auction_id": "r2", "closes_in_s": 3})
    assert sated.sent.to(f"{market_of(sated).bid_topic}/fern") == []


# --- the direction is the graph's, not the code's (#127) --------------------

def test_the_sign_is_read_off_the_domain_not_hardcoded(make):
    """Flip the domain's statement — say water LOWERS moisture — and the reflex pursues on the
    other side of the aim, with no code change. This is the whole of what stating the direction
    bought: a heater against a cold snap is the same rule, and the old `value < aim` was the
    one piece of "buy water to raise moisture" written nowhere in any graph."""
    from agent.ontology import ONTOLOGY_GRAPH

    ds = genesis_store()
    ds.update(f"""
        PREFIX market: <http://example.org/agora/market#>
        DELETE {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?t market:direction market:Raises }} }}
        INSERT {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?t market:direction market:Lowers }} }}
        WHERE  {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?t market:direction market:Raises }} }}""")
    decider = decider_of(build_agent_quiet(make, ds))
    assert decider.propose(MOISTURE, 0.10) is None      # below the aim helps nothing now
    assert decider.propose(MOISTURE, 0.80) == ACQUIRE   # above it is what the lot relieves


def test_no_stated_direction_means_no_pursuit(make):
    """Refusing is honest where guessing would be the hardcoded sign sneaking back in as a
    default. The shape refuses such a domain at the gate anyway; this is the runtime honouring
    the same fact if it ever meets it."""
    from agent.ontology import ONTOLOGY_GRAPH

    ds = genesis_store()
    ds.update(f"""
        PREFIX market: <http://example.org/agora/market#>
        DELETE {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?t market:direction ?d }} }}
        WHERE  {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?t market:direction ?d }} }}""")
    decider = decider_of(build_agent_quiet(make, ds))
    assert decider.propose(MOISTURE, 0.10) is None


def build_agent_quiet(make, ds):
    return make("fern", ds)


# --- the menu: what I could do, derived -------------------------------------

def test_the_menu_is_derived_from_the_graph(make):
    """The Consulting member's prompt substrate, checkable before that member exists: for this
    agent — these properties, these levers, these directions. Nothing here was written as a
    menu; every row is a join over facts that exist for their own reasons."""
    rows = menu_of(genesis_store().query, FERN)
    as_tuples = {(r.means.rsplit("#", 1)[-1], r.observed_property.rsplit("#", 1)[-1],
                  r.direction.rsplit("#", 1)[-1] if r.direction else None) for r in rows}
    assert as_tuples == {
        ("Observe", "SoilMoisture", None),       # look through the probe
        ("Observe", "AirTemperature", None),     # look through the thermometer
        ("Acquire", "SoilMoisture", "Raises"),   # raise it through the market
    }
    # and the row that is NOT there is the finding: fern wants a temperature it can see and
    # cannot move — a want with no lever, which is legitimate and now legible.
    assert not any(r.means.endswith("Acquire") and "Temperature" in r.observed_property
                   for r in rows)


def test_an_agent_with_no_desires_has_an_empty_menu(make):
    """The supplier holds levers everywhere and wants nothing — no rows, because an affordance
    is a move toward an end, not a list of what the wiring physically allows."""
    assert menu_of(genesis_store().query, "http://example.org/agora#supplier") == []


FERN = "http://example.org/agora#fern_agent"
