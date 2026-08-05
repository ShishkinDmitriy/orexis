"""SHACL — the constitution as code, one shapes module per capability.

The interesting property is that the rules are *capability-aware*: a shape applies to an agent
only if the world derived that capability for it. So an agent on a push-mode board is never
asked for an interval it could not apply, and one on a scheduled board is required to have it.
"""

import pytest
import rdflib
from pyshacl import validate

from agora import genesis, loader
from agora.ontology import WORLD_GRAPH, beliefs_graph

from agora.genesis import agent_id_of

from conftest import GENESIS_DIR, WORLDS_ROOT, genesis_store


def _flatten(st, world_dir=GENESIS_DIR) -> rdflib.Graph:
    """The vocabulary + the world + every agent's beliefs, exactly as validation sees it."""
    data = rdflib.Graph()
    for path in loader.ontology_files():
        data.parse(path, format="turtle")
    graphs = [WORLD_GRAPH]
    # every agent genesis authors, found the way an agent's birth finds them — so adding one
    # to the world is caught here rather than quietly skipped
    graphs += [beliefs_graph(agent_id_of(p)) for p in sorted(world_dir.glob(genesis.BELIEFS_GLOB))]
    for iri in graphs:
        ttl = st.get_graph(iri)
        if ttl.strip():
            data.parse(data=ttl, format="turtle")
    return data


def _worlds():
    return sorted(d.name for d in WORLDS_ROOT.iterdir() if genesis.world_files(d))


@pytest.mark.parametrize("world", _worlds())
def test_every_shipped_world_conforms(world):
    """Every ratified world in world/ must validate — found by looking, never listed.

    This is what makes a second world cheap: add a directory and it is held to the same
    constitution as the first, with no test edit.
    """
    assert _conforms(_flatten(genesis_store(world=world), WORLDS_ROOT / world))


def _conforms(data: rdflib.Graph) -> bool:
    ontology, shapes = rdflib.Graph(), rdflib.Graph()
    for path in loader.ontology_files():
        ontology.parse(path, format="turtle")
    for path in loader.shapes_files():
        shapes.parse(path, format="turtle")
    conforms, _, _ = validate(data, shacl_graph=shapes, ont_graph=ontology,
                              inference="rdfs", advanced=True)
    return conforms


def _mutate(update: str) -> rdflib.Graph:
    """Apply a change to the seeded belief base and re-validate the result."""
    ds = genesis_store()
    ds.update("PREFIX ag: <http://example.org/agora#>\n" + update)
    return _flatten(ds)


# --- the world we actually ship --------------------------------------------

def test_genesis_conforms():
    assert _conforms(_flatten(genesis_store()))


# --- capability-conditional rules ------------------------------------------

def test_polling_agent_must_state_a_cadence():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:fastSleepS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:fastSleepS ?v }} }}"""))


def test_polling_agent_must_state_a_freshness_limit():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:maxReadingAgeS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:maxReadingAgeS ?v }} }}"""))


def test_cadence_may_not_be_slower_when_thirsty():
    # watching LESS closely exactly when in trouble inverts the whole policy
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:fastSleepS 30 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:fastSleepS 800 }} }}
        WHERE  {{}}"""))


def test_nobody_may_sleep_past_the_constitutional_ceiling():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:slowSleepS 600 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:slowSleepS 5000 }} }}
        WHERE  {{}}"""))


def test_inverted_band_is_not_a_band():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:bandLow 0.35 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:bandLow 0.90 }} }}
        WHERE  {{}}"""))


def test_bidder_must_have_a_valuation():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("tomato")}> {{ ag:tomato_agent ag:maxValuePerL ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("tomato")}> {{ ag:tomato_agent ag:maxValuePerL ?v }} }}"""))


