"""Capabilities are derived from hardware and wiring — never declared.

These run the real derivation rules over the real genesis world, so they check the thing the
architecture actually rests on: that what an agent can do follows from what it is connected
to, and cannot drift from it.
"""

import pytest
import rdflib

from agent import genesis

from assembly import loader
from orexis_modality_graph.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH
from agent.world import WorldError, load_world
from orexis_capability_actuation import ACTUATION
from orexis_capability_market import BIDDING, HOSTING, PAY_AS_BID
from orexis_capability_sensing import LISTENING, SUBSCRIBING
from orexis_capability_reporting import STORING
from orexis_capability_review import RECKONING

#  Granted to every agent by the fact of a bus in the world (the-kernel-has-no-mailbox).
LINKING = "http://example.org/orexis/mqtt#Linking"

from conftest import genesis_store, query_fn, load_wired


@pytest.fixture
def me(query):
    return lambda agent_id: load_wired(query, agent_id)


# --- what the shipped world derives ----------------------------------------

def test_plant_agent_gets_subscribing_and_bidding(me):
    """Wired to a scheduled sensor and into a market — so it perceives and it buys.

    And given room to move on its cadence, so it may also re-pick it. And acting for a plant
    that states what it needs, so it wants something — and, wanting with levers to act, it may
    commit to acting and decide when to. SIX premises, six capabilities, none of them written
    down: two follow from what it is wired to, one from what its world allows it, one from
    having a stake at all, and two from the stake meeting the wiring — keeping and deciding,
    granted by the same fact and separate because their replaceable parts differ.
    """
    assert me("fern").capabilities == {
        SUBSCRIBING, BIDDING, RECKONING, STORING, LINKING}


def test_a_mandate_whose_ends_meet_grants_nothing(me):
    """`succulent`'s cadence is pinned — `review:notBelow 900 ; review:notAbove 900`.

    That is not an oversight: it is how an author says a figure is not up for review, by leaving
    nowhere to go rather than by a flag somewhere saying not to look, and `review.Range.fixed`
    reads it exactly that way. Granting on the mere *presence* of a mandate would hand it a
    capability whose every arising could only conclude nothing — a reviewer waking for ever to
    re-derive that there is one permitted value and it already holds it.

    Latitude is the grant, so where there is none there is nothing to grant. The wider rule is
    AGENTS.md's: a capability nothing could vary is a function wearing a capability's name.
    """
    succulent = me("succulent")
    assert RECKONING not in succulent.capabilities
    # STORING is there and RECKONING is not, in one agent — which is the whole distinction
    # between a MANDATORY capability and a granted one. Reporting is not conditional on
    # latitude, because an agent permitted to fall silent cannot be told from a dead one; the
    # ability to re-pick is, because with nowhere to go there is nothing to re-pick.
    assert succulent.capabilities == {SUBSCRIBING, BIDDING, STORING, LINKING}


def test_supplier_gets_hosting_actuation_and_matching(me):
    """It owns the venue and the valves — so it sells and it opens them.

    And it says how it matches bids, so it can also *run* what it convenes. Hosting is the
    protocol — announce, collect, issue; matching, which turns bids into an allocation with
    prices, is a separate ability, because there is more than one defensible answer and which
    one is in force changes what a rational bidder should offer.
    """
    from orexis_capability_sensing.terms import LISTENING

    #  Plus what the barrel arcs earned: LISTENING (arc 1 — it sees its stock) and, since it
    #  acts for a barrel that states its needs (arc 2); and since the city exists
    #  (arc 4), BIDDING — the city's pipe reaches its barrel, so the dealer's buy side derives
    #  from the plumbing exactly as a fern's does.
    #
    #  KEEPING and REFLEX were in this set and are not capabilities any more, nor is arc 5's
    #  PLANNING: committing and deciding are the kernel's, granted by nothing, and the dealer's
    #  depth turned out to be a clause rather than a member. What the dealer premise still buys
    #  is pinned in test_deliberation, against the fact instead of the grant.
    #  DEDUCING and OWING were here and are not capabilities any more: wanting and owing are
    #  the mind's, and the mind is the kernel's. What #233's split was really about — the city
    #  owes and wants nothing, a plant wants and owes nothing — is asserted against the data in
    #  test_the_city_owes_without_wanting_and_a_plant_wants_without_owing below.
    
    assert me("supplier").capabilities == {HOSTING, ACTUATION, PAY_AS_BID, STORING, LISTENING,
                                           BIDDING, LINKING}


