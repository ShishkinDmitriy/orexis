"""SHACL — the constitution as code, one shapes module per capability.

The interesting property is that the rules are *capability-aware*: a shape applies to an agent
only if the world derived that capability for it. So an agent on a push-mode board is never
asked for an interval it could not apply, and one on a scheduled board is required to have it.
"""

import pytest
import rdflib

from agent import genesis, inference, loader
from agent.ontology import (ONTOLOGY_GRAPH, WORLD_DERIVED_GRAPH, WORLD_GRAPH,
                            beliefs_graph)
from agent.validate import conforms as validate_conforms
from agent.store import Store

from agent.genesis import agent_id_of

from conftest import GENESIS_DIR, WORLDS_ROOT, genesis_store


def _flatten(st, world_dir=GENESIS_DIR) -> rdflib.Graph:
    """The vocabulary + the world + every agent's beliefs, exactly as validation sees it.

    The vocabulary comes from the STORE and not from the files, which is the whole of what
    "exactly as validation sees it" now means. `refresh_public` materialises what the T-Box
    entails before anything reads it, so the store's copy carries `onewire:DataPinRole a
    mc:OutputRole` and the files do not — and a shape's SPARQL asks about that literally. This
    helper used to parse the files and was therefore validating something no caller builds; the
    seven pin-role tests failing was the only reason anyone noticed.
    """
    data = rdflib.Graph()
    graphs = list(st.public_graphs())
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
    """The real verdict — `agent.validate.conforms`, not a second copy of it.

    This used to call pySHACL itself with the same arguments, which was fine while the two
    agreed and stopped being fine the moment the runtime learned to pass over `sh:Warning`:
    the tests still failed a world that `agora-validate` accepted. Two ways to decide whether
    a world holds is one too many, and the one that ships is the one to test.
    """
    ok, _ = validate_conforms(data)
    return ok


def _report(data: rdflib.Graph) -> str:
    return validate_conforms(data)[1]


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
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:readingGraceS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:readingGraceS ?v }} }}"""))


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


def test_an_agent_that_only_listens_must_not_hold_a_cadence():
    """Requiring a policy it cannot enforce would be theatre; stating one misdescribes it.

    ONLY listens — the Subscribing capability has to go too. An agent that holds both is a
    legitimate rig (a scheduled probe and a push thermometer on one plant) and needs both blocks.
    """
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:senseMode ag:Scheduled }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:senseMode ag:Push }} }}
        WHERE  {{}} ;
        DELETE {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{
            ag:fern_agent ag:hasCapability ag:Subscribing }} }}
        INSERT {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{
            ag:fern_agent ag:hasCapability ag:Listening }} }}
        WHERE  {{}}"""))


def test_an_agent_may_hold_both_modes_at_once():
    """A plant with a scheduled probe and a push thermometer is ordinary, and was unvalidatable.

    Two shapes each written for a pure agent contradicted each other here: one demanded an
    interval, the other forbade it. Nothing said the combination was disallowed; it simply could
    not be expressed.
    """
    assert _conforms(_mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            ag:chatter_fern a ag:Sensor ; ag:localId "chatter_fern" ; ag:onBus ag:local_bus ;
                ag:senseMode ag:Push ; ag:monitors ag:fern ; sosa:observes ag:SoilMoisture ;
                ag:readingTopic "sensors/chatter_fern/reading" .
            ag:fern_agent ag:polls ag:chatter_fern .
        }} }} WHERE {{}} ;
        INSERT {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{
            ag:fern_agent ag:hasCapability ag:Listening }} }} WHERE {{}}"""))


def _duplicate_probe(observes: str) -> rdflib.Graph:
    return _mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            ag:second_probe_fern a ag:Sensor ; ag:localId "second_probe_fern" ;
                ag:onBus ag:local_bus ; ag:senseMode ag:Scheduled ; ag:monitors ag:fern ;
                sosa:observes {observes} ;
                ag:readingTopic "sensors/second_probe_fern/reading" ;
                ag:commandTopic "sensors/second_probe_fern/command" .
            ag:fern_agent ag:polls ag:second_probe_fern .
        }} }} WHERE {{}}""")


