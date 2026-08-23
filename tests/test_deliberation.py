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
from agent.menu import menu_of
from agent.deliberator import ACQUIRE, OBSERVE

from conftest import MOISTURE, TEMPERATURE, build_agent, genesis_store, desires_build


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


def decider_of(agent):
    return next(m for m in agent.modules if m.name == "deliberation")


def market_of(agent):
    return agent.me.markets[0]


# --- who decides, and who has nothing to decide -----------------------------

def test_every_agent_deliberates_including_one_with_nothing_to_decide(make):
    """What the `deliberation:Reflex` GRANT used to say, and why it no longer says it.

    The premise was a stake AND a lever, so an agent with neither — world/sensing's, which
    records and wants nothing — was granted no deliberation and built no module. That was
    never defensible beside the two lines above it in `Agent.__init__`: `Desires` and
    `Intentions` are built for every agent unconditionally, because a mind is not
    plug-in-able. The deliberator now joins them.

    The reading the grant used to carry is preserved and moved onto the FACT: an agent with
    nothing to pursue proposes nothing and REPORTS nothing, so the absence of its figures
    still says something true — it just says it about what is true of the agent now rather
    than about what its world provisioned once. See `Deliberator.series`.
    """
    fern = make("fern")
    assert fern.deliberator is not None, "the kernel builds one for every agent"
    assert any(m.name == "deliberation" for m in fern.modules), \
        "and it joins the choir, so start/stop/series reach it like any other member"

    #  The reading that used to be carried by the ABSENCE of the module: nothing pursued,
    #  nothing reported. Monkeypatched rather than built from world/sensing, because what is
    #  under test is the deliberator's own rule and not that world's wiring.
    fern.deliberator.pursued = lambda: []
    assert fern.deliberator.series() == [], \
        "nothing to decide is not zero things decided — an agent with no wants files no figures"


# --- the reflex, which is the old chain verbatim ----------------------------

def test_not_seeing_means_look(make):
    """The oldest rule in the reflex, now asked in the words it means (#240).

    It used to be `propose(property, None) == OBSERVE` — a first line that read a missing value
    as ignorance. The behaviour is unchanged and the QUESTION is different: a desire says which
    epistemic failure it is, so "never read" and "the caller passed no number" stop being the
    same sentinel. Both epistemic states are asserted, because they are repaired by the same
    move for the same reason and a rule that covered only one would leave stale readings
    unwatched.
    """
    from agent.desire import Desire

    decider = decider_of(make("fern"))
    never_read = Desire(uri="urn:w", urgency=1.0, observed_property=MOISTURE,
                      value=None, state="unmeasured")
    too_old = Desire(uri="urn:w", urgency=1.0, observed_property=MOISTURE,
                   value=0.30, state="stale")
    assert decider.propose_for(never_read) == OBSERVE
    assert decider.propose_for(too_old) == OBSERVE, \
        "a reading that stopped being evidence is repaired by looking, not by watering"
    assert decider.propose(MOISTURE, None) is None, \
        "and the bare value door steers only — it no longer answers the epistemic question"


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
    #  Both doors: "silenced" means it answers nothing whatever it is asked. Patching only
    #  the one this scenario happens to use would pass while saying less than it claims, and
    #  would break silently the next time a caller changed which question it asks.
    monkeypatch.setattr(decider_of(fern), "propose", lambda prop, value: None)
    monkeypatch.setattr(decider_of(fern), "propose_for", lambda desire: None)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.sent.to(f"{market.bid_topic}/fern") == []


def test_the_deliberator_choosing_not_to_look_is_honoured(make, monkeypatch):
    """The other whether: with no fresh reading, the reflex says look — and a member that said
    otherwise (a model judging the last reading close enough to certain) is obeyed, not
    second-guessed. The bidder neither senses nor waits; the round simply passes."""
    fern = make("fern")  # no reading at all
    market = market_of(fern)
    #  Both doors: "silenced" means it answers nothing whatever it is asked. Patching only
    #  the one this scenario happens to use would pass while saying less than it claims, and
    #  would break silently the next time a caller changed which question it asks.
    monkeypatch.setattr(decider_of(fern), "propose", lambda prop, value: None)
    monkeypatch.setattr(decider_of(fern), "propose_for", lambda desire: None)
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
        PREFIX market: <http://example.org/orexis/market#>
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
        PREFIX market: <http://example.org/orexis/market#>
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
    st = genesis_store()
    rows = menu_of(st.query, FERN, desires_build(st, "fern").query_union)
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
    st = genesis_store()
    rows = menu_of(st.query, "http://example.org/orexis/world/simulation#supplier", desires_build(st, "supplier").query_union)
    assert [(r.means.rsplit("#", 1)[-1], r.observed_property.rsplit("#", 1)[-1],
             (r.direction or "").rsplit("#", 1)[-1] or None)
            for r in rows if r.is_chosen] == [("Acquire", "StoredLitres", "Raises"),
                                              ("Observe", "StoredLitres", None)]
    #  And beside them, since #218, what the dealer HONOURS: claims presented against the
    #  venue it hosts are redeemed through its valves — one row per lever, never a proposal.
    honoured = [r for r in rows if not r.is_chosen]
    assert {r.means.rsplit("#", 1)[-1] for r in honoured} == {"Apply"}
    assert len(honoured) == 3, "one duty per valve it holds for its buyers"