def test_the_city_owes_without_wanting_and_a_plant_wants_without_owing():
    """The split #233 asked for, stated as the two agents that separate it.

    The city keeps a ledger and deduces nothing: it acts for a mains that states a capacity and
    no ranges, so it has no stake and wants nothing for itself — and it hosts a venue and holds
    the valve that serves it, so others may demand its lever. A plant is the mirror: every want
    of its own, no lever anybody may demand, no ledger.

    Both directions asserted, because a premise that is too WIDE is as wrong as one too narrow
    and only one of those is visible from the agent that was broken.

    `desire:Owing` and `desire:Deducing` were the two capabilities this separated, and neither
    is one now — wanting and owing are the mind's, and every agent has a mind. The SPLIT is
    unchanged and still worth asserting; what changed is that it is a fact about each agent's
    data rather than about what its world granted. The city holds no region because its mains
    states no ranges; the fern's menu holds no honoured row because nobody may demand its
    lever. Those were always the facts underneath the two grants.
    """
    from agent.afforder import affordances_of
    from orexis_capability_sensing.regions import regions_of

    from orexis_modality_graph.ontology import beliefs_graph
    from conftest import desires_build

    st = genesis_store()
    uri = lambda who: load_wired(st.query, who).uri

    def honoured(who):
        return [r for r in affordances_of(st.query, uri(who), desires_build(st, who).query_union, beliefs_graph(who))
                if not r.is_own]

    assert not regions_of(desires_build(st, "city").query_union, uri("city")), \
        "a mains states no ranges — the city wants nothing for itself"
    assert regions_of(desires_build(st, "fern").query_union, uri("fern")), \
        "a plant states ranges, so it holds regions of its own"

    assert honoured("city"), "the city hosts a venue and holds the valve that serves it"
    assert not honoured("fern"), "a plant holds no lever anyone may demand"


def test_only_a_host_matches(me):
    """A bidder has no auction to set terms for — the matching is the convenor's."""
    assert PAY_AS_BID not in me("fern").capabilities


def test_supplier_commands_no_cadence_and_buys_upstream(me):
    """Half of what this test guarded fell to arc 4, and the half that fell is the story.

    It asserted the supplier neither perceives on a commanded clock NOR buys. The first
    stands — its one sensor announces, so Listening and never Subscribing. The second
    inverted the day the city opened shop: bidsIn derives from the pipe that reaches its
    barrel plus the stake it holds in it, so the dealer BUYS now, and nothing was declared
    to make it so.
    """
    supplier = me("supplier")
    assert not supplier.can(SUBSCRIBING)
    assert supplier.can(BIDDING)


def test_plant_agent_cannot_actuate(me):
    """Winning water is not the same as being able to open a valve."""
    fern = me("fern")
    assert not fern.can(ACTUATION)
    assert fern.actuators == ()


# --- the hardware decides which sensing you get -------------------------

