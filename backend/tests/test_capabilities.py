"""Capabilities are derived from hardware and wiring — never declared.

These run the real derivation rules over the real genesis world, so they check the thing the
architecture actually rests on: that what an agent can do follows from what it is connected
to, and cannot drift from it.
"""

import pytest
import rdflib

from agora import loader
from agora.ontology import WORLD_GRAPH
from agora.world import WorldError, load_self, load_world
from capabilities.actuation import ACTUATION
from capabilities.market import BIDDING, HOSTING
from capabilities.perception import LISTENING, POLLING

from conftest import genesis_dataset, query_fn


@pytest.fixture
def me(query):
    return lambda agent_id: load_self(query, agent_id)


# --- what the shipped world derives ----------------------------------------

def test_plant_agent_gets_polling_and_bidding(me):
    """Wired to a pull sensor and into a market — so it perceives and it buys."""
    assert me("fern").capabilities == {POLLING, BIDDING}


def test_supplier_gets_hosting_and_actuation(me):
    """It owns the venue and the valves — so it sells and it opens them."""
    assert me("supplier").capabilities == {HOSTING, ACTUATION}


def test_supplier_neither_perceives_nor_buys(me):
    supplier = me("supplier")
    assert not supplier.can(POLLING)
    assert not supplier.can(BIDDING)


def test_plant_agent_cannot_actuate(me):
    """Winning water is not the same as being able to open a valve."""
    fern = me("fern")
    assert not fern.can(ACTUATION)
    assert fern.actuators == ()


# --- the hardware decides which perception you get -------------------------

def _world_with_push_sensor() -> rdflib.Dataset:
    """Swap fern's board for one that pushes on its own clock, and re-derive."""
    ds = genesis_dataset()
    world = ds.graph(rdflib.URIRef(WORLD_GRAPH))
    world.update("""
        PREFIX ag: <http://example.org/agora#>
        DELETE { ag:moisture_sensor_fern ag:senseMode ag:Pull .
                 ag:fern_agent ag:hasCapability ag:Polling }
        INSERT { ag:moisture_sensor_fern ag:senseMode ag:Push }
        WHERE  { ag:moisture_sensor_fern ag:senseMode ag:Pull }
    """)
    for rule in loader.rule_files():
        ds.update(rule.read_text())
    return ds


def test_push_hardware_yields_listening_not_polling():
    """The same agent, the same wiring — a different board, a different capability."""
    me = load_self(query_fn(_world_with_push_sensor()), "fern")
    assert me.can(LISTENING)
    assert not me.can(POLLING)


def test_swapping_the_board_does_not_touch_the_agent():
    """Nothing about fern_agent was edited — only the device it is wired to."""
    me = load_self(query_fn(_world_with_push_sensor()), "fern")
    assert me.can(BIDDING)  # its market wiring is untouched
    assert [s.local_id for s in me.sensors] == ["moisture_sensor_fern"]


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