FERN = "http://example.org/orexis/world/simulation#fern_agent"


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
        <http://example.org/orexis/world/simulation#valve_fern>
            <http://example.org/orexis/actuation#actuates> ?pot }} }}""")
    rows = menu_of(st.query, FERN, desires_build(st, "fern").query_union)
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

    ns = "http://example.org/orexis/world/simulation#"
    market = "http://example.org/orexis/market#"
    st = genesis_store()
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{ns}dry_air> a <{market}Good> .
        <{ns}minutesPerFraction>
            <{market}ofGood> <{ns}dry_air> ;
            <{market}aboutProperty> <http://example.org/orexis/water#SoilMoisture> ;
            <{market}direction> <{market}Lowers> .
        <{ns}fan_bank> <{market}supplies> <{ns}dry_air> .
        <{ns}fan_market> a <{market}Market> ; <{market}marketFor> <{ns}fan_bank> .
        <{ns}fanco> <{market}hosts> <{ns}fan_market> ;
            <http://example.org/orexis/actuation#hasActuator> <{ns}fan1> .
        <{ns}fan1> <http://example.org/orexis/actuation#actuates> <{ns}fern> .
        <{ns}fern_agent> <{market}bidsIn> <{ns}fan_market> .
    }} }}""")
    acquire = [r for r in menu_of(st.query, FERN, desires_build(st, "fern").query_union)
               if r.means == ACQUIRE and r.observed_property.endswith("SoilMoisture")]
    assert sorted((r.direction or "").rsplit("#", 1)[-1] for r in acquire) == \
        ["Lowers", "Raises"], (
        "two opposite levers on one property must each carry their own direction — "
        "a cross-join would put both directions on both venues, four rows for two levers")


# --- the Planning member (arc 5) --------------------------------------------

STORED = "http://example.org/orexis/water#StoredLitres"
SUPPLIER = "http://example.org/orexis/world/simulation#supplier"


def test_the_dealers_clause_answers_for_the_dealer_and_nobody_else(make):
    """What the Planning GRANT used to say, said about the fact instead.

    There was a `deliberation:Planning` member derived from levers that compose — acting for a
    source you offer, refillable from a source another offers — and a `deliberation:Reflex` it
    SUBCLASSED. The subclass called `super().propose()` first and added one clause; that clause
    asks `_my_shop_needs`, which answers only for a property that is this agent's own vessel's
    stock. A member that contains the other, whose extra branch is inert for every other agent,
    is not an interchangeable implementation — so they are one class and the world derives
    neither.

    What must still be true is exactly what the grant protected: the clause fires for the
    dealer and is silent for everyone else. That is a property of the data now rather than of
    who was handed which module, which is why this asks the clause directly."""
    assert make("supplier").deliberator._my_shop_needs(STORED) is not None, \
        "the dealer acts for a vessel it offers — its shop owes a lot"
    for other in ("fern", "city"):
        assert make(other).deliberator._my_shop_needs(STORED) is None, \
            f"{other} has no shop, so the dealer's clause must not answer for it"


def test_the_planner_pursues_the_lot_past_the_aim(make, monkeypatch):
    """The one deduced desire past the region: the hosted lot must be serveable. With the aim
    satisfied (value above it) the reflex says nothing — and the planner still says ACQUIRE
    while the vessel holds less than the lot its shop owes, because every downstream buyer's
    Acquire silently preconditions stock >= lot. Aim moved to 1.0 for the test so the two
    members genuinely disagree: value 1.5 is comfortable for the reflex and too empty to
    trade from."""
    supplier = make("supplier")
    planner = supplier.deliberator
    monkeypatch.setattr(supplier.deducer, "aim", lambda p: 1.0)
    assert planner.propose(STORED, 1.5) == ACQUIRE, \
        "stock 1.5 < lot 2.0 — the shop cannot serve, so the dealer buys"
    assert planner.propose(STORED, 2.5) is None, \
        "stock covers the lot and the aim is met — nothing to do is a decision"


def test_the_plan_is_two_rows_through_two_venues(make):
    """The record's sentence made data: acquire upstream, then offer downstream — a path of
    menu-row-shaped steps through the two venues the grant's premise names, and the minted
    market IRIs recomputed exactly as every rule recomputes them."""
    supplier = make("supplier")
    steps = supplier.deliberator.plan_for(STORED)
    assert [(s.means.rsplit("#", 1)[-1], s.via.rsplit(".", 1)[-1]) for s in steps] == [
        ("Acquire", "city_mains"), ("Offer", "barrel1")]
    assert supplier.deliberator.plan_for(MOISTURE) == [], \
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
  VALUES ?property { $properties }
  BIND(ag:Consult AS ?means)
  BIND($me AS ?via)
}""")
    real = loader.affordance_files()
    monkeypatch.setattr(loader, "affordance_files", lambda: real + (toy,))
    st = genesis_store()
    rows = menu_of(st.query, FERN, desires_build(st, "fern").query_union)
    kinds = {r.means.rsplit("#", 1)[-1] for r in rows}
    assert "Consult" in kinds, "the toy package's kind must appear"
    assert {"Observe", "Acquire"} <= kinds, "and the shipped kinds must survive it"