def _world_with_push_sensor():
    """Swap fern's board for one that pushes on its own clock, and re-derive.

    EVERY sensor fern polls, not one named one. This used to edit `<http://example.org/orexis/world/simulation#moisture_sensor_fern>`
    alone, which was the whole of fern's wiring when the world it ran against had one sensor per
    agent. It has two now — a probe and a thermometer sharing the board's one message — and
    switching only the probe leaves the thermometer scheduled, so the agent keeps `Subscribing`
    as well and the test reads as a failure when the design is working exactly as
    `who-holds-the-clock` describes. What is under test is that the HARDWARE decides, so the
    edit has to be about the board rather than about one channel on it.

    Only the RATIFIED fact is edited — the sense mode, which is the sovereign's. The old
    capability is not deleted here because it is not the world's to delete: it was computed, it
    lives in the derived graph, and the way to be rid of a conclusion is to drop the conclusions
    and recompute. Clearing before re-running is exactly what `refresh_public` does, and skipping
    it leaves last derivation's answer sitting beside this one — which is how this test read
    `Listening` AND `Subscribing` and called it a pass.
    """
    st = genesis_store()
    st.update(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?s sensing:senseMode sensing:ScheduledProcedure }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?s sensing:senseMode sensing:PushProcedure }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{
                 <http://example.org/orexis/world/simulation#fern_agent> sensing:polls ?s .
                 ?s sensing:senseMode sensing:ScheduledProcedure }} }}
    """)
    st.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        # Through `substitute`, exactly as `refresh_public` runs them: a rule names no graph,
        # so running one without filling `$given` and `$derived` in is not a rule at all.
        st.update(genesis.substitute(rule.read_text(), st))
    return st


def test_push_hardware_yields_listening_not_subscribing():
    """The same agent, the same wiring — a different board, a different capability."""
    me = load_wired(query_fn(_world_with_push_sensor()), "fern")
    assert me.can(LISTENING)
    assert not me.can(SUBSCRIBING)


def test_swapping_the_board_does_not_touch_the_agent():
    """Nothing about fern_agent was edited — only the device it is wired to."""
    me = load_wired(query_fn(_world_with_push_sensor()), "fern")
    assert me.can(BIDDING)  # its market wiring is untouched
    #  A SET, not a sequence: the claim is that the wiring is untouched, and the row order a
    #  store returns is the engine's own — a load-order change flipped it once and only this
    #  assertion noticed, which was this test asserting more than it meant.
    assert sorted(s.local_id for s in me.sensors) == ["air_temp_fern", "moisture_sensor_fern"]


# --- the same hardware, a different world ----------------------------------

def test_the_smallest_world_yields_sensing_and_nothing_else():
    """world/sensing: the same agent id, the same board, plumbed into no market.

    Nothing in that world declares the agent sensor-only — it is the same derivation the
    society runs, over thinner wiring. This is the check that a capability can genuinely
    stand alone, which is the whole claim of deriving them.
    """
    me = load_wired(query_fn(genesis_store(world="sensing")), "fern")
    assert me.capabilities == {SUBSCRIBING, RECKONING, STORING, LINKING}
    assert not me.can(BIDDING) and not me.can(ACTUATION)
    assert me.markets == () and me.actuators == ()
    assert me.acts_for is None  # it advances nobody's interest; it only records


def test_the_board_did_not_change_only_the_model_did():
    """The point of the two worlds sharing device ids: one flashed board, either society.

    This used to compare the two sensor LISTS and require them equal, which was a stronger
    claim than the invariant needs and stopped being true when `sensing` began reading the
    KY-015's temperature and humidity (#51). What must hold is that the BOARD is the same: one
    credential, one topic, publishing one message. How many values a world chooses to take out
    of that message is the world's business, and a field nobody points at is simply ignored —
    which is why the identical flashed board still works in either.
    """
    watching = load_wired(query_fn(genesis_store(world="sensing")), "fern")
    buying = load_wired(query_fn(genesis_store(world="simulation")), "fern")

    assert {s.reading_topic for s in watching.sensors} == \
           {s.reading_topic for s in buying.sensors}, "one channel, whichever world is seeded"

    soil = {s.local_id: s for s in watching.sensors} | {}
    for world in (watching, buying):
        probe = next(s for s in world.sensors if s.local_id == "moisture_sensor_fern")
        assert probe.command_topic == soil["moisture_sensor_fern"].command_topic
        assert probe.reading_pointer == "/moisture"  # named for what it measures, both worlds alike

    # The same wire, read for more. Strictly more properties here, strictly fewer abilities.
    assert {s.observes for s in buying.sensors} < {s.observes for s in watching.sensors}
    assert watching.capabilities < buying.capabilities


# --- an agent knows only itself --------------------------------------------

def test_agent_sees_only_its_own_sensors(me):
    for agent_id in ("fern", "tomato", "succulent"):
        assert all(s.subject_id == agent_id for s in me(agent_id).sensors)


def test_unknown_agent_id_fails_loudly(query):
    with pytest.raises(WorldError, match="knows no agent"):
        load_wired(query, "orchid")


# --- the world itself ------------------------------------------------------

def test_world_is_found_by_type_not_by_name(query):
    assert load_world(query).version == 1


def test_market_channels_are_stated(me):
    market = me("fern").markets[0]
    assert market.offer_topic and market.bid_topic and market.claim_topic
    assert market.capacity_l == 5.0  # the allocation ceiling, from the source


def test_valve_carries_its_own_calibration(me):
    valve = me("supplier").actuator_for("tomato")
    assert valve.local_id == "valve_tomato"
    assert (valve.ml_per_second, valve.max_dose_ml) == (10.0, 1000.0)
    assert valve.command_topic  # stated, not built from a naming convention


def test_no_actuator_for_an_unplumbed_subject(me):
    assert me("supplier").actuator_for("orchid") is None


# --- a firmware describes itself, and the board just says which one it runs (#175) -------------

def test_a_boards_mode_is_entailed_from_its_firmware_class():
    """The sensing world states NO senseMode and NO mc:firmware for its real board any more:
    the device is typed governed:Node, and both facts arrive from
    firmware/moisture-sensor/ontology.ttl through the closure's hasValue rule — a datasheet
    fact whose sheet is src/main.cpp. The derivation, the runtime and the shapes all read the
    conclusion."""
    from orexis_capability_sensing.terms import SCHEDULED, SUBSCRIBING

    me = load_wired(query_fn(genesis_store(world="sensing")), "fern")
    assert SUBSCRIBING in me.capabilities, "the grant must flow through the entailed mode"
    probe = next(s for s in me.sensors if s.local_id == "moisture_sensor_fern")
    assert probe.sense_mode == SCHEDULED, "the runtime must read the entailed mode"


def test_the_firmware_self_descriptions_are_still_found():
    """The glob guard, in the spirit of test_store's: moving files has twice emptied a source
    glob without failing anything, and a firmware tree that quietly stopped loading would
    strip every typed board of its mode at the next genesis."""
    from assembly import loader

    found = sorted(str(p) for p in loader.ontology_files() if "/firmware/" in str(p))
    assert len(found) >= 2, "the firmware ontologies stopped being loaded"
    assert any("moisture-sensor" in f for f in found)
    assert any("moisture-sentinel" in f for f in found)


def test_the_alarm_promise_is_entailed_from_the_governed_class():
    """#181: the sensing world no longer hand-states ssn:implements sensing:AlarmProcedure —
    the flashed image watches its analog channel unconditionally, so the promise is the
    firmware class's, arriving through the same hasValue closure as the sense mode. Only the
    connecting device is typed, so the promise reaches the moisture channel and never the
    DHT's — per channel by construction, with nobody saying so per world."""
    me = load_wired(query_fn(genesis_store(world="sensing")), "fern")
    probe = next(s for s in me.sensors if s.local_id == "moisture_sensor_fern")
    assert probe.alarm, "the promise must flow from governed:Node to the connecting device"
    air = next(s for s in me.sensors if s.local_id == "air_temp_fern")
    assert not air.alarm, "an untyped channel promises nothing — honest by absence"