def test_two_sensors_on_one_property_are_warned_about_and_not_refused():
    """Two probes in one pot is legal wiring with defined behaviour — and a modelling smell.

    They share one observation node and the last writer wins, which is right if they really are
    one thing measured twice and wrong if they are in different soil. Neither reading can be
    settled from the graph, so the world is accepted and the operator is told.
    """
    data = _duplicate_probe("ag:SoilMoisture")
    assert _conforms(data), "a warning must not stop a world from being onboarded"
    assert "another sensor already reads this property" in _report(data)


def test_two_sensors_on_different_properties_are_not_warned_about():
    """The ordinary rig, and the case the shape must not catch. A pot whose moisture and
    temperature are both known is not a modelling error, and saying so would train the operator
    to ignore the message that matters."""
    data = _duplicate_probe("ag:AirTemperature")
    assert _conforms(data)
    assert "another sensor already reads this property" not in _report(data)


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


# --- the mc: wiring that cannot work must be refused --------------------------------------
#
# A shape that never fails is not a shape, so each of these asserts the REJECTION. They encode
# the ESP32's rules rather than RDF's, and every one of them is a mistake that costs an
# afternoon: a board that will not boot, an ADC that returns plausible rubbish, a colour that
# never lights.

_WIRING_PREAMBLE = """
@prefix ag:      <http://example.org/agora#> .
@prefix mc: <http://example.org/agora/microcontroller#> .
@prefix onewire: <http://example.org/agora/onewire#> .
@prefix i2c:     <http://example.org/agora/i2c#> .
@prefix dht11:   <http://example.org/agora/dht11#> .
@prefix rgbled:  <http://example.org/agora/rgb-led#> .
@prefix probe:   <http://example.org/agora/moisture-probe#> .
ag:test_board a mc:Microcontroller ; ag:localId "test_board" ; mc:model "ESP32-WROOM-32D" ;
    mc:logicVolts 3.3 ; mc:hasPin ag:t_3v3 , ag:t_gnd ;
"""

_RAILS = """
ag:t_3v3 a mc:Pin ; mc:pinRole mc:PowerPinRole ; mc:railVolts 3.3 .
ag:t_gnd a mc:Pin ; mc:pinRole mc:GroundPinRole .
"""


def _leg(device, name, role, gpio=None, powered=True):
    """One peripheral leg, the board pin it reaches, and the wire between them.

    Three statements where there used to be one, which is the model's whole point: the ROLE is
    a fact about the peripheral's leg and the GPIO NUMBER a fact about the board's, and only the
    wire knows they are the same connection. `powered` gives the device its rail and ground too,
    because a peripheral with an unwired leg is now itself a violation — so a test about pin 34
    would otherwise fail for a reason it is not about.
    """
    ttl = f"""
ag:{name}_leg a mc:Pin ; mc:pinRole {role} .
[] a mc:Wire ; mc:joins ag:{name}_leg , ag:{name}_line .
ag:{name}_line a mc:Pin {f'; mc:gpio {gpio}' if gpio is not None else ''} .
ag:test_board mc:hasPin ag:{name}_line .
ag:{device} mc:hasPin ag:{name}_leg .
"""
    if powered:
        ttl += f"""
ag:{device} mc:hasPin ag:{device}_vcc , ag:{device}_gnd .
ag:{device}_vcc a mc:Pin ; mc:pinRole mc:PowerPinRole .
ag:{device}_gnd a mc:Pin ; mc:pinRole mc:GroundPinRole .
[] a mc:Wire ; mc:joins ag:{device}_vcc , ag:t_3v3 .
[] a mc:Wire ; mc:joins ag:{device}_gnd , ag:t_gnd .
"""
    return ttl