# --- the menu's two modes (#218) --------------------------------------------

def test_a_duty_is_on_the_menu_and_the_reflex_passes_over_it(make):
    """The sovereign asking what an agent DOES gets its duties beside its options — and this
    member proposes none of them, for a narrower reason than the first draft claimed: an
    obligation IS a want (ag:Obligation) and is meant to reach deliberation, but the
    reflex steers a PROPERTY toward an aim and a duty is not a property-gap. Asked across the
    range rather than at one value, because a filter that leaks at one sign is a filter that
    leaks."""
    supplier = make("supplier")
    rows = menu_of(supplier.beliefs.query, supplier.me.uri, supplier.desires.query_union)
    duties = [r for r in rows if not r.is_chosen]
    assert duties, "the conduct surface includes what it honours"

    deliberator = supplier.deliberator
    duty_means = {r.means for r in duties}
    for row in duties:
        for value in (0.0, 0.5, 5.0, 50.0):
            assert deliberator.propose(row.observed_property, value) not in duty_means, \
                "a duty was proposed as if it were a choice"


def test_a_buyer_honours_nothing(make):
    """Fern holds no venue and no valve: everything on its menu is its own to choose."""
    fern = make("fern")
    assert all(r.is_chosen for r in menu_of(fern.beliefs.query, fern.me.uri, fern.desires.query_union))


# --- step 9: a desire, not a property and a value -----------------------------

def test_a_duty_is_pursued_through_the_lever_that_serves_its_counterparty(make):
    """`propose_for` takes the WANT, so a duty reaches deliberation as what it is.

    Its means is not deduced here and could not be: it is the honoured row the market derives
    from the delivery chain, and the one that answers is the row honoured for exactly this
    counterparty. A host with two buyers must not serve one's claim through the other's valve,
    which is why the match is on the agent and not on the mode alone.
    """
    from agent.desire import Desire

    supplier = make("supplier")
    duty = Desire(uri="urn:o", urgency=0.9, claim="j-1",
                owed_to="http://example.org/orexis/world/simulation#fern_agent")
    assert supplier.deliberator.propose_for(duty) == \
        "http://example.org/orexis#Apply"

    stranger = Desire(uri="urn:o", urgency=0.9, claim="j-2", owed_to="urn:nobody")
    assert supplier.deliberator.propose_for(stranger) is None, \
        "a debt no lever of mine can reach proposes nothing — and stays owed"


def test_an_unpresented_duty_is_hot_and_still_not_acted_on(make):
    """Two questions, kept apart: how urgent a debt is, and whether anything is being asked
    yet. The holder waits for its own watch to be live (#132), so a host that doses on the
    strength of urgency alone would spend the water where nothing is looking — and a debt
    approaching its deadline that nobody has presented is exactly the case where the two
    answers differ."""
    from agent.desire import Desire

    supplier = make("supplier")
    standing = Desire(uri="urn:o", urgency=0.99, claim="j-3", pursuable=False,
                    owed_to="http://example.org/orexis/world/simulation#fern_agent")
    assert supplier.deliberator.propose_for(standing) is None