# --- imports follow grants (#216) -------------------------------------------

def test_a_package_whose_import_fails_costs_only_the_agents_granted_it(tmp_path, monkeypatch):
    """The declared degrade path, synthesised: a package whose optional extra is missing.

    Before #216 the loader imported every package to build the registry, so ONE missing
    dependency — `orexis[consulting]` and its model client — crashed every agent in the
    society at import time, including the ones never granted the capability. Now a
    capability names its owning package by NAMESPACE (no Python read to find out), so the
    failure is scoped: the granted agent gets the honest "nothing provides it" path, and
    everyone else never touches the package at all.
    """
    from assembly import loader

    pkg = tmp_path / "capability" / "oracular"
    pkg.mkdir(parents=True)
    (pkg / "ontology.ttl").write_text(
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "<http://example.org/orexis/oracular> a owl:Ontology .\n")
    (pkg / "__init__.py").write_text("import definitely_not_installed  # the missing extra\n")

    real = loader.of_kind
    monkeypatch.setattr(loader, "of_kind", lambda kind: real(kind) + (
        loader.Package(path=pkg, kind="capability", name="oracular"),))
    loader._namespace_owners.cache_clear()

    consulting = "http://example.org/orexis/oracular#Consulting"
    assert loader.registry_for({consulting}) == {}, "granted: unprovided, and no crash"
    assert set(loader.registry_for({SUBSCRIBING})) == {SUBSCRIBING}, \
        "ungranted: the broken package is never even imported"
    loader._namespace_owners.cache_clear()


def test_a_fern_imports_no_actuation(monkeypatch):
    """The economy, stated as a fact rather than hoped for: the packages a grant reaches are
    the packages imported. Fern holds no actuator, so actuation's Python — and whatever a
    future package brings with it — stays out of its process."""
    from assembly import loader

    imported = []
    real = loader._provider_in
    monkeypatch.setattr(loader, "_provider_in",
                        lambda p, c: (imported.append(p.name), real(p, c))[1])
    loader.registry_for(load_wired(query_fn(genesis_store()), "fern").capabilities)
    assert "actuation" not in imported
    assert "sensing" in imported and "market" in imported
