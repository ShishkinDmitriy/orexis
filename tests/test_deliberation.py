"""Deliberation: the whether, extracted — and provably no longer the bidder's.

Phase 4 of knowledge/decisions/an-intention-is-an-amortised-deliberation.md, and the end of the
roadmap it opened. The welded chain (below the aim → pursue; cannot see → look) moved out of
the bidder, so the round tests hold untouched and the one NEW thing to prove is the seam
itself: silence the deliberator and a thirsty bidder with a fresh reading in hand submits
nothing, because the whether genuinely moved. That test is the property an LLM member will
stand on.

**The chain itself is gone now**, absorbed by the search that used to run in front of it —
see a-plan-is-a-path-of-graph-diffs.md. So the assertions here are about the BEHAVIOUR the
reflex used to carry rather than about the reflex: a thirsty plant buys, a sated one does not,
an obligation is never proposed as a choice, and an agent whose search cannot answer proposes
nothing instead of finding a second path.
"""

from __future__ import annotations

import pytest

from agent_old.world import load_self
from orexis_agent_deliberation.steps import find_steps
from orexis_capability_market.terms import ACQUIRING
from orexis_capability_sensing.terms import OBSERVING

from orexis_agent_progression.ontology import picks_graph
from orexis_capability_sensing.regions import ObservedWant
from conftest import region_want_of, MOISTURE, TEMPERATURE, build_agent, genesis_store, desires_build, open_round_for, wired_markets, wired_sensors, write_reading
from conftest import ABOUT, DIRECTION, VALVE, VENUE


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


def decider_of(agent):
    return next(m for m in agent.modules if m.name == "deliberation")


def market_of(agent):
    return wired_markets(agent)[0]


# --- who decides, and who has nothing to decide -----------------------------