def test_host_must_say_how_long_it_waits_for_bids():
    # without a window a round never closes
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("supplier")}> {{ ag:supplier ag:bidWindowS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("supplier")}> {{ ag:supplier ag:bidWindowS ?v }} }}"""))


def test_the_supplier_is_not_asked_for_a_cadence():
    """It composed no perception capability, so the polling rules simply do not apply to it."""
    assert _conforms(_flatten(genesis_store()))  # it has no cadence, and that is fine


# --- the world must be coherently wired ------------------------------------

def test_sensor_must_state_how_it_is_driven():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:senseMode ?m }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:senseMode ?m }} }}"""))


def test_pull_sensor_must_state_a_command_topic():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:commandTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:commandTopic ?t }} }}"""))


def test_a_device_on_the_bus_must_state_where_it_publishes():
    """Declaring a binding and then not completing it is the failure worth catching."""
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:readingTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:readingTopic ?t }} }}"""))


def test_a_listening_agent_must_not_hold_a_cadence():
    """Requiring a policy it cannot enforce would be theatre; stating one misdescribes it."""
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:senseMode ag:Scheduled }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:senseMode ag:Push .
                                           ag:fern_agent ag:hasCapability ag:Listening }} }}
        WHERE  {{}}"""))


def test_valve_must_carry_its_calibration():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:valve_fern ag:maxDoseMl ?v }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:valve_fern ag:maxDoseMl ?v }} }}"""))


def test_a_plant_may_not_hold_a_desire():
    """The target belongs to an agent's beliefs; a plant that held one would be a category error."""
    assert not _conforms(_mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ag:fern ag:hasTarget 0.55 }} }} WHERE {{}}"""))


def test_market_must_state_all_three_channels():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:barrel1_market ag:voucherTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:barrel1_market ag:voucherTopic ?t }} }}"""))


# --- the stand: wiring that cannot work must be refused --------------------------------------
#
# A shape that never fails is not a shape, so each of these asserts the REJECTION. They encode
# the ESP32's rules rather than RDF's, and every one of them is a mistake that costs an
# afternoon: a board that will not boot, an ADC that returns plausible rubbish, a colour that
# never lights.

_WIRING_PREAMBLE = """
@prefix ag: <http://example.org/agora#> .
ag:test_board a ag:Microcontroller ; ag:localId "test_board" ; ag:model "ESP32-WROOM-32D" ;
"""


def _wiring(body: str) -> rdflib.Graph:
    """A board with the given wiring, held to the shapes exactly as a world would be."""
    data = rdflib.Graph()
    for path in loader.ontology_files():
        data.parse(path, format="turtle")
    data.parse(data=_WIRING_PREAMBLE + body, format="turtle")
    return data


def test_the_real_wiring_is_accepted():
    """The guard against a shape so strict that nothing passes it."""
    assert _conforms(_wiring("""
    ag:carries ag:probe , ag:led .
ag:probe a ag:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ ag:pinRole ag:AnalogIn ; ag:gpio 34 ] .
ag:led a ag:RgbLed ; ag:localId "led" ; ag:pin [ ag:pinRole ag:Red ; ag:gpio 25 ] ,
                            [ ag:pinRole ag:Green ; ag:gpio 26 ] ,
                            [ ag:pinRole ag:Blue ; ag:gpio 27 ] .
"""))


@pytest.mark.parametrize("gpio", [6, 8, 11])
def test_a_flash_pin_is_refused(gpio):
    """6-11 are wired to the SPI flash. A board driving one does not boot at all, which reads
    as a dead board rather than as a wiring mistake."""
    assert not _conforms(_wiring(f"""
    ag:carries ag:probe .
ag:probe a ag:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ ag:pinRole ag:DigitalOut ; ag:gpio {gpio} ] .
"""))


@pytest.mark.parametrize("gpio", [4, 12, 25, 27])
def test_an_analog_input_on_adc2_is_refused(gpio):
    """The sharpest of these: ADC2 is unusable while WiFi is up, and it fails by returning
    numbers that look like readings. Nothing downstream can tell they are rubbish."""
    assert not _conforms(_wiring(f"""
    ag:carries ag:probe .
ag:probe a ag:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ ag:pinRole ag:AnalogIn ; ag:gpio {gpio} ] .
"""))