def test_a_stake_reaches_the_same_door_and_behaves_exactly_as_before(make):
    """The widening must not move the reflex. A desire with a property and a value is the old
    question in the new shape, and it has to answer identically — the regression this design
    is most exposed to is a rewrite that quietly changes what a thirsty agent does."""
    from agent.desire import Desire

    fern = make("fern")
    reflex = fern.deliberator
    for value in (0.30, 0.55, 0.80):
        stake = Desire(uri="urn:want", urgency=0.4, observed_property=MOISTURE, value=value)
        assert reflex.propose_for(stake) == reflex.propose(MOISTURE, value)


def test_every_want_is_drawn_by_the_one_module_that_sees_them_all(make):
    """One row per want, tagged by the WANT — the sovereign's correction to a first draft that
    keyed the panel on the property.

    A property cannot name every want: freshness is per instrument, a duty is per counterparty.
    So a graph grouped by property could only ever draw stakes, and "urgency is the common
    currency" would stay a claim rather than something you can look at.

    A duty is tagged by whom it is owed to and NEVER by its claim: a jti is unique per round, so
    tagging by it would mint a series every time the society traded and grow the store's
    cardinality with its history.
    """
    fern = make("fern")
    rows = [(tags, fields) for meas, tags, fields in
            next(m for m in fern.modules if m.name == "deliberation").series()
            if meas == "agent_want"]

    assert rows, "an agent that wants things reports each of them"
    assert all(set(f) == {"urgency"} for _, f in rows), "one figure: how badly it is unmet"
    assert all(0.0 <= f["urgency"] <= 1.0 for _, f in rows), "normalised, or the axis lies"
    tags = {t["want"] for t, _ in rows}
    assert len(tags) == len(rows), "one line per want, not several sharing a name"
    assert not any(len(t) > 60 for t in tags), \
        "a tag carrying a jti would mint a new series per round — duties are tagged by whom"


def test_a_pass_reports_what_it_cost_and_what_it_could_not_see(make):
    """The figures fall out of the pass that already happened — never a second one.

    Re-planning to measure would double the cost being measured, which is the one thing an
    observability change must not do. So every figure here is a projection of the trace the
    pass wrote as it ended.

    Asked of FERN, and the numbers are the point rather than the plumbing. fern buys its
    water, and since #268 the market states what buying does — so the search now sees the lever
    that matters and `blind` is ZERO. That number was 1 for every plant, and its falling is the
    whole of what #268 changed: a search that passed over Acquire could not claim to see the
    menu, and the pass now does.
    """
    from agent import trace

    #  WITH A READING, because an agent that has never looked does not plan: `propose_for`
    #  answers an unmeasured or stale want with Observe before any search runs (#240). So an
    #  agent at rest reports zeros here — honestly, since nothing was deliberated — and a test
    #  that used one would have pinned the figures of a pass that never happened.
    fern = make("fern", genesis_store({"fern": 0.10}))
    rows = {measurement: fields for measurement, _, fields in
            next(m for m in fern.modules if m.name == "deliberation").series()}
    planning = rows["agent_planning"]

    assert planning["seconds"] > 0, "a pass that took no time did not happen"
    assert planning["blind"] == 0, \
        "since #268 every lever on fern's menu states its effect, so no desire is passed over"
    assert planning["deepest"] <= 1, \
        "depth beyond one step is nominal today (#254, #258) — if this rises, those were fixed"
    assert set(trace.FIELD.values()) <= set(planning), \
        "every candidate verdict is reported under the short name declared beside it"


def test_the_figures_do_not_cost_what_they_report(make):
    """An observability change that slows the thing it observes is worse than none.

    The trace write was measured at 0.7% of a pass when it landed; this reads that trace back
    and must stay in the same league. Generous bound because a shared machine's noise is larger
    than the thing being bounded — what would fail here is an implementation that re-planned,
    or one that walked the whole store per field.
    """
    import time

    from agent import trace

    fern = make("fern", genesis_store({"fern": 0.10}))
    next(m for m in fern.modules if m.name == "deliberation").series()   # fill the trace

    trace.effort(fern.desires.query_union)                                 # warm
    started = time.monotonic()
    for _ in range(5):
        trace.effort(fern.desires.query_union)
    each = (time.monotonic() - started) / 5

    assert each < 0.05, f"reading the figures took {each*1000:.0f}ms — it should be under 1ms"