def test_every_agent_deliberates_including_one_with_nothing_to_decide(make):
    """What the `deliberation:Reflex` GRANT used to say, and why it no longer says it.

    The premise was a region want AND a lever, so an agent with neither — world/sensing's, which
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


# --- the behaviour the old chain carried, asked of the search ---------------

def test_not_seeing_means_look(make):
    """The oldest rule in deliberation, and now nothing in deliberation says it.

    Three forms, in order. It was `propose(property, None) == OBSERVING`, a first line reading a
    missing value as ignorance. Then it was `desire.state in ("unmeasured", "stale") ->
    OBSERVING`, which said the same thing in the words it meant and still said it by hand. It is
    now a WANT — this reading exists and was taken recently enough — whose met-shape a look
    repairs and whose repair the search finds, so the rule is not stated anywhere and holds
    anyway.

    Both epistemic states are still asserted, because they are the same want short in two
    ways and a change that covered only one would leave stale readings unwatched. Asked of the
    agent's OWN want rather than of a constructed one: a want is a shape now, and a shape
    nobody derived is a want the search has nothing to check.
    """
    fern = make("fern")
    decider = decider_of(fern)
    never_read = next(d for d in fern.considering()
                      if d.is_epistemic and d.observed_property == MOISTURE)
    assert never_read.state == "unmeasured"
    assert decider.propose_for(never_read) == OBSERVING

    _read(fern, 0.30, age_s=10_000)
    too_old = next(d for d in fern.considering()
                   if d.is_epistemic and d.observed_property == MOISTURE)
    assert too_old.state == "stale", "read once, and the answer has gone cold"
    assert decider.propose_for(too_old) == OBSERVING, \
        "a reading that stopped being evidence is repaired by looking, not by watering"


def _read(agent, value, age_s=0):
    """Put one reading of the agent's own moisture in its sensed graph, `age_s` old.

    Written through the production writer rather than by hand, so the observation carries the
    sensor that made it — which the freshness want asks for, and which is exactly what tells
    a look apart from a dose's prediction of what a look would find.
    """
    from datetime import datetime, timedelta, timezone

    from orexis_capability_sensing.sensed_writer import SensedWriter

    sensor = wired_sensors(agent)[0]
    SensedWriter(agent.beliefs).write(
        subject_uri=sensor.subject, subject_id=sensor.subject.rsplit("#", 1)[-1],
        value=value, sensor_uri=sensor.uri, observed_property=sensor.observes,
        author_uri=agent.me.uri, used_procedure=sensor.sense_mode,
        ts=(datetime.now(timezone.utc) - timedelta(seconds=age_s)).isoformat())
    #  AND THE AGENT NOTICES, which since #598 is a second thing: a reading is stale because
    #  sensing said so on the reading, not because its timestamp is old. The module re-arms
    #  from what stands and marks one whose horizon has already gone.
    for module in agent.modules:
        if hasattr(module, "watch_staleness"):
            module.watch_staleness(sensor.subject, sensor.observes)


def test_below_the_aim_means_pursue_and_above_means_nothing(make):
    """Fern aims at 0.55, and steering is toward the PICK rather than the region's edge —
    pursuing only past the band would leave the agent permanently short of where it decided
    to sit.

    Asked of the search, which is the only path there is. The chain that used to answer this
    compared the gap's sign to the lever's stated direction; the search builds the world a
    purchase would reach and takes it only if that world scores better. The two agree at every
    value below the aim and at every value above it, which is what made deleting the first one
    safe — and they disagree exactly where the old answer was wrong, which
    `tests/test_planning.py` measures on a plant sitting above its region.
    """
    from orexis_agent_deliberation.want import Want

    fern = make("fern")
    open_round_for(fern, "fern")   # a buying row exists only while a round is open (#358)
    decider = decider_of(fern)
    #  The WORLD holds the value, not the want: a reading is sensing's, and the rule sizing
    #  a purchase reads where the property stands from the sensed graph.
    #  BY BAND (#579): a pot below its region buys; a pot inside it — below its aim or not —
    #  is content, since the search plans on what the reading IS and steering to the aim
    #  inside the region is the actor's, when it sizes the act it takes. A pot above buys
    #  nothing either: a lot reaches the region from below, and from above it helps nothing.
    for value in (0.10, 0.39):
        write_reading(fern, value, MOISTURE)
        region_want = ObservedWant(uri=region_want_of(fern).uri, observed_property=MOISTURE,
                             value=value)
        assert decider.propose_for(region_want) == ACQUIRING, f"thirsty at {value} and not buying"
    for value in (0.54, 0.55, 0.80):
        write_reading(fern, value, MOISTURE)
        region_want = ObservedWant(uri=region_want_of(fern).uri, observed_property=MOISTURE,
                             value=value)
        assert decider.propose_for(region_want) is None, f"content at {value} and buying anyway"


def test_a_property_this_agent_cannot_move_is_not_pursued(make):
    """Fern can SEE a temperature and holds no lever that changes one, so nothing is proposed
    about it — a want with no lever, which is legitimate and now legible.

    This used to be asserted about the AIM: fern picks no temperature aim, and the chain
    refused to steer a property its agent had chosen no point in. That reason has gone with
    the chain — a declared measure stands the region's CENTRE in where no pick exists, so a
    search would steer an aimless property if it held a lever for one. It never got the
    chance even before the deletion, because the search already answered first for every
    desire it could rank; the reflex's aim clause had been unreachable for a measurable want
    since simulation landed. What answers now is the honest fact: no lever, no move.
    """
    from orexis_agent_deliberation.want import Want

    fern = make("fern")
    region_want = ObservedWant(uri=region_want_of(fern, TEMPERATURE).uri,
                         observed_property=TEMPERATURE, value=5.0)
    assert decider_of(fern).propose_for(region_want) is None


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
    #  would break silently the next time a caller changed which question it asks. They are
    #  the desire door and the property door, and `decide`, the PLAN door execution asks.
    monkeypatch.setattr(decider_of(fern), "propose_for", lambda desire: None)
    monkeypatch.setattr(decider_of(fern), "propose_for", lambda desire: None)
    monkeypatch.setattr(decider_of(fern), "decide", lambda desire, **kw: None)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    assert fern.sent.to(f"{market.bid_topic}/fern") == []


def test_the_deliberator_choosing_not_to_look_is_honoured(make, monkeypatch):
    """The other whether: with no fresh reading, the reflex says look — and a member that said
    otherwise (a model judging the last reading close enough to certain) is obeyed, not
    second-guessed. The bidder neither senses nor bids; the round simply passes.

    WHEN it passes moved with #392. The offer marks the want and returns — a handler does not
    wait on a search — so the bidder finds out that nothing was proposed at the round's CLOSE
    rather than at once, which is also the more honest moment: a reading arriving mid-round
    could have changed the answer. What the silence still buys is the whole of it: nothing
    committed, nothing sensed, nothing bid.
    """
    fern = make("fern")  # no reading at all
    market = market_of(fern)
    #  Both doors: "silenced" means it answers nothing whatever it is asked. Patching only
    #  the one this scenario happens to use would pass while saying less than it claims, and
    #  would break silently the next time a caller changed which question it asks. They are
    #  the desire door and the property door, and `decide`, the PLAN door execution asks.
    monkeypatch.setattr(decider_of(fern), "propose_for", lambda desire: None)
    monkeypatch.setattr(decider_of(fern), "propose_for", lambda desire: None)
    monkeypatch.setattr(decider_of(fern), "decide", lambda desire, **kw: None)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    # nothing was committed to — no observe intention, no acquire, nothing to wait on
    keeper = next(m for m in fern.modules if m.name == "intention")
    assert keeper.standing() == []
    #  The nudge is not the deliberator's: `on_offer` asks its board to look whenever a round
    #  opens, silenced or not. What the silence buys is that no BID went out.
    assert not fern.sent.to(f"{market.bid_topic}/{fern.id}"), "silenced, and it bid anyway"
    # and the round passes when it closes, which is the give-up the offer's own window set
    fern.bidding().give_up()
    assert fern.bidding().pending is None


def test_the_round_runs_exactly_as_it_always_did(make):
    """Thirsty bids, sated cedes — through the extraction, and through the reflex's deletion.
    The round tests hold this in the large; this is the same fact stated where the seam lives,
    and it is the one assertion that would have caught the search quietly deciding differently
    from the chain it replaced."""
    thirsty = make("fern", genesis_store({"fern": 0.10}))
    thirsty.deliver(market_of(thirsty).offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    assert len(thirsty.sent.to(f"{market_of(thirsty).bid_topic}/fern")) == 1

    sated = make("fern", genesis_store({"fern": 0.80}))
    sated.deliver(market_of(sated).offer_topic, {"auction_id": "r2", "closes_in_s": 30})
    assert sated.sent.to(f"{market_of(sated).bid_topic}/fern") == []


# --- which way a lever moves things is the graph's, not the code's (#127) ---

def test_the_sign_is_the_packages_statement_and_not_this_codes(make):
    """Say that buying water LOWERS the moisture it is priced in, and a thirsty plant stops
    buying — with no line of Python changed anywhere.

    This is #127's claim, asked where the claim now lives. It used to be asked of
    `market:direction`, a one-bit fact the chain compared against the gap's sign: flip Raises
    to Lowers and the reflex pursued on the other side of the aim. The search never reads that
    bit. What it reads is the EFFECT — the market's own `sh:construct`, which declares what the
    reading BECOMES (#579) — so the sign is stated by the package that owns the lever, in RDF,
    and in the domain's own description of its world rather than as one bit.

    So the fixture flips what the shipped rule says a bought lot reaches: the region, or below
    it. A plant at 0.10 buys because the world it would reach is one where its moisture sits in
    its region; told that buying leaves it below the region, the same plant finds that world no
    better than standing still and declines. The bit itself is untouched here, which is the
    point — it steers nothing now, and its retirement rides with repair-matching.
    """
    from orexis_agent_deliberation.want import Want
    from orexis_agent_progression.ontology import ACTIONS_GRAPH

    ds = genesis_store()
    ds.update(f"""
        DELETE {{ GRAPH <{ACTIONS_GRAPH}> {{ market:Acquiring sh:construct ?text }} }}
        INSERT {{ GRAPH <{ACTIONS_GRAPH}> {{ market:Acquiring sh:construct ?flipped }} }}
        WHERE  {{ GRAPH <{ACTIONS_GRAPH}> {{ market:Acquiring sh:construct ?text }}
                  BIND(REPLACE(?text, "sensing:InRegion", "sensing:BelowRegion") AS ?flipped) }}""")
    fern = make("fern", ds)
    open_round_for(fern, "fern")
    decider = decider_of(fern)
    region_want = ObservedWant(uri=region_want_of(fern).uri, observed_property=MOISTURE,
                         value=0.10)
    assert decider.propose_for(region_want) is None, \
        "a lever the graph says would dry this plant out was pulled anyway"


# --- the menu: what I could do, derived -------------------------------------

def test_the_menu_is_derived_from_the_graph(make):
    """The Consulting member's prompt substrate, checkable before that member exists: for this
    agent — these properties, these levers, these directions. Nothing here was written as a
    menu; every row is a join over facts that exist for their own reasons."""
    st = genesis_store()
    open_round_for(st, "fern")
    rows = find_steps(st, desires_build(st, "fern").abouts(FERN), FERN, picks_graph("fern"))
    as_tuples = {(r.action.rsplit("#", 1)[-1], (r.value_of(ABOUT) or "").rsplit("#", 1)[-1],
                  (r.value_of(DIRECTION) or "").rsplit("#", 1)[-1] or None) for r in rows}
    #  A row says which WANT it serves through what the want is about: a region_want is about its
    #  property, a freshness want about its instrument (the-region-want-is-sensings-want). So a look
    #  appears twice per probe — for the region it should sit in, and for knowing it recently.
    assert as_tuples == {
        ("Observing", "SoilMoisture", None),          # look through the probe, for the region want
        ("Observing", "AirTemperature", None),        # look through the thermometer, for it
        ("Observing", "moisture_sensor_fern", None),  # look, for knowing what the probe says
        ("Observing", "air_temp_fern", None),         # and what the thermometer says
        ("Acquiring", "SoilMoisture", "Raises"),      # raise it through the market
    }
    # and the row that is NOT there is the finding: fern wants a temperature it can see and
    # cannot move — a want with no lever, which is legitimate and now legible.
    assert not any(r.action.endswith("Acquiring") and "Temperature" in (r.value_of(ABOUT) or "")
                   for r in rows)


def test_the_dealers_menu_gained_its_lever(make):
    """The supplier across the arcs: it wants its barrel full (arc 2), can SEE the level
    (arc 1), and — since the city exists (arc 4) — holds the LEVER: bidding in the refill
    venue, whose winnings physically reach its barrel through the city's pipe, priced in
    StoredLitres, raising it. This test guarded the seen-but-unmovable reading while that
    was the honest one; the row it waited for is derived now, direction and all.

    AND NO OBSERVING ROW, which is the shipped case of a lever an agent cannot pull. The
    supplier's one instrument is `barrel1_level`, a float switch that announces — push mode,
    so the supplier is a LISTENER on it and `sense_now()` is an empty method whose docstring
    says listening cannot. The row was offered anyway until the mode-conditional precondition:
    the search proposed a look, the keeper committed to it, nothing left the process, and the
    intention stood until patience outwaited it and adopted the same nothing again. What the
    supplier gets now is one lever and an honest silence about the other.
    """
    st = genesis_store()
    open_round_for(st, "supplier")
    rows = find_steps(st, desires_build(st, "supplier").abouts("http://example.org/orexis/world/simulation#supplier"), "http://example.org/orexis/world/simulation#supplier", picks_graph("supplier"))
    assert {(r.action.rsplit("#", 1)[-1], (r.value_of(ABOUT) or "").rsplit("#", 1)[-1],
             (r.value_of(DIRECTION) or "").rsplit("#", 1)[-1] or None)
            for r in rows if r.is_own} == {("Acquiring", "StoredLitres", "Raises"),
                                            ("Offering", "StoredLitres", None)}, \
        "buy upstream while the city's round is open, and offer downstream (#359) — no direction " \
        "on the second, because offering moves no water"
    #  And NOTHING HONOURED beside them: what the dealer honours — claims presented against
    #  the venue it hosts, redeemed through its valves (#218) — is a row per want about a
    #  debt, and a store with no debt in it holds no such want. It used to be one row per
    #  valve, standing whether or not anybody was owed anything.
    assert [r for r in rows if not r.is_own] == [], "nothing owed, nothing honoured"


FERN = "http://example.org/orexis/world/simulation#fern_agent"


def test_a_market_no_valve_connects_to_your_pot_is_no_lever(make):
    """The Acquire row is DEDUCED along the plumbing (#127, strengthened): the market's host
    holds an actuator, the actuator is plumbed to MY pot, so opening it puts the good where I
    am — and only the physics atom (water raises moisture) is stated, once, by the domain.
    Cut the pipe and the row vanishes: fern still bids in a market, the domain still prices
    moisture, but a delivery that cannot reach your pot is, for you, no lever at all — and
    the reflex must not be offered a move that moves nothing."""
    from orexis_agent_progression.ontology import WORLD_GRAPH

    st = genesis_store()
    st.update(f"""DELETE WHERE {{ GRAPH <{WORLD_GRAPH}> {{
        <http://example.org/orexis/world/simulation#valve_fern>
            <http://example.org/orexis/actuation#actuates> ?pot }} }}""")
    rows = find_steps(st, desires_build(st, "fern").abouts(FERN), FERN, picks_graph("fern"))
    assert not any(r.action == ACQUIRING for r in rows), (
        "an unplumbed market must yield no Acquire row")
    assert any(r.action == OBSERVING for r in rows), (
        "cutting the pipe must not blind the agent — the probes still watch")


def test_two_denominations_make_two_rows_and_never_four(make):
    """#198's fixture, pinned dead: a drying market beside the water market.

    A fan bank sells dry air against the SAME property water raises, into the same pot. Before
    the venue tie, the menu joined "a market I can reach" and "a valuation about this property"
    as independent facts, so each venue would have collected BOTH directions — four rows, two
    of them lies, and the reflex steered by whichever the store returned first. With the tie
    (venue -> marketFor -> source -> supplies -> good <- ofGood <- valuation) each lever
    carries its own physics: two Acquire rows, opposite directions, and a fan is still an
    ACQUIRING — the ladder's rung is about whose resource it is, not which way it moves things.

    Authored by hand into the world graph, which stays legal for a venue the wiring does not
    imply; the goods and the valuation are the test's own, because no shipped domain sells
    drying yet — the day one does, this fixture retires into its ontology.
    """
    from orexis_agent_progression.ontology import WORLD_GRAPH

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
    open_round_for(st, "fern")
    acquire = [r for r in find_steps(st, desires_build(st, "fern").abouts(FERN), FERN, picks_graph("fern"))
               if r.action == ACQUIRING and (r.value_of(ABOUT) or "").endswith("SoilMoisture")]
    assert sorted((r.value_of(DIRECTION) or "").rsplit("#", 1)[-1] for r in acquire) == \
        ["Lowers", "Raises"], (
        "two opposite levers on one property must each carry their own direction — "
        "a cross-join would put both directions on both venues, four rows for two levers")


# --- the dealer's two-step (arc 5) ------------------------------------------
#
#  WHAT IS NOT HERE ANY MORE. Two tests stood here about the reflex's one clause past the
#  region — `_my_shop_needs`, which fired only for an agent whose own vessel's stock was the
#  property in hand, and made a dealer buy while the barrel held less than the lot it had
#  promised even where its aim was met. The clause went with the reflex and nothing derives
#  serveability as a DESIRE, so the search cannot pursue what it is never handed. Inert in
#  every shipped world (the supplier aims at 3.0 L and offers 2.0 L, so short of the lot is
#  short of the aim), and live for anyone who authors an aim below their own lot. Recorded in
#  a-plan-is-a-path-of-graph-diffs.md rather than left as a test nobody could keep green.

STORED = "http://example.org/orexis/water#StoredLitres"
SUPPLIER = "http://example.org/orexis/world/simulation#supplier"


def test_the_search_finds_the_dealers_two_step_from_two_nodes_that_never_meet(make):
    """The record's sentence, FOUND rather than written: acquire upstream, then offer
    downstream. A call on a dry barrel, the city's round open — and the search plans exactly
    those two rows, because Acquiring's effect raises the stock that Offering's premise reads.
    `plan.rq` used to narrate this by hand; a narrative beside a search that produces the same
    thing was the kernel's last reason to spell the market's `Offer`."""
    from orexis_capability_market import calls

    supplier = make("supplier", genesis_store({("barrel1", STORED): 0.0}))
    open_round_for(supplier, "supplier")                 # the city convenes
    calls.call(supplier, next(m.uri for m in supplier.hosting().markets), "fern")
    #  THE WANT ABOUT THE CALL, not the call itself: a call is an instance under the host's
    #  standing desire now, and the want the derivation mints is named after the desire.
    called = calls.uri_for(next(m.uri for m in supplier.hosting().markets))
    want = next(d for d in supplier.considering() if called in d.about)
    plan = supplier.deliberator.decide(want)
    assert plan is not None
    assert [(s.action.rsplit("#", 1)[-1], (s.value_of(VENUE) or s.value_of(VALVE) or "").rsplit(".", 1)[-1])
            for s in plan.steps] == [
        ("Acquiring", "city_mains"), ("Offering", "barrel1")]
    assert plan.unmet_after == 0.0, "and the world it reaches has the round the call wanted"
# --- the menu is the union of package contributions (#207) ------------------

def test_a_new_kind_of_move_is_a_new_directory(make, tmp_path, monkeypatch):
    """The tool-plugin claim, proven: a package shipping an `actions.ttl` puts a new KIND of
    row on the menu with no edit outside its own directory. The toy consults an oracle — a
    means no shipped package knows — and its row appears beside Observe and Acquire the moment
    the loader would find its file. Instances were always dynamic (premises in, rows out);
    this is the kinds joining them."""
    from assembly import loader

    toy = tmp_path / "actions.ttl"
    toy.write_text("""
@prefix orexis: <http://example.org/orexis#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
orexis:Consulting a orexis:Action ; orexis:means orexis:Consult ;
    orexis:takes orexis:about, <urn:toy#lever> ;
    orexis:available \"\"\"SELECT ?want ?about ?lever WHERE { VALUES (?want ?about) { $wants } BIND($me AS ?lever) }\"\"\" ;
    sh:construct "CONSTRUCT {} WHERE {}" .
""")
    real = loader.action_files()
    monkeypatch.setattr(loader, "action_files", lambda: real + (toy,))
    st = genesis_store()
    open_round_for(st, "fern")
    rows = find_steps(st, desires_build(st, "fern").abouts(FERN), FERN, picks_graph("fern"))
    kinds = {r.action.rsplit("#", 1)[-1] for r in rows}
    assert "Consulting" in kinds, "the toy package's kind must appear"
    assert {"Observing", "Acquiring"} <= kinds, "and the shipped kinds must survive it"


# --- whom a row serves (#218) --------------------------------------------

def test_a_duty_is_on_the_menu_and_a_stake_never_reaches_for_it(make):
    """The sovereign asking what an agent DOES gets its obligations beside its options — and asked
    about a PROPERTY it holds a region_want in, deliberation proposes none of them.

    An obligation IS a want — a Want whose premise is a claim (#471) — and reaches deliberation through the
    door that takes the want itself. What must not happen is an obligation answering a question about
    a region want: the honoured row exists because somebody else holds paper, and serving it is not
    a move this agent may choose for its own reasons. The search enforces it by filtering to
    chosen rows for anything that is not an obligation — the same filter the chain applied, for the
    same reason, one step further along.
    """
    from orexis_agent_deliberation.want import Want

    supplier = make("supplier")
    #  A ROW OWED TO SOMEONE EXISTS FOR A WANT ABOUT A DEBT, and names it: the market joins
    #  its serve to the want the derivation minted under *no overdue debts*, so with nothing owed
    #  there is nothing honoured among the steps, and with a claim presented there is.
    ledger = supplier.hosting().ledger
    me, picks = supplier.me.uri, picks_graph(supplier.id)
    def offered():
        return find_steps(supplier.beliefs, supplier.desires.abouts(me), me, picks)
    assert not [r for r in offered() if not r.is_own], "nothing owed, nothing honoured"
    ledger.owe("fern", "j-owed", amount_l=0.5)
    ledger.demanded("j-owed")
    [want] = [j.uri for j in ledger.obligations()]
    rows = offered()
    obligations = [r for r in rows if not r.is_own]
    assert obligations and all(r.want == want for r in obligations), \
        "the conduct surface includes what it honours, and each row names the want it serves"

    deliberator = supplier.deliberator
    duty_means = {r.action for r in obligations}
    #  Across the range rather than at one value, because a filter that leaks at one sign is a
    #  filter that leaks.
    for row in obligations:
        for value in (0.0, 0.5, 5.0, 50.0):
            region_want = ObservedWant(uri="urn:w", observed_property=row.value_of(ABOUT),
                                 value=value)
            assert deliberator.propose_for(region_want) not in duty_means, \
                "an obligation was proposed as if it were a choice"


def test_a_buyer_honours_nothing(make):
    """Fern holds no venue and no valve: everything on its menu is its own to choose."""
    fern = make("fern")
    assert all(r.is_own for r in find_steps(fern.beliefs, fern.desires.abouts(fern.me.uri), fern.me.uri, picks_graph(fern.id)))


# --- step 9: a desire, not a property and a value -----------------------------

def test_a_duty_is_pursued_through_the_lever_that_serves_its_counterparty(make):
    """`propose_for` takes the WANT, so an obligation reaches deliberation as what it is.

    Its means is not deduced here and could not be: it is the honoured row the market derives
    from the delivery chain, and the one that answers is the row honoured for exactly this
    counterparty. A host with two buyers must not serve one's claim through the other's valve,
    which is why the match is on the agent and not on the mode alone.
    """
    from orexis_capability_market.ower import OwedWant

    supplier = make("supplier")
    #  THE WANT THE DERIVATION MINTED for a presented claim, which is what the market's serve names
    #  (one-function-mints-every-want); a judgment written by hand names no debt, so no row
    #  names it, which is the stranger below.
    ledger = supplier.hosting().ledger
    ledger.owe("fern", "j-1", amount_l=0.5)
    ledger.demanded("j-1")
    obligation = next(j for j in ledger.obligations() if j.claim == "j-1")
    assert supplier.deliberator.propose_for(obligation) == \
        "http://example.org/orexis/market#Serving"

    stranger = OwedWant(uri="urn:o", claim="j-2", owed_to="urn:nobody")
    assert supplier.deliberator.propose_for(stranger) is None, \
        "a debt no lever of mine can reach proposes nothing — and stays owed"


def test_an_unpresented_duty_is_hot_and_still_not_acted_on(make):
    """Two questions, kept apart: how urgent a debt is, and whether anything is being asked
    yet. The holder waits for its own watch to be live (#132), so a host that doses on the
    strength of urgency alone would spend the water where nothing is looking — and a debt
    approaching its deadline that nobody has presented is exactly the case where the two
    answers differ."""
    from orexis_capability_market.ower import OwedWant

    supplier = make("supplier")
    standing = OwedWant(uri="urn:o", claim="j-3", pursuable=False,
                    owed_to="http://example.org/orexis/world/simulation#fern_agent")
    assert supplier.deliberator.propose_for(standing) is None


def test_a_search_that_answers_nothing_proposes_nothing(make, monkeypatch):
    """There is ONE path, and this is the assertion that says so.

    It replaces an equivalence test — `propose_for` against the bare-value door, at three
    values — which could only ever say that the two paths agreed. They did. What matters now
    is that there is no second path to fall back to when the first one comes up empty: a
    search that finds no candidate returns NOTHING, and the honest answer to that is to
    propose nothing, not to consult a chain that would have steered by the gap's sign.

    Made to fail by hand: a line standing in for the deleted deferral — return ACQUIRING where
    the plan comes back NOTHING — turns this red, which is what a guard that has never failed
    cannot claim about itself.
    """
    from orexis_agent_deliberation import planner as search
    from orexis_agent_deliberation.want import Want
    from orexis_agent_deliberation.planner import Planner

    fern = make("fern")
    monkeypatch.setattr(Planner, "plan", lambda self, desire, **kw: search.Plan(search.NOTHING))
    thirsty = ObservedWant(uri=region_want_of(fern).uri, observed_property=MOISTURE,
                           value=0.10)
    assert fern.deliberator.propose_for(thirsty) is None, \
        "the search said it had nothing to weigh, and something else answered anyway"


def test_every_want_is_drawn_by_the_one_module_that_sees_them_all(make):
    """One row per want, tagged by the WANT — the sovereign's correction to a first draft that
    keyed the panel on the property.

    A property cannot name every want: freshness is per instrument, an obligation is per counterparty.
    So a graph grouped by property could only ever draw region wants, and one axis over every kind
    of want would stay a claim rather than something you can look at.

    A obligation is tagged by whom it is owed to and NEVER by its claim: a jti is unique per round, so
    tagging by it would mint a series every time the society traded and grow the store's
    cardinality with its history.
    """
    fern = make("fern")
    rows = [(tags, fields) for meas, tags, fields in
            next(m for m in fern.modules if m.name == "deliberation").series()
            if meas == "agent_want"]

    assert rows, "an agent that wants things reports each of them"
    #  TWO FIGURES, and neither is an urgency. The row carried one — a number four packages
    #  each computed their own way, ahead of the search that was the only thing able to
    #  compare them — and what a panel per want can still say is whether it is unmet and
    #  whether anything the agent can do answers it.
    assert all(set(f) == {"unmet", "answered"} for _, f in rows), \
        "whether it is unmet, and whether anything answers it"
    assert all(f["unmet"] in (0.0, 1.0) and f["answered"] in (0.0, 1.0) for _, f in rows), \
        "both are flags, or the axis lies"
    tags = {t["want"] for t, _ in rows}
    assert len(tags) == len(rows), "one line per want, not several sharing a name"
    assert not any(len(t) > 60 for t in tags), \
        "a tag carrying a jti would mint a new series per round — obligations are tagged by whom"


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
    from orexis_agent_deliberation import trace

    #  WITH A READING, because an agent that has never looked does not plan: `propose_for`
    #  answers an unmeasured or stale want with Observe before any search runs (#240). So an
    #  agent at rest reports zeros here — honestly, since nothing was deliberated — and a test
    #  that used one would have pinned the figures of a pass that never happened.
    fern = make("fern", genesis_store({"fern": 0.10}))
    rows = {measurement: fields for measurement, _, fields in
            next(m for m in fern.modules if m.name == "deliberation").series()}
    planning = rows["agent_planning"]

    assert planning["seconds"] > 0, "a pass that took no time did not happen"
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

    from orexis_agent_deliberation import trace

    fern = make("fern", genesis_store({"fern": 0.10}))
    next(m for m in fern.modules if m.name == "deliberation").series()   # fill the trace

    trace.effort(fern.desires.query)                                 # warm
    started = time.monotonic()
    for _ in range(5):
        trace.effort(fern.desires.query)
    each = (time.monotonic() - started) / 5

    assert each < 0.05, f"reading the figures took {each*1000:.0f}ms — it should be under 1ms"


def test_a_plan_landing_after_the_wants_expiry_is_not_one(make):
    """#472: an obligation's scope is `orexis:Within`, and the search holds every candidate's
    landing time to the room left before the want expires. A serve that would land after the
    claim lapses is discarded before the met-test can crown it — the plan comes back with no
    steps, and the debt stays owed and visible, which is the evidence-producing posture. The
    same want with a generous window keeps the very same plan: the control that proves the
    gate did it, and not the fixture."""
    from datetime import datetime, timedelta, timezone

    from orexis_capability_market.ower import OwedWant
    from orexis_agent_deliberation.planner import Planner

    supplier = make("supplier", genesis_store({("barrel1", STORED): 3.0}))
    now = datetime.now(timezone.utc)
    #  THROUGH THE LEDGER (#635): the record carries the debt's own met-test, and a row
    #  written by hand without one is a want the planner can no longer judge.
    ledger = supplier.hosting().ledger
    debt = ledger.owe("fern", "w1", amount_l=0.5)
    assert debt == "http://example.org/orexis#obligation.w1"
    ledger.demanded("w1")
    #  THE WANT IS THE DERIVATION'S, not the debt (one-function-mints-every-want): presented, the
    #  debt is a want under "no overdue debts", about that debt, and it is the want the
    #  search is handed — pointing at the desire's met-test, which reads a serve as met.
    uri = next(j.uri for j in ledger.obligations() if j.claim == "w1")
    assert uri.startswith(f"{supplier.me.uri}.no_overdue_debts.pursued.")

    def planned(seconds_left):
        want = OwedWant(uri=uri, claim="w1",
                    owed_to="http://example.org/orexis/world/simulation#fern_agent",
                    expires=now + timedelta(seconds=seconds_left))
        return Planner(supplier, supplier.me).plan(want)

    generous = planned(86400.0)
    assert generous.steps, \
        "the control: with a day of room the serve is a plan — if this fails, the gate is untested"
    assert not planned(0.5).steps, \
        "half a second of room is less than any serve lands in, and a late world answers nothing"


def test_of_two_worlds_the_same_urgency_apart_the_cheaper_is_the_plan(make, tmp_path,
                                                                      monkeypatch):
    """#466's done-when: the ranking gains its second axis, and only for ties.

    Two toy levers repair the same region want identically — the same predicted reading, which
    lands in fern's region, so both candidate worlds are MET and neither is better than the
    other on the only axis left — and differ in exactly one declared figure:
    `orexis:costs`, five against three. Each RETRACTS the reading it replaces, as every real
    effect does: the sensed graph holds one node per (subject, property), and a toy that only
    added left the world claiming 0.30 AND 0.50 — which the want's met-test reads as still
    violated, where the measure it used to be scored by read the newest and did not.
    Distinct marker triples keep the two worlds distinct,
    or cycle detection would discard the second as somewhere already seen before the ranking
    ever compared them. Whatever order the menu yields them in, the plan must be the cheaper
    one — which proves the tie-break from both sides with one assertion: if the cheap toy
    came first, the dear one must not displace it; if the dear one came first, the cheap one
    must."""
    from assembly import loader
    from orexis_agent_deliberation.planner import Planner

    def toy(name, cost, mark):
        return f"""
toy:{name} a orexis:Action ;
    orexis:takes orexis:about, <urn:toy#lever> ;
    orexis:available \"\"\"SELECT ?want ?about ?lever WHERE {{ VALUES (?want ?about) {{ $wants }} BIND($me AS ?lever) }}\"\"\" ;
    orexis:costs \"\"\"SELECT ?cost WHERE {{ BIND({cost} AS ?cost) }}\"\"\" ;
    sh:construct \"\"\"CONSTRUCT {{
            ?obs a <http://www.w3.org/ns/sosa/Observation> ;
                 <http://www.w3.org/ns/sosa/hasFeatureOfInterest> $subject ;
                 <http://www.w3.org/ns/sosa/observedProperty> $about ;
                 <http://www.w3.org/ns/sosa/resultTime> ?now ;
                 <http://www.w3.org/ns/sosa/hasSimpleResult> 0.50 .
            <urn:mark:{mark}> <urn:took> <urn:it> .
        }} WHERE {{ BIND(BNODE() AS ?obs) BIND(NOW() AS ?now) }}\"\"\" ;
    orexis:retracts \"\"\"CONSTRUCT {{ ?obs ?p ?o }} WHERE {{
            ?obs <http://www.w3.org/ns/sosa/hasFeatureOfInterest> $subject ;
                 <http://www.w3.org/ns/sosa/observedProperty> $about ;
                 <http://www.w3.org/ns/sosa/hasSimpleResult> ?was ;
                 ?p ?o . }}\"\"\" .
"""

    toys = tmp_path / "actions.ttl"
    toys.write_text("@prefix orexis: <http://example.org/orexis#> .\n"
                    "@prefix toy: <urn:toy#> .\n"
                    "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                    + toy("Dearly", 5.0, "dear") + toy("Cheaply", 3.0, "cheap"))
    real = loader.action_files()
    monkeypatch.setattr(loader, "action_files", lambda: real + (toys,))

    fern = make("fern", genesis_store({("fern", MOISTURE): 0.30}))
    plan = Planner(fern, fern.me).plan(region_want_of(fern))

    assert plan.steps, "both toys bring 0.30 into the region — one must be taken"
    assert plan.steps[0].action == "urn:toy#Cheaply", \
        "same urgency either way round, so the declared cost is the only thing left to decide"


def test_among_plans_that_achieve_the_want_cost_alone_decides(make, tmp_path, monkeypatch):
    """The sovereign's two-stage cut, stage two: urgency is the desire's term and cost is
    the action's — urgency picks WHICH want, and among plans that ACHIEVE it, cost alone
    decides. The first-met-returns shortcut crowned whichever achiever the menu yielded
    first; this authors two achievers (both predict 0.55, inside the region) differing only
    in the declared cost, and the cheaper must win from either order."""
    from assembly import loader
    from orexis_agent_deliberation.planner import Planner

    def toy(name, cost, mark):
        return f"""
toy:{name} a orexis:Action ;
    orexis:takes orexis:about, <urn:toy#lever> ;
    orexis:available \"\"\"SELECT ?want ?about ?lever WHERE {{ VALUES (?want ?about) {{ $wants }} BIND($me AS ?lever) }}\"\"\" ;
    orexis:costs \"\"\"SELECT ?cost WHERE {{ BIND({cost} AS ?cost) }}\"\"\" ;
    orexis:retracts \"\"\"CONSTRUCT {{ ?old ?p ?o }} WHERE {{
            {{ ?old <http://www.w3.org/ns/sosa/hasFeatureOfInterest> $subject ;
                                 <http://www.w3.org/ns/sosa/observedProperty> $about .
                            ?old ?p ?o }} }}\"\"\" ;
    sh:construct \"\"\"CONSTRUCT {{
            ?obs a <http://www.w3.org/ns/sosa/Observation> ;
                 <http://www.w3.org/ns/sosa/hasFeatureOfInterest> $subject ;
                 <http://www.w3.org/ns/sosa/observedProperty> $about ;
                 <http://www.w3.org/ns/sosa/resultTime> ?now ;
                 <http://www.w3.org/ns/sosa/hasSimpleResult> 0.55 .
            <urn:mark:{mark}> <urn:took> <urn:it> .
        }} WHERE {{ BIND(BNODE() AS ?obs) BIND(NOW() AS ?now) }}\"\"\" ;
    orexis:retracts \"\"\"CONSTRUCT {{ ?obs ?p ?o }} WHERE {{
            ?obs <http://www.w3.org/ns/sosa/hasFeatureOfInterest> $subject ;
                 <http://www.w3.org/ns/sosa/observedProperty> $about ;
                 <http://www.w3.org/ns/sosa/hasSimpleResult> ?was ;
                 ?p ?o . }}\"\"\" .
"""

    toys = tmp_path / "actions.ttl"
    toys.write_text("@prefix orexis: <http://example.org/orexis#> .\n"
                    "@prefix toy: <urn:toy#> .\n"
                    "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                    + toy("GoldPlated", 5.0, "gold") + toy("Thrifty", 3.0, "thrift"))
    real = loader.action_files()
    monkeypatch.setattr(loader, "action_files", lambda: real + (toys,))

    fern = make("fern", genesis_store({("fern", MOISTURE): 0.30}))
    plan = Planner(fern, fern.me).plan(region_want_of(fern))

    assert plan.outcome == "satisfied" and plan.steps, \
        "both toys land 0.55 inside 0.45-0.65 — the want is achievable in one step"
    assert plan.steps[0].action == "urn:toy#Thrifty", \
        "two ways of achieving one want differ only in cost, and the cheaper must be the plan"