@pytest.mark.parametrize("gpio", [32, 33, 34, 36, 39])
def test_an_analog_input_on_adc1_is_accepted(gpio):
    """The other half of the same rule: ADC1 is exactly what an analog input should use."""
    assert _conforms(_wiring(f"""
    ag:carries ag:probe .
ag:probe a ag:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ ag:pinRole ag:AnalogIn ; ag:gpio {gpio} ] .
"""))


@pytest.mark.parametrize("gpio", [34, 36, 39])
def test_driving_an_input_only_pin_is_refused(gpio):
    """34-39 can be read and never driven. An LED wired there simply never lights."""
    assert not _conforms(_wiring(f"""
    ag:carries ag:led .
ag:led a ag:RgbLed ; ag:localId "led" ; ag:pin [ ag:pinRole ag:Red ; ag:gpio {gpio} ] ,
                            [ ag:pinRole ag:Green ; ag:gpio 26 ] ,
                            [ ag:pinRole ag:Blue ; ag:gpio 27 ] .
"""))


@pytest.mark.parametrize("gpio", [-1, 40, 99])
def test_a_gpio_off_the_board_is_refused(gpio):
    assert not _conforms(_wiring(f"""
    ag:carries ag:probe .
ag:probe a ag:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ ag:pinRole ag:AnalogIn ; ag:gpio {gpio} ] .
"""))


def test_two_peripherals_on_one_gpio_are_refused():
    """The mistake made months later, when a device is added and nobody re-reads the file."""
    assert not _conforms(_wiring("""
    ag:carries ag:probe , ag:led .
ag:probe a ag:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ ag:pinRole ag:AnalogIn ; ag:gpio 34 ] .
ag:led a ag:RgbLed ; ag:localId "led" ; ag:pin [ ag:pinRole ag:Red ; ag:gpio 34 ] ,
                            [ ag:pinRole ag:Green ; ag:gpio 26 ] ,
                            [ ag:pinRole ag:Blue ; ag:gpio 27 ] .
"""))


def test_one_device_using_a_gpio_twice_is_refused():
    """Same rule, inside a single device: an RGB LED with two legs on one line."""
    assert not _conforms(_wiring("""
    ag:carries ag:led .
ag:led a ag:RgbLed ; ag:localId "led" ; ag:pin [ ag:pinRole ag:Red ; ag:gpio 25 ] ,
                            [ ag:pinRole ag:Green ; ag:gpio 25 ] ,
                            [ ag:pinRole ag:Blue ; ag:gpio 27 ] .
"""))


@pytest.mark.parametrize("missing", ["Red", "Green", "Blue"])
def test_an_rgb_led_missing_a_colour_is_refused(missing):
    """One channel that never lights looks, from across the room, exactly like a sleeping board."""
    legs = {"Red": "ag:gpio 25", "Green": "ag:gpio 26", "Blue": "ag:gpio 27"}
    del legs[missing]
    pins = " ,\n           ".join(f"[ ag:pinRole ag:{c} ; {g} ]" for c, g in legs.items())
    assert not _conforms(_wiring(f"""
    ag:carries ag:led .
ag:led a ag:RgbLed ; ag:localId "led" ; ag:pin {pins} .
"""))


def test_a_pin_without_a_role_is_refused():
    """A number with no role cannot be checked for direction, so it cannot be checked at all."""
    assert not _conforms(_wiring("""
    ag:carries ag:probe .
ag:probe a ag:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ ag:gpio 34 ] .
"""))


def test_a_board_without_a_model_is_refused():
    """The model is what a person orders a replacement by, and what a generated firmware
    configuration will have to name."""
    data = rdflib.Graph()
    for path in loader.ontology_files():
        data.parse(path, format="turtle")
    data.parse(data="""
@prefix ag: <http://example.org/agora#> .
ag:nameless a ag:Microcontroller ; ag:localId "nameless" .
""", format="turtle")
    assert not _conforms(data)
