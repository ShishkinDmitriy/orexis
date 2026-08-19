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
    and the other way round is the case the family exists for.

    Both flavours of lever now demonstrate the premise: fern's is a market position, the
    supplier's the valves it always held — which became a lever's other half the day the
    stake arrived (arc 2). The levers-without-stake counterexample the supplier used to be
    died with that stake, so the missing-stake half is shown by taking it away."""
    q = genesis_store().query
    assert REFLEX in load_self(q, "fern").capabilities
    assert REFLEX in load_self(q, "supplier").capabilities
    assert REFLEX not in load_self(genesis_store(world="sensing").query, "fern").capabilities

    from agent import genesis, loader
    from agent.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH

    st = genesis_store()
    st.update(f"""DELETE WHERE {{ GRAPH <{WORLD_GRAPH}> {{
        <http://example.org/agora/world/simulation#supplier>
            <http://example.org/agora#actsFor> ?o }} }}""")
    st.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        st.update(genesis.substitute(rule.read_text(), st))
    assert REFLEX not in load_self(st.query, "supplier").capabilities, \
        "means without wants have nothing to decide — the premise needs both halves"


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


def test_the_dealers_menu_gained_its_lever(make):
    """The supplier across the arcs: it wants its barrel full (arc 2), can SEE the level
    (arc 1), and — since the city exists (arc 4) — holds the LEVER: bidding in the refill
    venue, whose winnings physically reach its barrel through the city's pipe, priced in
    StoredLitres, raising it. This test guarded the seen-but-unmovable reading while that
    was the honest one; the row it waited for is derived now, direction and all, and the
    Observe row stands beside it exactly as a fern's does."""
    rows = menu_of(genesis_store().query,
                   "http://example.org/agora/world/simulation#supplier")
    assert [(r.means.rsplit("#", 1)[-1], r.observed_property.rsplit("#", 1)[-1],
             (r.direction or "").rsplit("#", 1)[-1] or None)
            for r in rows if r.is_chosen] == [("Acquire", "StoredLitres", "Raises"),
                                              ("Observe", "StoredLitres", None)]
    #  And beside them, since #218, what the dealer HONOURS: claims presented against the
    #  venue it hosts are redeemed through its valves — one row per lever, never a proposal.
    honoured = [r for r in rows if not r.is_chosen]
    assert {r.means.rsplit("#", 1)[-1] for r in honoured} == {"Apply"}
    assert len(honoured) == 3, "one duty per valve it holds for its buyers"


FERN = "http://example.org/agora/world/simulation#fern_agent"


def test_a_market_no_valve_connects_to_your_pot_is_no_lever(make):
    """The Acquire row is DEDUCED along the plumbing (#127, strengthened): the market's host
    holds an actuator, the actuator is plumbed to MY pot, so opening it puts the good where I
    am — and only the physics atom (water raises moisture) is stated, once, by the domain.
    Cut the pipe and the row vanishes: fern still bids in a market, the domain still prices
    moisture, but a delivery that cannot reach your pot is, for you, no lever at all — and
    the reflex must not be offered a move that moves nothing."""
    from agent.ontology import WORLD_GRAPH

    st = genesis_store()
    st.update(f"""DELETE WHERE {{ GRAPH <{WORLD_GRAPH}> {{
        <http://example.org/agora/world/simulation#valve_fern>
            <http://example.org/agora/actuation#actuates> ?pot }} }}""")
    rows = menu_of(st.query, FERN)
    assert not any(r.means == ACQUIRE for r in rows), (
        "an unplumbed market must yield no Acquire row")
    assert any(r.means == OBSERVE for r in rows), (
        "cutting the pipe must not blind the agent — the probes still watch")


def test_two_denominations_make_two_rows_and_never_four(make):
    """#198's fixture, pinned dead: a drying market beside the water market.

    A fan bank sells dry air against the SAME property water raises, into the same pot. Before
    the venue tie, the menu joined "a market I can reach" and "a valuation about this property"
    as independent facts, so each venue would have collected BOTH directions — four rows, two
    of them lies, and the reflex steered by whichever the store returned first. With the tie
    (venue -> marketFor -> source -> supplies -> good <- ofGood <- valuation) each lever
    carries its own physics: two Acquire rows, opposite directions, and a fan is still an
    ACQUIRE — the ladder's rung is about whose resource it is, not which way it moves things.

    Authored by hand into the world graph, which stays legal for a venue the wiring does not
    imply; the goods and the valuation are the test's own, because no shipped domain sells
    drying yet — the day one does, this fixture retires into its ontology.
    """
    from agent.ontology import WORLD_GRAPH

    ns = "http://example.org/agora/world/simulation#"
    market = "http://example.org/agora/market#"
    st = genesis_store()
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{ns}dry_air> a <{market}Good> .
        <{ns}minutesPerFraction>
            <{market}ofGood> <{ns}dry_air> ;
            <{market}aboutProperty> <http://example.org/agora/water#SoilMoisture> ;
            <{market}direction> <{market}Lowers> .
        <{ns}fan_bank> <{market}supplies> <{ns}dry_air> .
        <{ns}fan_market> a <{market}Market> ; <{market}marketFor> <{ns}fan_bank> .
        <{ns}fanco> <{market}hosts> <{ns}fan_market> ;
            <http://example.org/agora/actuation#hasActuator> <{ns}fan1> .
        <{ns}fan1> <http://example.org/agora/actuation#actuates> <{ns}fern> .
        <{ns}fern_agent> <{market}bidsIn> <{ns}fan_market> .
    }} }}""")
    acquire = [r for r in menu_of(st.query, FERN)
               if r.means == ACQUIRE and r.observed_property.endswith("SoilMoisture")]
    assert sorted((r.direction or "").rsplit("#", 1)[-1] for r in acquire) == \
        ["Lowers", "Raises"], (
        "two opposite levers on one property must each carry their own direction — "
        "a cross-join would put both directions on both venues, four rows for two levers")


# --- the Planning member (arc 5) --------------------------------------------

STORED = "http://example.org/agora/water#StoredLitres"
SUPPLIER = "http://example.org/agora/world/simulation#supplier"
_DESIRE = "http://example.org/agora/desire#DesireCapability"
_DELIBERATION = "http://example.org/agora/deliberation#DeliberationCapability"


def test_the_dealer_derives_planning_and_nobody_else_does(make):
    """The grant's premise is levers that compose: acting for a source you offer, refillable
    from a source another offers. The supplier is that shape; a fern offers nothing and the
    city acts for nothing, so depth-2 deliberation arises exactly once in this world."""
    supplier = make("supplier")
    assert any(m.name == "planning" for m in supplier.modules)
    for other in ("fern", "city"):
        assert not any(m.name == "planning" for m in make(other).modules), other


def test_the_provider_hands_actors_the_planner(make):
    """A planner always also derives Reflex (its premise subsumes the reflex's), so two
    family members run in one agent — and which one answers the actors must be a fact, not
    the accident of IRI sort order. This is the pin: if a rename ever flips the build order,
    this fails instead of the dealer quietly losing its depth."""
    supplier = make("supplier")
    assert supplier.provider(_DELIBERATION).name == "planning"


def test_the_planner_pursues_the_lot_past_the_aim(make, monkeypatch):
    """The one deduced goal past the region: the hosted lot must be serveable. With the aim
    satisfied (value above it) the reflex says nothing — and the planner still says ACQUIRE
    while the vessel holds less than the lot its shop owes, because every downstream buyer's
    Acquire silently preconditions stock >= lot. Aim moved to 1.0 for the test so the two
    members genuinely disagree: value 1.5 is comfortable for the reflex and too empty to
    trade from."""
    supplier = make("supplier")
    planner = supplier.provider(_DELIBERATION)
    monkeypatch.setattr(supplier.provider(_DESIRE), "aim", lambda p: 1.0)
    assert planner.propose(STORED, 1.5) == ACQUIRE, \
        "stock 1.5 < lot 2.0 — the shop cannot serve, so the dealer buys"
    assert planner.propose(STORED, 2.5) is None, \
        "stock covers the lot and the aim is met — nothing to do is a decision"


def test_the_plan_is_two_rows_through_two_venues(make):
    """The record's sentence made data: acquire upstream, then offer downstream — a path of
    menu-row-shaped steps through the two venues the grant's premise names, and the minted
    market IRIs recomputed exactly as every rule recomputes them."""
    supplier = make("supplier")
    steps = supplier.provider(_DELIBERATION).plan_for(STORED)
    assert [(s.means.rsplit("#", 1)[-1], s.via.rsplit(".", 1)[-1]) for s in steps] == [
        ("Acquire", "city_mains"), ("Offer", "barrel1")]
    assert supplier.provider(_DELIBERATION).plan_for(MOISTURE) == [], \
        "a planner asked about somebody else's gap has no chain to offer, and says so"


# --- the menu is the union of package contributions (#207) ------------------

def test_a_new_kind_of_move_is_a_new_directory(make, tmp_path, monkeypatch):
    """The tool-plugin claim, proven: a package shipping an `affordances.rq` puts a new KIND
    of row on the menu with no edit outside its own directory. The toy consults an oracle —
    a means no shipped package knows — and its row appears beside Observe and Acquire the
    moment the loader would find its file. Instances were always dynamic (premises in, rows
    out); this is the kinds joining them."""
    from agent import loader

    toy = tmp_path / "affordances.rq"
    toy.write_text("""
SELECT ?means ?property ?via ?direction WHERE {
  $me desire:desires ?region .
  ?region ssn:forProperty ?property .
  BIND(intention:Consult AS ?means)
  BIND($me AS ?via)
}""")
    real = loader.affordance_files()
    monkeypatch.setattr(loader, "affordance_files", lambda: real + (toy,))
    rows = menu_of(genesis_store().query, FERN)
    kinds = {r.means.rsplit("#", 1)[-1] for r in rows}
    assert "Consult" in kinds, "the toy package's kind must appear"
    assert {"Observe", "Acquire"} <= kinds, "and the shipped kinds must survive it"


# --- the menu's two modes (#218) --------------------------------------------

def test_a_duty_is_on_the_menu_and_the_reflex_passes_over_it(make):
    """The sovereign asking what an agent DOES gets its duties beside its options — and this
    member proposes none of them, for a narrower reason than the first draft claimed: an
    obligation IS a want (desire:Obligation) and is meant to reach deliberation, but the
    reflex steers a PROPERTY toward an aim and a duty is not a property-gap. Asked across the
    range rather than at one value, because a filter that leaks at one sign is a filter that
    leaks."""
    supplier = make("supplier")
    rows = menu_of(supplier.store.query, supplier.me.uri)
    duties = [r for r in rows if not r.is_chosen]
    assert duties, "the conduct surface includes what it honours"

    deliberator = supplier.provider(
        "http://example.org/agora/deliberation#DeliberationCapability")
    duty_means = {r.means for r in duties}
    for row in duties:
        for value in (0.0, 0.5, 5.0, 50.0):
            assert deliberator.propose(row.observed_property, value) not in duty_means, \
                "a duty was proposed as if it were a choice"


def test_a_buyer_honours_nothing(make):
    """Fern holds no venue and no valve: everything on its menu is its own to choose."""
    fern = make("fern")
    assert all(r.is_chosen for r in menu_of(fern.store.query, fern.me.uri))