def _wiring(body: str) -> rdflib.Graph:
    """A board with the given wiring, held to the shapes exactly as a world would be.

    Through a real store, and that is load-bearing rather than ceremony. These wirings never see
    `refresh_public`, so parsing the vocabulary straight from the files left them without the
    entailments every other caller has — and the pin-role rules ask `?role a mc:OutputRole`,
    which is asserted nowhere and entailed twice over. Building the store and materialising is
    what makes "exactly as a world would be" true instead of approximately true.
    """
    st = Store()
    st.put_graph(ONTOLOGY_GRAPH, "\n".join(p.read_text() for p in loader.ontology_files()))
    st.put_graph(WORLD_GRAPH, _WIRING_PREAMBLE + body + _RAILS)
    inference.materialise(st)

    data = rdflib.Graph()
    for iri in st.public_graphs():
        ttl = st.get_graph(iri)
        if ttl.strip():
            data.parse(data=ttl, format="turtle")
    return data


def test_the_real_wiring_is_accepted():
    """The guard against a shape so strict that nothing passes it."""
    assert _conforms(_wiring("""
    mc:carries ag:probe , ag:led .
ag:probe a probe:CapacitiveMoistureProbe ; ag:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
ag:led a rgbled:RgbLed ; ag:localId "led" .
""" + _leg("probe", "p", "mc:AnalogInPinRole", 34)
   + _leg("led", "r", "rgbled:RedPinRole", 25)
   + _leg("led", "g", "rgbled:GreenPinRole", 26, powered=False)
   + _leg("led", "b", "rgbled:BluePinRole", 27, powered=False)))


@pytest.mark.parametrize("gpio", [6, 8, 11])
def test_a_flash_pin_is_refused(gpio):
    """6-11 are wired to the SPI flash. A board driving one does not boot at all, which reads
    as a dead board rather than as a wiring mistake."""
    assert not _conforms(_wiring("""
    mc:carries ag:probe .
ag:probe a probe:CapacitiveMoistureProbe ; ag:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
""" + _leg("probe", "p", "mc:DigitalOutPinRole", gpio)))


@pytest.mark.parametrize("gpio", [4, 12, 25, 27])
def test_an_analog_input_on_adc2_is_refused(gpio):
    """The sharpest of these: ADC2 is unusable while WiFi is up, and it fails by returning
    numbers that look like readings. Nothing downstream can tell they are rubbish."""
    assert not _conforms(_wiring("""
    mc:carries ag:probe .
ag:probe a probe:CapacitiveMoistureProbe ; ag:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
""" + _leg("probe", "p", "mc:AnalogInPinRole", gpio)))


@pytest.mark.parametrize("gpio", [32, 33, 34, 36, 39])
def test_an_analog_input_on_adc1_is_accepted(gpio):
    """The other half of the same rule: ADC1 is exactly what an analog input should use."""
    assert _conforms(_wiring("""
    mc:carries ag:probe .
ag:probe a probe:CapacitiveMoistureProbe ; ag:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
""" + _leg("probe", "p", "mc:AnalogInPinRole", gpio)))


@pytest.mark.parametrize("gpio", [34, 36, 39])
def test_driving_an_input_only_pin_is_refused(gpio):
    """34-39 can be read and never driven. An LED wired there simply never lights."""
    assert not _conforms(_wiring("""
    mc:carries ag:led .
ag:led a rgbled:RgbLed ; ag:localId "led" .
""" + _leg("led", "r", "rgbled:RedPinRole", gpio)
   + _leg("led", "g", "rgbled:GreenPinRole", 26, powered=False)
   + _leg("led", "b", "rgbled:BluePinRole", 27, powered=False)))


@pytest.mark.parametrize("role", ["onewire:DataPinRole", "i2c:DataPinRole"])
@pytest.mark.parametrize("gpio", [34, 35, 39])
def test_a_bidirectional_line_on_an_input_only_pin_is_refused(role, gpio):
    """The same rule, for the lines that look like inputs and are not.

    A DHT's data leg and an I2C SDA carry almost all their traffic inbound, so both read as
    inputs — but the board must PULL EACH LOW to start a conversation, and 34-39 cannot pull
    anything. Wired there, a DHT returns nothing but a timeout and an SDA hangs the bus.
    """
    assert not _conforms(_wiring("""
    mc:carries ag:air .
ag:air a mc:Peripheral ; ag:localId "air" .
""" + _leg("air", "d", role, gpio)))


