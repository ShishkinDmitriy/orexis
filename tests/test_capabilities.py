"""Capabilities are derived from hardware and wiring — never declared.

These run the real derivation rules over the real genesis world, so they check the thing the
architecture actually rests on: that what an agent can do follows from what it is connected
to, and cannot drift from it.
"""

import pytest
import rdflib

from agent import genesis, loader
from agent.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH
from agent.world import WorldError, load_self, load_world
from agent.capabilities.actuation import ACTUATION
from agent.capabilities.market import BIDDING, HOSTING
from agent.capabilities.matching import PAY_AS_BID
from agent.capabilities.perception import LISTENING, SUBSCRIBING
from agent.capabilities.review import RECKONING

from conftest import genesis_store, query_fn


@pytest.fixture
def me(query):
    return lambda agent_id: load_self(query, agent_id)


# --- what the shipped world derives ----------------------------------------

def test_plant_agent_gets_subscribing_and_bidding(me):
    """Wired to a scheduled sensor and into a market — so it perceives and it buys.

    And given room to move on its cadence, so it may also re-pick it. Three premises, three
    capabilities, none of them written down: two follow from what it is wired to and the third
    from what its world allows it.
    """
    assert me("fern").capabilities == {SUBSCRIBING, BIDDING, RECKONING}


def test_a_mandate_whose_ends_meet_grants_nothing(me):
    """`succulent`'s cadence is pinned — `ag:notBelow 900 ; ag:notAbove 900`.

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
    assert succulent.capabilities == {SUBSCRIBING, BIDDING}


def test_supplier_gets_hosting_actuation_and_matching(me):
    """It owns the venue and the valves — so it sells and it opens them.

    And it says how it matches bids, so it can also *run* what it convenes. Hosting is the
    protocol — announce, collect, issue; matching, which turns bids into an allocation with
    prices, is a separate ability, because there is more than one defensible answer and which
    one is in force changes what a rational bidder should offer.
    """
    assert me("supplier").capabilities == {HOSTING, ACTUATION, PAY_AS_BID}


def test_only_a_host_matches(me):
    """A bidder has no auction to set terms for — the matching is the convenor's."""
    assert PAY_AS_BID not in me("fern").capabilities


def test_supplier_neither_perceives_nor_buys(me):
    supplier = me("supplier")
    assert not supplier.can(SUBSCRIBING)
    assert not supplier.can(BIDDING)


def test_plant_agent_cannot_actuate(me):
    """Winning water is not the same as being able to open a valve."""
    fern = me("fern")
    assert not fern.can(ACTUATION)
    assert fern.actuators == ()


# --- the hardware decides which perception you get -------------------------

def _world_with_push_sensor():
    """Swap fern's board for one that pushes on its own clock, and re-derive.

    Only the RATIFIED fact is edited — the sense mode, which is the sovereign's. The old
    capability is not deleted here because it is not the world's to delete: it was computed, it
    lives in the derived graph, and the way to be rid of a conclusion is to drop the conclusions
    and recompute. Clearing before re-running is exactly what `refresh_public` does, and skipping
    it leaves last derivation's answer sitting beside this one — which is how this test read
    `Listening` AND `Subscribing` and called it a pass.
    """
    st = genesis_store()
    st.update(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{
                 ag:moisture_sensor_fern ag:senseMode ag:Scheduled }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
                 ag:moisture_sensor_fern ag:senseMode ag:Push }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{
                 ag:moisture_sensor_fern ag:senseMode ag:Scheduled }} }}
    """)
    st.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        # Through `substitute`, exactly as `refresh_public` runs them: a rule names no graph,
        # so running one without filling `$given` and `$derived` in is not a rule at all.
        st.update(genesis.substitute(rule.read_text(), st))
    return st


def test_push_hardware_yields_listening_not_subscribing():
    """The same agent, the same wiring — a different board, a different capability."""
    me = load_self(query_fn(_world_with_push_sensor()), "fern")
    assert me.can(LISTENING)
    assert not me.can(SUBSCRIBING)


def test_swapping_the_board_does_not_touch_the_agent():
    """Nothing about fern_agent was edited — only the device it is wired to."""
    me = load_self(query_fn(_world_with_push_sensor()), "fern")
    assert me.can(BIDDING)  # its market wiring is untouched
    assert [s.local_id for s in me.sensors] == ["moisture_sensor_fern"]


# --- the same hardware, a different world ----------------------------------

def test_the_smallest_world_yields_perception_and_nothing_else():
    """world/sensing: the same agent id, the same board, plumbed into no market.

    Nothing in that world declares the agent sensor-only — it is the same derivation the
    society runs, over thinner wiring. This is the check that a capability can genuinely
    stand alone, which is the whole claim of deriving them.
    """
    me = load_self(query_fn(genesis_store(world="sensing")), "fern")
    assert me.capabilities == {SUBSCRIBING, RECKONING}
    assert not me.can(BIDDING) and not me.can(ACTUATION)
    assert me.markets == () and me.actuators == ()
    assert me.acts_for is None  # it advances nobody's interest; it only records


def test_the_board_did_not_change_only_the_model_did():
    """The point of the two worlds sharing device ids: one flashed board, either society."""
    watching = load_self(query_fn(genesis_store(world="sensing")), "fern")
    buying = load_self(query_fn(genesis_store(world="society")), "fern")
    assert [s.local_id for s in watching.sensors] == [s.local_id for s in buying.sensors]
    assert [s.reading_topic for s in watching.sensors] == \
           [s.reading_topic for s in buying.sensors]
    assert watching.capabilities < buying.capabilities  # strictly fewer, same hardware


# --- an agent knows only itself --------------------------------------------

def test_agent_sees_only_its_own_sensors(me):
    for agent_id in ("fern", "tomato", "succulent"):
        assert all(s.subject_id == agent_id for s in me(agent_id).sensors)


def test_unknown_agent_id_fails_loudly(query):
    with pytest.raises(WorldError, match="knows no agent"):
        load_self(query, "orchid")


# --- the world itself ------------------------------------------------------

def test_world_is_found_by_type_not_by_name(query):
    assert load_world(query).version == 1


def test_market_channels_are_stated(me):
    market = me("fern").markets[0]
    assert market.offer_topic and market.bid_topic and market.voucher_topic
    assert market.capacity_l == 5.0  # the allocation ceiling, from the source


def test_valve_carries_its_own_calibration(me):
    valve = me("supplier").actuator_for("tomato")
    assert valve.local_id == "valve_tomato"
    assert (valve.ml_per_second, valve.max_dose_ml) == (10.0, 1000.0)
    assert valve.command_topic  # stated, not built from a naming convention


def test_no_actuator_for_an_unplumbed_subject(me):
    assert me("supplier").actuator_for("orchid") is None