@pytest.mark.parametrize("gpio", [32, 33, 25, 4])
def test_a_bidirectional_line_on_a_drivable_pin_is_accepted(gpio):
    """The other half: any pin that can be driven will do, ADC membership included — a
    one-wire line is digital, so ADC2 costs it nothing."""
    assert _conforms(_wiring("""
    mc:carries ag:air .
ag:air a mc:Peripheral ; ag:localId "air" .
""" + _leg("air", "d", "onewire:DataPinRole", gpio)))


@pytest.mark.parametrize("gpio", [-1, 40, 99])
def test_a_gpio_off_the_board_is_refused(gpio):
    assert not _conforms(_wiring("""
    mc:carries ag:probe .
ag:probe a probe:CapacitiveMoistureProbe ; ag:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
""" + _leg("probe", "p", "mc:AnalogInPinRole", gpio)))


# --- what the pin/wire model made sayable, and the old one could not -------------------------

def test_a_leg_that_no_wire_reaches_is_refused():
    """The old model could not express this at all: a pin WAS its connection, so an
    unconnected leg was invisible rather than wrong. A floating ground is the commonest reason
    a three-legged sensor answers with silence, and it looks exactly like a dead part."""
    assert not _conforms(_wiring("""
    mc:carries ag:air .
ag:air a mc:Peripheral ; ag:localId "air" ; mc:hasPin ag:air_float .
ag:air_float a mc:Pin ; mc:pinRole mc:GroundPinRole .
""" + _leg("air", "d", "onewire:DataPinRole", 32)))


def test_a_leg_the_PART_never_connects_is_accepted():
    """What the component IS. A DHT's third pin connects to nothing inside it — the package has
    four positions and the die uses three — and that is true of every DHT ever made. Intrinsic,
    so it is a role."""
    assert _conforms(_wiring("""
    mc:carries ag:air .
ag:air a mc:Peripheral ; ag:localId "air" ; mc:hasPin ag:air_nc .
ag:air_nc a mc:Pin ; mc:pinRole mc:NotConnectedPinRole .
""" + _leg("air", "d", "onewire:DataPinRole", 32)))


def test_a_leg_THIS_BUILD_leaves_unwired_is_accepted():
    """What the build DID, which is a different fact and cannot be a role.

    A board has thirty legs and a world wires seven; nothing about the ESP32 says which, and the
    same board in another world uses different ones. Putting that in a role would file a fact
    about one breadboard inside the description of a component.
    """
    assert _conforms(_wiring("""
    mc:carries ag:air .
ag:air a mc:Peripheral ; ag:localId "air" ; mc:hasPin ag:air_spare .
ag:air_spare a mc:Pin ; mc:pinRole mc:DigitalOutPinRole ; mc:unused true .
""" + _leg("air", "d", "onewire:DataPinRole", 32)))


def test_a_leg_that_is_merely_forgotten_is_still_refused():
    """The whole point of the other two. Silence must go on meaning 'I have not thought about
    this leg' — a floating ground is the commonest reason a three-legged part answers with
    silence, and it looks exactly like a dead part."""
    assert not _conforms(_wiring("""
    mc:carries ag:air .
ag:air a mc:Peripheral ; ag:localId "air" ; mc:hasPin ag:air_spare .
ag:air_spare a mc:Pin ; mc:pinRole mc:DigitalOutPinRole .
""" + _leg("air", "d", "onewire:DataPinRole", 32)))


def test_a_five_volt_rail_into_a_three_volt_input_is_refused():
    """The fault this whole remodelling exists to make sayable, and the one that cost an evening.

    A three-legged sensor carries a pull-up to its OWN VCC, so its data line idles at whatever
    it is powered from. On VIN that is 5V, presented to an input that is not 5V tolerant — which
    does not fail, it degrades over weeks and looks like a flaky sensor. There was nowhere in
    the old model to say which rail a device was on, so there was nothing to check.
    """
    assert not _conforms(_wiring("""
    mc:carries ag:air .
ag:air a mc:Peripheral ; ag:localId "air" ; mc:hasPin ag:air_vcc , ag:air_gnd .
ag:air_vcc a mc:Pin ; mc:pinRole mc:PowerPinRole .
ag:air_gnd a mc:Pin ; mc:pinRole mc:GroundPinRole .
ag:t_vin a mc:Pin ; mc:pinRole mc:PowerPinRole ; mc:railVolts 5.0 .
ag:test_board mc:hasPin ag:t_vin .
[] a mc:Wire ; mc:joins ag:air_vcc , ag:t_vin .
[] a mc:Wire ; mc:joins ag:air_gnd , ag:t_gnd .
""" + _leg("air", "d", "onewire:DataPinRole", 32, powered=False)))


def test_a_dht_must_name_all_three_of_its_legs():
    """Its data line alone was the old model's best effort — there was nowhere to put the
    other two — and it is precisely the missing ones that go wrong."""
    assert not _conforms(_wiring("""
    mc:carries ag:air .
ag:air a dht11:Dht11 ; ag:localId "air" .
""" + _leg("air", "d", "onewire:DataPinRole", 32, powered=False)))


def test_two_peripherals_on_one_gpio_are_refused():
    """The mistake made months later, when a device is added and nobody re-reads the file."""
    assert not _conforms(_wiring("""
    mc:carries ag:probe , ag:led .
ag:probe a probe:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ mc:pinRole mc:AnalogInPinRole ; mc:gpio 34 ] .
ag:led a rgbled:RgbLed ; ag:localId "led" ; ag:pin [ mc:pinRole rgbled:RedPinRole ; mc:gpio 34 ] ,
                            [ mc:pinRole rgbled:GreenPinRole ; mc:gpio 26 ] ,
                            [ mc:pinRole rgbled:BluePinRole ; mc:gpio 27 ] .
"""))


def test_one_device_using_a_gpio_twice_is_refused():
    """Same rule, inside a single device: an RGB LED with two legs on one line."""
    assert not _conforms(_wiring("""
    mc:carries ag:led .
ag:led a rgbled:RgbLed ; ag:localId "led" ; ag:pin [ mc:pinRole rgbled:RedPinRole ; mc:gpio 25 ] ,
                            [ mc:pinRole rgbled:GreenPinRole ; mc:gpio 25 ] ,
                            [ mc:pinRole rgbled:BluePinRole ; mc:gpio 27 ] .
"""))


@pytest.mark.parametrize("missing", ["Red", "Green", "Blue"])
def test_an_rgb_led_missing_a_colour_is_refused(missing):
    """One channel that never lights looks, from across the room, exactly like a sleeping board."""
    legs = {"Red": "mc:gpio 25", "Green": "mc:gpio 26", "Blue": "mc:gpio 27"}
    del legs[missing]
    pins = " ,\n           ".join(f"[ mc:pinRole ag:{c} ; {g} ]" for c, g in legs.items())
    assert not _conforms(_wiring(f"""
    mc:carries ag:led .
ag:led a rgbled:RgbLed ; ag:localId "led" ; ag:pin {pins} .
"""))


def test_a_pin_without_a_role_is_refused():
    """A number with no role cannot be checked for direction, so it cannot be checked at all."""
    assert not _conforms(_wiring("""
    mc:carries ag:probe .
ag:probe a probe:CapacitiveMoistureProbe ; ag:localId "probe" ; ag:pin [ mc:gpio 34 ] .
"""))


def test_a_board_without_a_model_is_refused():
    """The model is what a person orders a replacement by, and what a generated firmware
    configuration will have to name."""
    data = rdflib.Graph()
    for path in loader.ontology_files():
        data.parse(path, format="turtle")
    data.parse(data="""
@prefix ag:    <http://example.org/agora#> .
@prefix mc: <http://example.org/agora/microcontroller#> .
ag:nameless a mc:Microcontroller ; ag:localId "nameless" .
""", format="turtle")
    assert not _conforms(data)
