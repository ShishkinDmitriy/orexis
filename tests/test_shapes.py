"""SHACL — the constitution as code, one shapes module per capability.

The interesting property is that the rules are *capability-aware*: a shape applies to an agent
only if the world derived that capability for it. So an agent on a push-mode board is never
asked for an interval it could not apply, and one on a scheduled board is required to have it.
"""

import pathlib

import pytest
import rdflib

from agent import genesis, inference

from assembly import loader
from orexis_agent_progression.ontology import (ONTOLOGY_GRAPH, WORLD_DERIVED_GRAPH, WORLD_GRAPH,
                            beliefs_graph)
from agent.validate import conforms as validate_conforms
from orexis_agent_progression.store import Store

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
    for iri in st.public_graphs():
        ttl = st.get_graph(iri)
        if ttl.strip():
            data.parse(data=ttl, format="turtle")
    # every agent genesis authors, found the way an agent's birth finds them — and its WANTS
    # built the way its boot builds them (#312): the derived regions and the projected pick
    # record arrive through the desire modality, and only through it, because a record
    # flattened beside its projection splits every blank-node aim in two.
    from orexis_agent_deliberation import effects
    from orexis_agent_deliberation.beliefs import Beliefs
    from orexis_agent_deliberation.desire import Desires

    for path in sorted(world_dir.glob(genesis.BELIEFS_GLOB)):
        wants = Desires(Beliefs(st, agent_id_of(path)))
        for triple in wants.construct(
                "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
            data.add(effects._triple(triple))
    return data


def _worlds():
    #  The roster moved to `conftest.shipped_worlds` so three files share one — this file had
    #  it right and two others hard-coded a pair that stopped growing.
    from conftest import shipped_worlds

    return shipped_worlds()


@pytest.mark.parametrize("world", _worlds())
def test_every_shipped_world_conforms(world):
    """Every ratified world in world/ must validate — found by looking, never listed.

    This is what makes a second world cheap: add a directory and it is held to the same
    constitution as the first, with no test edit.
    """
    assert _conforms(_flatten(genesis_store(world=world), WORLDS_ROOT / world))


def _validated(data: rdflib.Graph) -> tuple[bool, str]:
    """One pyshacl run per graph, keeping BOTH halves of what it already returns.

    Issue #272. `agent.validate.conforms` hands back `(ok, report)` from a single validation, and
    `_conforms` and `_report` each threw away the half they were not asked for — so a test that
    asserts a world is refused and then checks WHY validated a byte-identical graph twice, and
    one of them three times. Measured on the Pi: pyshacl is 2.35s a call, against 0.20s for all
    of `_mutate` (build 0.052s, re-derive 0.033s, flatten 0.116s). The validation is 92% of this
    file, and this file is the largest block of the suite.

    Cached on the graph OBJECT rather than in a dict keyed on identity, which would hold every
    graph alive for the session and go wrong the moment CPython reused an id. It cannot go stale:
    `_mutate` returns a freshly flattened graph per test and nothing here mutates one after
    validating it — asserted by `test_a_graph_is_never_changed_after_it_is_validated` below, so
    the day someone does, the guard says so rather than the cache lying.
    """
    verdict = getattr(data, "_orexis_verdict", None)
    if verdict is None:
        verdict = validate_conforms(data)
        data._orexis_verdict = verdict
    return verdict


def _conforms(data: rdflib.Graph) -> bool:
    """The real verdict — `agent.validate.conforms`, not a second copy of it.

    This used to call pySHACL itself with the same arguments, which was fine while the two
    agreed and stopped being fine the moment the runtime learned to pass over `sh:Warning`:
    the tests still failed a world that `orexis-validate` accepted. Two ways to decide whether
    a world holds is one too many, and the one that ships is the one to test.
    """
    return _validated(data)[0]


def _report(data: rdflib.Graph) -> str:
    return _validated(data)[1]


def _mutate(update: str) -> rdflib.Graph:
    """Apply a change to the seeded belief base, re-derive, and validate the result.

    The re-derivation is what makes a mutated world one genesis could actually have produced.
    A test that ADDS a sensor and stops there builds a graph with a premise and no conclusion —
    which no world ever has, and which now fails validation for a reason that has nothing to do
    with what the test is about: every sensor is derived a codec and a scaling, and one
    inserted by hand has neither.

    Additive rather than cleared-and-recomputed, which is the opposite of what
    `test_capabilities._world_with_push_sensor` does and deliberately so. That one CHANGES a
    premise and needs the previous conclusion gone. These mostly delete beliefs and hand-write
    the one derived fact they are about, so clearing would take away what they just set up.
    Adding what the rules would add leaves both intact.
    """
    ds = genesis_store()
    ds.update("PREFIX orexis: <http://example.org/orexis#>\n" + update)
    for rule in loader.rule_files():
        ds.update(genesis.substitute(rule.read_text(), ds))
    return _flatten(ds)


# --- the world we actually ship --------------------------------------------

def test_genesis_conforms():
    assert _conforms(_flatten(genesis_store()))


# --- capability-conditional rules ------------------------------------------

def test_polling_agent_must_state_a_cadence():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:fastSleepS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:fastSleepS ?v }} }}"""))


def test_polling_agent_must_state_a_freshness_limit():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:readingGraceS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:readingGraceS ?v }} }}"""))


def test_cadence_may_not_be_slower_when_thirsty():
    # watching LESS closely exactly when in trouble inverts the whole policy
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:fastSleepS 30 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:fastSleepS 800 }} }}
        WHERE  {{}}"""))


def test_nobody_may_sleep_past_the_constitutional_ceiling():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:slowSleepS 600 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:slowSleepS 5000 }} }}
        WHERE  {{}}"""))


def test_a_bidder_with_no_aim_in_the_priced_property_is_refused():
    """The domain's own half of the split: WHERE an aim may sit is desire's arithmetic, but that
    a BID needs one is a fact only the domain knows — a bidder with no aim in the property its
    bids are priced in has no deficit to value. Deleting fern's whole aim leaves a bidder that
    could only invent a number, and it must not start instead."""
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{
                 <http://example.org/orexis/world/simulation#fern_agent> sensing:aims ?aim . ?aim ?p ?o }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{
                 <http://example.org/orexis/world/simulation#fern_agent> sensing:aims ?aim . ?aim ?p ?o }} }}"""))


def test_an_aim_in_a_property_with_no_region_is_refused():
    """A pick with nothing to pick inside. Fern holds no humidity region — its plant states no
    humidity range — so an aim there is a number with nothing behind it, whatever its value."""
    assert not _conforms(_mutate(f"""
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{
            <http://example.org/orexis/world/simulation#fern_agent> sensing:aims [
                ssn:forProperty <http://example.org/orexis/water#AirHumidity> ;
                schema:value 0.5 ] }} }}
        WHERE {{}}"""))


def test_bidder_must_have_a_valuation():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("tomato")}> {{ <http://example.org/orexis/world/simulation#tomato_agent> water:maxValuePerL ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("tomato")}> {{ <http://example.org/orexis/world/simulation#tomato_agent> water:maxValuePerL ?v }} }}"""))


def test_host_must_say_how_long_it_waits_for_bids():
    # without a window a round never closes
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("supplier")}> {{ <http://example.org/orexis/world/simulation#supplier> market:bidWindowS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("supplier")}> {{ <http://example.org/orexis/world/simulation#supplier> market:bidWindowS ?v }} }}"""))


def test_the_supplier_is_not_asked_for_a_cadence():
    """It composed no sensing capability, so the polling rules simply do not apply to it."""
    assert _conforms(_flatten(genesis_store()))  # it has no cadence, and that is fine


# --- the world must be coherently wired ------------------------------------

def test_sensor_must_state_how_it_is_driven():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> sensing:senseMode ?m }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> sensing:senseMode ?m }} }}"""))


def test_a_host_must_say_how_it_matches():
    """Without it no matching capability is derived and the failure arrives at the END of a
    round: bids collected, deadline passed, nothing to allocate them with, every bidder waiting
    on a claim that will not come. Refusing the world costs nothing by comparison."""
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#supplier> market:matchesBy ?f }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#supplier> market:matchesBy ?f }} }}"""))


def test_only_a_host_may_state_how_it_matches():
    """An auction's terms belong to whoever convenes it. A bidder saying how it would match is
    an authoring slip, and the derivation already ignores it — so without a shape the statement
    would sit in the world doing nothing, which is the shape of a fact somebody later believes."""
    assert not _conforms(_mutate(f"""
        INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#fern_agent> market:matchesBy market:PayAsBid }} }}"""))


def test_pull_sensor_must_state_a_command_topic():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:commandTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:commandTopic ?t }} }}"""))


def test_a_device_on_the_bus_must_state_where_it_publishes():
    """Declaring a binding and then not completing it is the failure worth catching."""
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:readingTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:readingTopic ?t }} }}"""))


def test_an_agent_that_only_listens_must_not_hold_a_cadence():
    """Requiring a policy it cannot enforce would be theatre; stating one misdescribes it.

    ONLY listens — the Subscribing capability has to go too. An agent that holds both is a
    legitimate rig (a scheduled probe and a push thermometer on one plant) and needs both blocks.

    Every sensor fern polls is switched, and the derived capability is left to the rules rather
    than hand-written. It used to switch `<http://example.org/orexis/world/simulation#moisture_sensor_fern>` and then edit the derived
    graph directly, which worked only while fern had exactly one sensor: it has two now, so the
    untouched one kept it `Scheduled`, and `_mutate` re-derives ADDITIVELY — so the
    hand-deleted `Subscribing` came straight back and the agent conformed, holding both modes
    legitimately. Stating the premise properly is what makes the conclusion follow.
    """
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?s sensing:senseMode sensing:ScheduledProcedure }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?s sensing:senseMode sensing:PushProcedure }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#fern_agent> sensing:polls ?s .
                                           ?s sensing:senseMode sensing:ScheduledProcedure }} }} ;
        DELETE {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{
            <http://example.org/orexis/world/simulation#fern_agent> orexis:hasCapability sensing:Subscribing }} }}
        WHERE  {{}}"""))


def test_an_agent_may_hold_both_modes_at_once():
    """A plant with a scheduled probe and a push thermometer is ordinary, and was unvalidatable.

    Two shapes each written for a pure agent contradicted each other here: one demanded an
    interval, the other forbade it. Nothing said the combination was disallowed; it simply could
    not be expressed.
    """
    assert _conforms(_mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            orexis:chatter_fern a sosa:Sensor , device:Device ; orexis:localId "chatter_fern" ; mqtt:onBus <http://example.org/orexis/world/simulation#local_bus> ;
                sensing:senseMode sensing:PushProcedure ; sensing:monitors <http://example.org/orexis/world/simulation#fern> ; sosa:observes water:SoilMoisture ;
                scaling:quantityUnit unit:UNITLESS ;
                mqtt:readingTopic "sensors/chatter_fern/reading" .
            <http://example.org/orexis/world/simulation#fern_agent> sensing:polls orexis:chatter_fern .
        }} }} WHERE {{}} ;
        INSERT {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{
            <http://example.org/orexis/world/simulation#fern_agent> orexis:hasCapability sensing:Listening }} }} WHERE {{}}"""))


def _duplicate_probe(observes: str) -> rdflib.Graph:
    return _mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            orexis:second_probe_fern a sosa:Sensor , device:Device ; orexis:localId "second_probe_fern" ;
                mqtt:onBus <http://example.org/orexis/world/simulation#local_bus> ; sensing:senseMode sensing:ScheduledProcedure ; sensing:monitors <http://example.org/orexis/world/simulation#fern> ;
                sosa:observes {observes} ;
                scaling:quantityUnit unit:UNITLESS ;
                mqtt:readingTopic "sensors/second_probe_fern/reading" ;
                mqtt:commandTopic "sensors/second_probe_fern/command" .
            <http://example.org/orexis/world/simulation#fern_agent> sensing:polls orexis:second_probe_fern .
        }} }} WHERE {{}}""")


def test_two_sensors_on_one_property_are_warned_about_and_not_refused():
    """Two probes in one pot is legal wiring with defined behaviour — and a modelling smell.

    They share one observation node and the last writer wins, which is right if they really are
    one thing measured twice and wrong if they are in different soil. Neither reading can be
    settled from the graph, so the world is accepted and the operator is told.
    """
    data = _duplicate_probe("water:SoilMoisture")
    assert _conforms(data), "a warning must not stop a world from being onboarded"
    assert "another sensor already reads this property" in _report(data)


def test_two_sensors_on_different_properties_are_not_warned_about():
    """The ordinary rig, and the case the shape must not catch. A pot whose moisture and
    humidity are both known is not a modelling error, and saying so would train the operator
    to ignore the message that matters.

    Humidity rather than temperature, because fern already reads a temperature — the world this
    runs against has a probe and a thermometer sharing one board. Adding a second thermometer
    would be the duplicate case, which is the test above, and it fired exactly as it should.
    """
    data = _duplicate_probe("water:AirHumidity")
    assert _conforms(data)
    assert "another sensor already reads this property" not in _report(data)


def test_valve_must_carry_its_calibration():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#valve_fern> actuation:maxDoseMl ?v }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#valve_fern> actuation:maxDoseMl ?v }} }}"""))


def test_a_plant_may_not_hold_a_desire():
    """The aim belongs to an agent's beliefs; a plant that held one would be a category error."""
    assert not _conforms(_mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#fern> <http://example.org/orexis/sensing#aims> [
            <http://www.w3.org/ns/ssn/forProperty> <http://example.org/orexis/water#SoilMoisture> ;
            <https://schema.org/value> 0.55 ] }} }} WHERE {{}}"""))


def test_market_must_state_all_three_channels():
    # The shipped venue DERIVES since arc 3 — deleting from it would just re-derive — so the
    # shape is shown on what it still exists for: a hand-authored venue (the derivation adds,
    # never forbids) that forgot a channel.
    assert not _conforms(_mutate(f"""
        INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
            <http://example.org/orexis/world/simulation#lopsided_market>
                a <http://example.org/orexis/market#Market> ;
                <http://example.org/orexis#localId> "lopsided_market" ;
                <http://example.org/orexis/market#offerTopic> "market/lopsided/offer" ;
                <http://example.org/orexis/market#bidTopic> "market/lopsided/bid" }} }}"""))


# --- the mc: wiring that cannot work must be refused --------------------------------------
#
# A shape that never fails is not a shape, so each of these asserts the REJECTION. They encode
# the ESP32's rules rather than RDF's, and every one of them is a mistake that costs an
# afternoon: a board that will not boot, an ADC that returns plausible rubbish, a colour that
# never lights.

_WIRING_PREAMBLE = """
@prefix schema: <https://schema.org/> .
@prefix unit: <http://qudt.org/vocab/unit/> .
@prefix orexis:      <http://example.org/orexis#> .
@prefix mc: <http://example.org/orexis/microcontroller#> .
@prefix onewire: <http://example.org/orexis/onewire#> .
@prefix i2c:     <http://example.org/orexis/i2c#> .
@prefix dht11:   <http://example.org/orexis/dht11#> .
@prefix rgbled:  <http://example.org/orexis/rgb-led#> .
@prefix probe:   <http://example.org/orexis/moisture-probe#> .
@prefix sosa:    <http://www.w3.org/ns/sosa/> .
orexis:test_board a mc:Microcontroller ; orexis:localId "test_board" ; mc:model "ESP32-WROOM-32D" ;
    mc:logicVolts 3.3 ; mc:hasPin orexis:t_3v3 , orexis:t_gnd ;
"""

_RAILS = """
orexis:t_3v3 a mc:Pin ; mc:pinRole mc:PowerPinRole ; mc:railVolts 3.3 .
orexis:t_gnd a mc:Pin ; mc:pinRole mc:GroundPinRole .
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
orexis:{name}_leg a mc:Pin ; mc:pinRole {role} .
[] a mc:Wire ; mc:joins orexis:{name}_leg , orexis:{name}_line .
orexis:{name}_line a mc:Pin {f'; mc:gpio {gpio}' if gpio is not None else ''} .
orexis:test_board mc:hasPin orexis:{name}_line .
orexis:{device} mc:hasPin orexis:{name}_leg .
"""
    if powered:
        ttl += f"""
orexis:{device} mc:hasPin orexis:{device}_vcc , orexis:{device}_gnd .
orexis:{device}_vcc a mc:Pin ; mc:pinRole mc:PowerPinRole .
orexis:{device}_gnd a mc:Pin ; mc:pinRole mc:GroundPinRole .
[] a mc:Wire ; mc:joins orexis:{device}_vcc , orexis:t_3v3 .
[] a mc:Wire ; mc:joins orexis:{device}_gnd , orexis:t_gnd .
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
    sosa:hosts orexis:probe , orexis:led .
orexis:probe a probe:CapacitiveMoistureProbe ; orexis:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
orexis:led a rgbled:RgbLed ; orexis:localId "led" .
""" + _leg("probe", "p", "mc:AnalogInPinRole", 34)
   + _leg("led", "r", "rgbled:RedPinRole", 25)
   + _leg("led", "g", "rgbled:GreenPinRole", 26, powered=False)
   + _leg("led", "b", "rgbled:BluePinRole", 27, powered=False)))


@pytest.mark.parametrize("gpio", [6, 8, 11])
def test_a_flash_pin_is_refused(gpio):
    """6-11 are wired to the SPI flash. A board driving one does not boot at all, which reads
    as a dead board rather than as a wiring mistake."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:probe .
orexis:probe a probe:CapacitiveMoistureProbe ; orexis:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
""" + _leg("probe", "p", "mc:DigitalOutPinRole", gpio)))


@pytest.mark.parametrize("gpio", [4, 12, 25, 27])
def test_an_analog_input_on_adc2_is_refused(gpio):
    """The sharpest of these: ADC2 is unusable while WiFi is up, and it fails by returning
    numbers that look like readings. Nothing downstream can tell they are rubbish."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:probe .
orexis:probe a probe:CapacitiveMoistureProbe ; orexis:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
""" + _leg("probe", "p", "mc:AnalogInPinRole", gpio)))


@pytest.mark.parametrize("gpio", [32, 33, 34, 36, 39])
def test_an_analog_input_on_adc1_is_accepted(gpio):
    """The other half of the same rule: ADC1 is exactly what an analog input should use."""
    assert _conforms(_wiring("""
    sosa:hosts orexis:probe .
orexis:probe a probe:CapacitiveMoistureProbe ; orexis:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
""" + _leg("probe", "p", "mc:AnalogInPinRole", gpio)))


@pytest.mark.parametrize("gpio", [34, 36, 39])
def test_driving_an_input_only_pin_is_refused(gpio):
    """34-39 can be read and never driven. An LED wired there simply never lights."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:led .
orexis:led a rgbled:RgbLed ; orexis:localId "led" .
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
    sosa:hosts orexis:air .
orexis:air a mc:Peripheral ; orexis:localId "air" .
""" + _leg("air", "d", role, gpio)))


@pytest.mark.parametrize("gpio", [32, 33, 25, 4])
def test_a_bidirectional_line_on_a_drivable_pin_is_accepted(gpio):
    """The other half: any pin that can be driven will do, ADC membership included — a
    one-wire line is digital, so ADC2 costs it nothing."""
    assert _conforms(_wiring("""
    sosa:hosts orexis:air .
orexis:air a mc:Peripheral ; orexis:localId "air" .
""" + _leg("air", "d", "onewire:DataPinRole", gpio)))


@pytest.mark.parametrize("gpio", [-1, 40, 99])
def test_a_gpio_off_the_board_is_refused(gpio):
    assert not _conforms(_wiring("""
    sosa:hosts orexis:probe .
orexis:probe a probe:CapacitiveMoistureProbe ; orexis:localId "probe" ; probe:rawDry 3200 ; probe:rawWet 1300 .
""" + _leg("probe", "p", "mc:AnalogInPinRole", gpio)))


# --- what the pin/wire model made sayable, and the old one could not -------------------------

def test_a_leg_that_no_wire_reaches_is_refused():
    """The old model could not express this at all: a pin WAS its connection, so an
    unconnected leg was invisible rather than wrong. A floating ground is the commonest reason
    a three-legged sensor answers with silence, and it looks exactly like a dead part."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:air .
orexis:air a mc:Peripheral ; orexis:localId "air" ; mc:hasPin orexis:air_float .
orexis:air_float a mc:Pin ; mc:pinRole mc:GroundPinRole .
""" + _leg("air", "d", "onewire:DataPinRole", 32)))


def test_a_leg_the_PART_never_connects_is_accepted():
    """What the component IS. A DHT's third pin connects to nothing inside it — the package has
    four positions and the die uses three — and that is true of every DHT ever made. Intrinsic,
    so it is a role."""
    assert _conforms(_wiring("""
    sosa:hosts orexis:air .
orexis:air a mc:Peripheral ; orexis:localId "air" ; mc:hasPin orexis:air_nc .
orexis:air_nc a mc:Pin ; mc:pinRole mc:NotConnectedPinRole .
""" + _leg("air", "d", "onewire:DataPinRole", 32)))


def test_a_leg_THIS_BUILD_leaves_unwired_is_accepted():
    """What the build DID, which is a different fact and cannot be a role.

    A board has thirty legs and a world wires seven; nothing about the ESP32 says which, and the
    same board in another world uses different ones. Putting that in a role would file a fact
    about one breadboard inside the description of a component.
    """
    assert _conforms(_wiring("""
    sosa:hosts orexis:air .
orexis:air a mc:Peripheral ; orexis:localId "air" ; mc:hasPin orexis:air_spare .
orexis:air_spare a mc:Pin ; mc:pinRole mc:DigitalOutPinRole ; mc:unused true .
""" + _leg("air", "d", "onewire:DataPinRole", 32)))


def test_a_leg_that_is_merely_forgotten_is_still_refused():
    """The whole point of the other two. Silence must go on meaning 'I have not thought about
    this leg' — a floating ground is the commonest reason a three-legged part answers with
    silence, and it looks exactly like a dead part."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:air .
orexis:air a mc:Peripheral ; orexis:localId "air" ; mc:hasPin orexis:air_spare .
orexis:air_spare a mc:Pin ; mc:pinRole mc:DigitalOutPinRole .
""" + _leg("air", "d", "onewire:DataPinRole", 32)))


def test_a_five_volt_rail_into_a_three_volt_input_is_refused():
    """The fault this whole remodelling exists to make sayable, and the one that cost an evening.

    A three-legged sensor carries a pull-up to its OWN VCC, so its data line idles at whatever
    it is powered from. On VIN that is 5V, presented to an input that is not 5V tolerant — which
    does not fail, it degrades over weeks and looks like a flaky sensor. There was nowhere in
    the old model to say which rail a device was on, so there was nothing to check.
    """
    assert not _conforms(_wiring("""
    sosa:hosts orexis:air .
orexis:air a mc:Peripheral ; orexis:localId "air" ; mc:hasPin orexis:air_vcc , orexis:air_gnd .
orexis:air_vcc a mc:Pin ; mc:pinRole mc:PowerPinRole .
orexis:air_gnd a mc:Pin ; mc:pinRole mc:GroundPinRole .
orexis:t_vin a mc:Pin ; mc:pinRole mc:PowerPinRole ; mc:railVolts 5.0 .
orexis:test_board mc:hasPin orexis:t_vin .
[] a mc:Wire ; mc:joins orexis:air_vcc , orexis:t_vin .
[] a mc:Wire ; mc:joins orexis:air_gnd , orexis:t_gnd .
""" + _leg("air", "d", "onewire:DataPinRole", 32, powered=False)))


def test_a_dht_must_name_all_three_of_its_legs():
    """Its data line alone was the old model's best effort — there was nowhere to put the
    other two — and it is precisely the missing ones that go wrong."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:air .
orexis:air a dht11:Dht11 ; orexis:localId "air" .
""" + _leg("air", "d", "onewire:DataPinRole", 32, powered=False)))


def test_two_peripherals_on_one_gpio_are_refused():
    """The mistake made months later, when a device is added and nobody re-reads the file."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:probe , orexis:led .
orexis:probe a probe:CapacitiveMoistureProbe ; orexis:localId "probe" ; orexis:pin [ mc:pinRole mc:AnalogInPinRole ; mc:gpio 34 ] .
orexis:led a rgbled:RgbLed ; orexis:localId "led" ; orexis:pin [ mc:pinRole rgbled:RedPinRole ; mc:gpio 34 ] ,
                            [ mc:pinRole rgbled:GreenPinRole ; mc:gpio 26 ] ,
                            [ mc:pinRole rgbled:BluePinRole ; mc:gpio 27 ] .
"""))


def test_one_device_using_a_gpio_twice_is_refused():
    """Same rule, inside a single device: an RGB LED with two legs on one line."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:led .
orexis:led a rgbled:RgbLed ; orexis:localId "led" ; orexis:pin [ mc:pinRole rgbled:RedPinRole ; mc:gpio 25 ] ,
                            [ mc:pinRole rgbled:GreenPinRole ; mc:gpio 25 ] ,
                            [ mc:pinRole rgbled:BluePinRole ; mc:gpio 27 ] .
"""))


@pytest.mark.parametrize("missing", ["Red", "Green", "Blue"])
def test_an_rgb_led_missing_a_colour_is_refused(missing):
    """One channel that never lights looks, from across the room, exactly like a sleeping board."""
    legs = {"Red": "mc:gpio 25", "Green": "mc:gpio 26", "Blue": "mc:gpio 27"}
    del legs[missing]
    pins = " ,\n           ".join(f"[ mc:pinRole orexis:{c} ; {g} ]" for c, g in legs.items())
    assert not _conforms(_wiring(f"""
    sosa:hosts orexis:led .
orexis:led a rgbled:RgbLed ; orexis:localId "led" ; orexis:pin {pins} .
"""))


def test_a_pin_without_a_role_is_refused():
    """A number with no role cannot be checked for direction, so it cannot be checked at all."""
    assert not _conforms(_wiring("""
    sosa:hosts orexis:probe .
orexis:probe a probe:CapacitiveMoistureProbe ; orexis:localId "probe" ; orexis:pin [ mc:gpio 34 ] .
"""))


def test_a_board_without_a_model_is_refused():
    """The model is what a person orders a replacement by, and what a generated firmware
    configuration will have to name."""
    data = rdflib.Graph()
    for path in loader.ontology_files():
        data.parse(path, format="turtle")
    data.parse(data="""
@prefix orexis:    <http://example.org/orexis#> .
@prefix mc: <http://example.org/orexis/microcontroller#> .
orexis:nameless a mc:Microcontroller ; orexis:localId "nameless" .
""", format="turtle")
    assert not _conforms(data)


# --- what the equipment can honour ------------------------------------------------------------

def test_a_mandate_past_what_the_board_can_honour_is_refused():
    """A world may commit an agent to less than its equipment allows; never to more.

    `MandateWithinTheConstitutionShape` checks the other end — what the SOCIETY permits anyone.
    This is what the HARDWARE permits this one, and until `ssn-system:Frequency` there was
    nothing to check it against: an agent could be committed to a ten-second cadence a board
    would never keep, `stale_after_s` would compute freshness from the interval it asked for,
    and a healthy board would read as a quiet one.

    700 against `simulation`'s fern, which commits `notBelow 600`. The floor has to exceed the
    mandate to conflict with it — a board FASTER than its mandate contradicts nothing, which is
    why the shipped worlds still validate with a KY-015 declaring two seconds.
    """
    report = _report(_mutate("""
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX sensing: <http://example.org/orexis/sensing#>
INSERT DATA { GRAPH <http://example.org/orexis/graph/world> {
  <http://example.org/orexis/world/simulation#moisture_sensor_fern> ssn-system:hasSystemCapability [
      a ssn-system:SystemCapability ;
      ssn-system:hasSystemProperty [ a ssn-system:Frequency , schema:PropertyValue ; schema:value 700 ; schema:unitCode unit:SEC ] ] } }"""))
    assert "Conforms: False" in report
    assert "equipment can honour" in report


def test_a_board_faster_than_its_mandate_is_not_refused():
    """The negative half, and the reason the shipped worlds still pass: a device that can be read
    every second under a mandate committing to ten minutes has contradicted nothing. Without this
    the shape above would be satisfied by any floor at all, which is a shape that fires on the
    ordinary case.

    It asks the VERDICT rather than reading "Conforms: True" off the report, which is the same
    lesson `_conforms` above records: a report is now false whenever any agent wants anything,
    because a want is a shape and an unmet want is a result. The verdict is what refuses a
    world, and the message is what says why — so the negative case asserts both.
    """
    data = _mutate("""
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX sensing: <http://example.org/orexis/sensing#>
INSERT DATA { GRAPH <http://example.org/orexis/graph/world> {
  <http://example.org/orexis/world/simulation#moisture_sensor_fern> ssn-system:hasSystemCapability [
      a ssn-system:SystemCapability ;
      ssn-system:hasSystemProperty [ a ssn-system:Frequency , schema:PropertyValue ; schema:value 1 ; schema:unitCode unit:SEC ] ] } }""")
    assert _conforms(data), _report(data)
    assert "equipment can honour" not in _report(data)


# --- the target answers to the region ------------------------------------------------------
#
# The split these check: a plant states the ranges it needs, publicly in the world; its agent
# DEDUCES a region from them, publicly and derived; and it picks a target inside that region,
# privately in its own beliefs. See
# knowledge/decisions/desire-is-deduced-from-the-ranges-the-world-states.md.

def test_an_aim_outside_the_agents_region_is_refused():
    """A desire is a pick WITHIN a range. Moved outside it, the agent will not start.

    Fern grows in 0.45-0.65, so 0.90 is not a bold opinion about water — it is a number with
    nothing behind it. Worth stating why this can be checked at all: the region is public and
    the aim is private, and they meet in exactly one place — inside the agent, whose store holds
    the world it booted with and its own beliefs. Nothing outside the agent ever sees the number.
    """
    data = _mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ?aim schema:value 0.55 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ?aim schema:value 0.90 }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{
                 <http://example.org/orexis/world/simulation#fern_agent> sensing:aims ?aim . ?aim schema:value 0.55 }} }}""")
    assert not _conforms(data)
    assert "pick within a range" in _report(data)


def test_a_region_in_another_property_does_not_judge_the_moisture_target():
    """An agent that also holds a HUMIDITY region must not have its MOISTURE target checked
    against it. The constraint matches on `market:aboutProperty`, which is what the desire term
    itself declares — the same reason `_is_mine` compares the property in the desire module.

    Written against a region — a shape the agent HOLDS — rather than against a plant's range,
    which is what the aim check now reads. It matters that it is the region: fern already holds two, so this could have been
    written by moving the target against the temperature one — and 0.55 sits nowhere near 18-24
    either, which would make the test pass for a reason having nothing to do with the property
    match. A humidity region nothing else in this world has is the case with only one exit.

    Without the property match this passes vacuously, so it is written as a region the target
    would certainly violate: 0.55 is nowhere near 0.60-0.80.

    Built as TWO SIDE SHAPES since #242, because that is what the aim check now reads — the
    floor off the Below shape's `sh:maxExclusive`, the ceiling off the Above shape's
    `sh:minExclusive`, each identified by `orexis:violationIs`. Left in the old single-shape form
    this test went on passing and stopped meaning anything: the query matched the fixture
    nowhere, so the property match it exists to prove was no longer being exercised at all.
    A fixture that drifts from what the derivation emits fails silently, in the direction of
    green — which is why it is now a DESIRE NODE carrying the shape through `orexis:metWhen`,
    the form the derivation emits since a-desire-states-its-own-measure, for the same reason.
    """
    data = _mutate("""
        INSERT { GRAPH <http://example.org/orexis/graph/constraint> {
            <http://example.org/orexis/world/simulation#fern_agent> <http://example.org/orexis#holds> [
                a <http://example.org/orexis#Desire> ;
                <http://example.org/orexis#scope> <http://example.org/orexis#Always> ;
                <http://www.w3.org/ns/ssn/forProperty>
                    <http://example.org/orexis/water#AirHumidity> ;
                <http://example.org/orexis#metWhen> [
                a <http://www.w3.org/ns/shacl#NodeShape> ;
                <http://www.w3.org/ns/shacl#targetNode>
                    <http://example.org/orexis/world/simulation#fern_agent> ;
                <http://www.w3.org/ns/ssn/forProperty>
                    <http://example.org/orexis/water#AirHumidity> ;
                <http://www.w3.org/ns/shacl#property> [
                    <http://example.org/orexis#violationIs> <http://example.org/orexis#Below> ;
                    <http://www.w3.org/ns/shacl#path> (
                        <http://example.org/orexis#actsFor>
                        [ <http://www.w3.org/ns/shacl#inversePath>
                          <http://www.w3.org/ns/sosa/hasFeatureOfInterest> ] ) ;
                    <http://www.w3.org/ns/shacl#qualifiedMaxCount> 0 ;
                    <http://www.w3.org/ns/shacl#qualifiedValueShape> [
                        <http://www.w3.org/ns/shacl#property> [
                            <http://www.w3.org/ns/shacl#path>
                                <http://www.w3.org/ns/sosa/observedProperty> ;
                            <http://www.w3.org/ns/shacl#hasValue>
                                <http://example.org/orexis/water#AirHumidity> ] ,
                        [
                            <http://www.w3.org/ns/shacl#path>
                                <http://www.w3.org/ns/sosa/hasSimpleResult> ;
                            <http://www.w3.org/ns/shacl#maxExclusive> 0.60 ] ] ] ,
                [
                    <http://example.org/orexis#violationIs> <http://example.org/orexis#Above> ;
                    <http://www.w3.org/ns/shacl#path> (
                        <http://example.org/orexis#actsFor>
                        [ <http://www.w3.org/ns/shacl#inversePath>
                          <http://www.w3.org/ns/sosa/hasFeatureOfInterest> ] ) ;
                    <http://www.w3.org/ns/shacl#qualifiedMaxCount> 0 ;
                    <http://www.w3.org/ns/shacl#qualifiedValueShape> [
                        <http://www.w3.org/ns/shacl#property> [
                            <http://www.w3.org/ns/shacl#path>
                                <http://www.w3.org/ns/sosa/observedProperty> ;
                            <http://www.w3.org/ns/shacl#hasValue>
                                <http://example.org/orexis/water#AirHumidity> ] ,
                        [
                            <http://www.w3.org/ns/shacl#path>
                                <http://www.w3.org/ns/sosa/hasSimpleResult> ;
                            <http://www.w3.org/ns/shacl#minExclusive> 0.80 ] ] ] ] ] } }
        WHERE {}""")
    assert _conforms(data), _report(data)


def test_a_denomination_without_a_direction_is_refused():
    """Half the claim is not a smaller claim (#127). A valuation that says what bids are priced
    in must say which way winning moves it — a reflex handed the denomination alone falls back
    to a hardcoded sign, and a model handed it cannot act at all. Targeted at the T-Box, so it
    fires on whoever ratifies a domain, not on any agent's beliefs.

    A SYNTHETIC term rather than water's with its direction deleted, because `conforms` re-adds
    the ontology from the files — a mutation of the store's copy is quietly healed on the way
    in, and the first draft of this test passed vacuously exactly that way.
    """
    data = _flatten(genesis_store())
    data.parse(data="""
        @prefix market: <http://example.org/orexis/market#> .
        @prefix water: <http://example.org/orexis/water#> .
        <http://example.org/orexis/heat#wattsPerDegree>
            market:aboutProperty water:AirTemperature .
    """, format="turtle")
    assert not _conforms(data)
    assert "state its direction" in _report(data)


def test_a_plant_still_holds_no_desire_of_its_own():
    """The range is not an aim wearing a different name. The older rule stands: a plant may
    say what it needs and may not say what it wants."""
    data = _mutate("""
        INSERT { GRAPH <http://example.org/orexis/graph/world> {
            <http://example.org/orexis/world/simulation#fern> <http://example.org/orexis/sensing#aims> [
                <http://www.w3.org/ns/ssn/forProperty> <http://example.org/orexis/water#SoilMoisture> ;
                <https://schema.org/value> 0.55 ] } }
        WHERE {}""")
    assert not _conforms(data)
    assert "a plant holds no desire" in _report(data)


def _duplicate_probe_in_its_own_patch() -> rdflib.Graph:
    """The second probe again, but each names its patch — the #98 statement."""
    return _mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            orexis:fern_east a <http://www.w3.org/ns/sosa/Sample> ;
                <http://www.w3.org/ns/sosa/isSampleOf> <http://example.org/orexis/world/simulation#fern> .
            orexis:fern_west a <http://www.w3.org/ns/sosa/Sample> ;
                <http://www.w3.org/ns/sosa/isSampleOf> <http://example.org/orexis/world/simulation#fern> .
            <http://example.org/orexis/world/simulation#moisture_sensor_fern> sensing:samples orexis:fern_east .
            orexis:second_probe_fern a sosa:Sensor , device:Device ; orexis:localId "second_probe_fern" ;
                mqtt:onBus <http://example.org/orexis/world/simulation#local_bus> ; sensing:senseMode sensing:ScheduledProcedure ; sensing:monitors <http://example.org/orexis/world/simulation#fern> ;
                sensing:samples orexis:fern_west ;
                sosa:observes water:SoilMoisture ;
                scaling:quantityUnit unit:UNITLESS ;
                mqtt:readingTopic "sensors/second_probe_fern/reading" ;
                mqtt:commandTopic "sensors/second_probe_fern/command" .
            <http://example.org/orexis/world/simulation#fern_agent> sensing:polls orexis:second_probe_fern .
        }} }} WHERE {{}}""")


def test_two_probes_in_two_stated_patches_are_two_honest_records_and_silent():
    """The warning's cure, one statement away (#98): each probe in its own sosa:Sample of the
    pot is no longer a collision — two features, two observation nodes, nothing to warn about."""
    data = _duplicate_probe_in_its_own_patch()
    assert _conforms(data)
    assert "another sensor already reads this property" not in _report(data), \
        "two probes in two stated patches must not be warned about — that IS the cure"


def test_a_patch_of_the_wrong_pot_is_refused():
    """A probe claiming a patch of some other pot would key its readings under a feature
    nobody walks back to the right plant — recorded faithfully, found by no one."""
    assert not _conforms(_mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            orexis:tomato_patch a <http://www.w3.org/ns/sosa/Sample> ;
                <http://www.w3.org/ns/sosa/isSampleOf> <http://example.org/orexis/world/simulation#tomato> .
            <http://example.org/orexis/world/simulation#moisture_sensor_fern> sensing:samples orexis:tomato_patch .
        }} }} WHERE {{}}"""))


# --- the two result forms, and what a sensor detects (#100, #101) ------------------------------


def _observation(extra: str) -> rdflib.Graph:
    """A synthetic observation beside the world's own, to hold the shape to its xone."""
    return _mutate(f"""
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            orexis:obs_test a sosa:Observation ;
                sosa:hasFeatureOfInterest <http://example.org/orexis/world/simulation#fern> ;
                sosa:observedProperty water:SoilMoisture ;
                sosa:resultTime "2026-08-15T10:00:00Z"^^xsd:dateTime ;
                sosa:madeBySensor <http://example.org/orexis/world/simulation#moisture_sensor_fern> ;
                sosa:usedProcedure sensing:ScheduledProcedure ;
                orexis:underWorldVersion 1 ;
                prov:wasGeneratedBy <http://example.org/orexis/world/simulation#fern_agent> ;
                {extra} .
        }} }} WHERE {{}}""")


def test_a_structured_result_is_the_legal_alternative_to_the_scalar():
    """#101: one of the two forms — the scalar shortcut, or a sosa:Result with parts for the
    reading that is genuinely multi-component. The accelerometer's door, held open."""
    assert _conforms(_observation(
        'sosa:hasResult [ a sosa:Result ; orexis:x "0.1"^^xsd:decimal ]'))


def test_an_observation_with_neither_result_form_is_refused():
    """Both-optional would be the silent-emptiness failure: an observation carrying no value at
    all, recorded and satisfying everything."""
    assert not _conforms(_observation('rdfs:label "empty"'))


def test_an_observation_with_both_result_forms_is_refused():
    assert not _conforms(_observation(
        'sosa:hasSimpleResult "0.4"^^xsd:decimal ; sosa:hasResult [ a sosa:Result ]'))


def test_what_a_probe_detects_is_entailed_from_its_part():
    """#100: the datasheet fact reaches every device through the class — the hasValue closure —
    and the stimulus states what it stands in for."""
    st = genesis_store(world="sensing")
    from orexis_agent_progression.store import bindings

    rows = bindings(st.query("""
SELECT ?stimulus ?property WHERE {
  ?probe a <http://example.org/orexis/moisture-probe#CapacitiveMoistureProbe> ;
         <http://www.w3.org/ns/ssn/detects> ?stimulus .
  ?stimulus <http://www.w3.org/ns/ssn/isProxyFor> ?property }"""))
    assert rows, "the probe detects nothing — the hasValue entailment or the proxy is gone"
    assert all(r["property"].endswith("SoilMoisture") for r in rows)


def test_detecting_something_that_is_not_a_stimulus_is_refused():
    """SSN's own restriction, restated because borrowed IRIs bring no axioms with them."""
    assert not _conforms(_mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            <http://example.org/orexis/world/simulation#moisture_sensor_fern> <http://www.w3.org/ns/ssn/detects> water:SoilMoisture .
        }} }} WHERE {{}}"""))


def test_a_watched_channel_on_a_push_device_is_legal():
    """The sentinel's wiring (#151): a push device may promise announce-on-crossing — its band
    is compiled at flash from the world's own range, because a board that takes no orders can
    still keep a promise the world wrote. What stays refused is the gap between: a scheduled
    device without the channel its bands would arrive on."""
    data = _mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            orexis:sentinel_x a sosa:Sensor , device:Device ; orexis:localId "sentinel_x" ;
                mqtt:onBus <http://example.org/orexis/world/simulation#local_bus> ;
                sensing:senseMode sensing:PushProcedure ;
                <http://www.w3.org/ns/ssn/implements> sensing:AlarmProcedure ;
                sensing:monitors <http://example.org/orexis/world/simulation#tomato> ;
                sosa:observes <http://example.org/orexis/water#AirHumidity> ;
                scaling:quantityUnit unit:UNITLESS ;
                mqtt:readingTopic "sensors/sentinel_x/reading" .
        }} }} WHERE {{}}""")
    assert _conforms(data), _report(data)


# --- the alarm promise held to the silicon (#181) ----------------------------

def test_the_shipped_wiring_keeps_its_alarm_promise():
    """The moisture channel's promise — entailed from governed:Node — sits on an analog pin
    wired to a board whose class states its watcher reaches analog. The world above already
    conformed; this pins WHY, so the shape below is known to be non-vacuous company."""
    st = genesis_store(world="sensing")
    rows = st.query("""SELECT ?role WHERE {
        ?ch <http://www.w3.org/ns/ssn/implements>
            <http://example.org/orexis/sensing#AlarmProcedure> ;
            <http://example.org/orexis/microcontroller#hasPin> ?leg .
        ?leg <http://example.org/orexis/microcontroller#pinRole> ?role .
        ?wire <http://example.org/orexis/microcontroller#joins> ?leg , ?pin .
        ?board <http://example.org/orexis/microcontroller#hasPin> ?pin ;
               <http://example.org/orexis/microcontroller#watcherReachesRole> ?role . }""")
    from orexis_agent_progression.store import bindings
    assert bindings(rows), (
        "the sensing world's watched channel must be visibly within its board's reach — if "
        "this is empty the wiring shape is passing vacuously")


def test_a_promise_no_watcher_can_keep_is_refused():
    """Promise announce-on-crossing on the DHT channel: its data pin is one-wire, which the
    ESP32's FSM watcher cannot speak — the fact that lived in a comment now refuses a world."""
    st = genesis_store(world="sensing")
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <http://example.org/orexis/world/sensing#air_temp_fern>
            <http://www.w3.org/ns/ssn/implements>
            <http://example.org/orexis/sensing#AlarmProcedure> }} }}""")
    assert not _conforms(_flatten(st, WORLDS_ROOT / "sensing")), (
        "a channel whose signal pin no sleep-watcher reaches must not be allowed to promise")


# --- a deployment is held to its instruments' ranges (#111) -------------------

_SENSING_NS = "http://example.org/orexis/world/sensing#"


def test_the_windowsill_sits_inside_every_stated_range():
    """Non-vacuity for the shape below: the join it polices — deployment envelope to
    instrument range, matched on property AND unit — must actually bind in the shipped
    world, or the conformance above is silence, not coverage."""
    st = genesis_store(world="sensing")
    rows = st.query("""SELECT ?sensor ?u WHERE {
        ?d <http://www.w3.org/ns/ssn/deployedSystem> ?deployed .
        ?deployed (<http://www.w3.org/ns/ssn/hasSubSystem>)* ?sensor .
        ?sensor <http://www.w3.org/ns/sosa/observes> ?p .
        ?d <http://www.w3.org/ns/ssn/systems/inCondition> ?k .
        ?k <http://www.w3.org/ns/ssn/forProperty> ?p ; <https://schema.org/unitCode> ?u .
        ?sensor <http://www.w3.org/ns/ssn/systems/hasSystemCapability> ?c .
        ?c <http://www.w3.org/ns/ssn/systems/hasSystemProperty> ?r .
        ?r a <http://www.w3.org/ns/ssn/systems/MeasurementRange> ;
           <https://schema.org/unitCode> ?u . }""")
    from orexis_agent_progression.store import bindings
    found = bindings(rows)
    assert len(found) >= 2, (
        "the windowsill envelope must reach the DHT11's two ranged channels — if this is "
        "empty the range shape is passing vacuously")


def test_a_deployment_past_the_instruments_range_is_refused():
    """THE terrace test. Send the windowsill outdoors — a Berlin winter reaches -15 °C — and
    the DHT11's own datasheet figures (0..50, stated at the class since the package was
    written) refuse the world. The answer the graph gave in conversation, now given by
    orexis-validate instead."""
    st = genesis_store(world="sensing")
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{_SENSING_NS}fern_windowsill_deployment>
            <http://www.w3.org/ns/ssn/systems/inCondition> [
                a <http://www.w3.org/ns/ssn/systems/Condition> ;
                <http://www.w3.org/ns/ssn/forProperty> <http://example.org/orexis/water#AirTemperature> ;
                <https://schema.org/minValue> -15.0 ;
                <https://schema.org/maxValue> 40.0 ;
                <https://schema.org/unitCode> <http://qudt.org/vocab/unit/DEG_C> ] }} }}""")
    assert not _conforms(_flatten(st, WORLDS_ROOT / "sensing")), (
        "an envelope the instrument's stated range cannot contain must refuse the world")


def test_an_envelope_in_an_alien_unit_is_skipped_not_refused():
    """The stated seam: PERCENT and a fraction are not comparable, and refusing on
    arithmetic that means nothing would be worse than skipping. Asserted so the silence
    is a documented choice rather than a hole nobody chose."""
    st = genesis_store(world="sensing")
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{_SENSING_NS}fern_windowsill_deployment>
            <http://www.w3.org/ns/ssn/systems/inCondition> [
                a <http://www.w3.org/ns/ssn/systems/Condition> ;
                <http://www.w3.org/ns/ssn/forProperty> <http://example.org/orexis/water#AirHumidity> ;
                <https://schema.org/minValue> 0.0 ;
                <https://schema.org/maxValue> 1.0 ;
                <https://schema.org/unitCode> <http://qudt.org/vocab/unit/UNITLESS> ] }} }}""")
    assert _conforms(_flatten(st, WORLDS_ROOT / "sensing")), (
        "a mismatched unit must be skipped — comparing 0..1 against 20..90 PERCENT would "
        "refuse on meaningless arithmetic")


def test_a_venue_that_takes_presentations_must_say_how_long_it_holds_a_claim():
    """Opening shop is still ONE authored triple, and the window is not it.

    Requiring `market:redeemWindowS` in the derivation was the first attempt, and it was wrong
    in a way worth keeping a test about: the venue then failed to ARISE without one, so a world
    that stated `market:matchesBy` and nothing else had no market and no error — consent had
    quietly come to cost two triples. The venue now arises either way and the shape says what
    is missing, which is the difference between a world that is refused and a world that is
    silently smaller than its author thought.

    Deleting the window rather than building a venue by hand, because the deletion is the case
    that actually happens: somebody adds a source, copies the neighbouring one, and drops a line.
    """
    #  Wherever it lives, by asking rather than by naming a graph: the world states the
    #  window and the derivation copies it onto the venue, and `_mutate` re-derives by adding,
    #  so deleting only the authored triple leaves the derived one behind — a world that
    #  validates for a fact its files no longer contain.
    data = _mutate("""
        DELETE { GRAPH ?g { ?s <http://example.org/orexis/market#redeemWindowS> ?w } }
        WHERE  { GRAPH ?g { ?s <http://example.org/orexis/market#redeemWindowS> ?w } }""")
    assert not _conforms(data)
    assert "how long it holds a winner's claim" in _report(data)


# --- the guard on the cache above -------------------------------------------------------------

def test_a_graph_is_never_changed_after_it_is_validated():
    """`_validated` memoises pyshacl's verdict ON the graph, which is only safe while no test
    validates a graph and then changes it. That is true today (#272) and is exactly the kind of
    thing a later test would break without noticing, because the stale verdict would simply be
    the one from before the change — a passing assertion about a world that no longer exists.

    A source scan rather than a runtime check: the hazard is a test that COULD be written, and
    the cheapest moment to refuse it is the one where someone writes it.
    """
    import ast

    source = ast.parse(pathlib.Path(__file__).read_text())
    functions = [fn for fn in source.body
                 if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_")]
    mutating = ("add", "remove", "parse", "update", "set", "addN", "bind")

    offenders = []
    for fn in functions:
        validated = False
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id in ("_conforms", "_report", "_validated"):
                validated = True
            elif validated and isinstance(node, ast.Call) \
                    and isinstance(node.func, ast.Attribute) and node.func.attr in mutating:
                offenders.append(f"{fn.name}: .{node.func.attr}() after validating")

    assert functions, "no test functions found — the scan stopped matching"
    assert not offenders, (
        "a graph is mutated after being validated, so `_validated`'s cached verdict is stale:\n  "
        + "\n  ".join(offenders)
        + "\nEither build a fresh graph for the second question, or drop the memoisation."
    )


def test_no_capability_asks_what_a_thing_is_made_of():
    """A role is a role. Nothing that observes, acts, bids or hosts may name `device:`.

    The rule this guards is `a-stand-in-is-not-a-device`. `sensing:polls` used to demand
    `sosa:Sensor , device:Device` and `actuation:hasActuator` the actuator equivalent — the
    intersection left behind when our two classes were retired for SOSA's — so every simulated
    world declared a physical edge node and denied it in the next line, and W3C's own DHT22
    description had to be told it was hardware before our shapes would take it.

    Substrate is the inventory's question and the harness's: `mc:hasPin` asks it, because boards
    have pins. Whether a role has a referent at all is `sim:simulatedBy`, on `ssn:System`. A
    capability asks neither.

    Prose is exempt — the two ontologies carry the audit that reached this conclusion, and it
    cannot be written without naming the word. Only what a machine reads is checked.
    """
    offenders = {}
    for path in sorted(f for p in loader.of_kind("capability") for f in p.path.rglob("*.ttl")):
        code = _without_comments(path.read_text())
        for line in code.splitlines():
            if "device:" in line or "orexis/device#" in line:
                offenders.setdefault(str(path), []).append(line.strip())
    assert not offenders, (
        "a capability names the substrate vocabulary — a role asks for the role alone "
        "(a-stand-in-is-not-a-device):\n" + "\n".join(
            f"  {p}: {ls}" for p, ls in offenders.items()))


def _without_comments(text: str) -> str:
    """Turtle with its `#` comments and its string literals removed — the machine-read part."""
    import re
    text = re.sub(r'"""(?:.|\n)*?"""', '""', text)
    text = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', text)
    text = re.sub(r"^\s*#.*$", "", text, flags=re.M)
    return re.sub(r"\s#.*$", "", text, flags=re.M)


def test_a_valve_on_the_bus_must_state_where_it_takes_commands():
    """Moved from actuation to the transport with #404, and it must still fire from there.

    `actuation:ActuatorShape` used to demand `mqtt:commandTopic` of EVERY actuator — a capability
    deciding how its subject must be spoken to. `mqtt:MqttActuatorShape` demands it of an actuator
    on a bus, which is the honest scope, and this proves the requirement did not evaporate in the
    move.
    """
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#valve_fern> mqtt:commandTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#valve_fern> mqtt:commandTopic ?t }} }}"""))


def test_a_stood_in_valve_must_state_where_it_reports():
    """The other half of #404's move: `sim:StandInReportsShape`.

    Without a status topic the stand-in opens into nowhere — the command is verified, the dose
    computed, and the soil stays dry, because a simulated sensor waters only on what the valve
    reports and physics has no wire between two containers.
    """
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#valve_fern> mqtt:statusTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#valve_fern> mqtt:statusTopic ?t }} }}"""))


def test_no_capability_shape_names_a_transport():
    """A capability says what a role must BE, never how it must be spoken to (#404).

    The boundary this guards is `a-shape-belongs-to-the-vocabulary-it-checks`: a shape can be
    deleted with the package whose terms it CONSTRAINS, so a constraint on `mqtt:` left behind in
    a capability would outlive the transport and refuse every world for a vocabulary that is no
    longer declared. A selector may still be foreign — one that matches nothing costs nothing.

    Shapes only. A capability's `rules.ru` may still join through a transport's terms: sensing's
    three derivation rules do, deliberately, and `knowledge/domain/channel.md` records why — a
    transport-neutral class earns its place the day a second transport exists, and a premise is
    its own capability's to state whatever happens.
    """
    transports = {p.name for p in loader.of_kind("transport") if p.path.is_dir()
                  and not p.name.startswith("__")}
    assert transports, "the transport family glob stopped matching"
    offenders = {}
    for path in sorted(f for p in loader.of_kind("capability") for f in p.path.rglob("shapes.ttl")):
        code = _without_comments(path.read_text())
        for name in transports:
            for line in code.splitlines():
                if f"{name}:" in line or f"orexis/{name}#" in line:
                    offenders.setdefault(str(path), []).append(line.strip())
    assert not offenders, (
        "a capability's shapes constrain a transport's vocabulary — that constraint belongs "
        "where it can be deleted with the transport (a-shape-belongs-to-the-vocabulary-it-checks):"
        "\n" + "\n".join(f"  {p}: {ls}" for p, ls in offenders.items()))


def test_every_shape_says_what_it_is_for():
    """A named `sh:NodeShape` carries an `rdfs:comment`, because nothing else can read one.

    The audit behind #275 asked whether any other shape's name or comment had drifted from its
    constraints, and found two: `sensing:BeyondSurvivalShape`, named for a check that had moved
    into the deduction, and `market:MarketShape`, which said *all three of its channels* while
    demanding four. **Neither is mechanically checkable** — SHACL does not care what a shape is
    called, and no gate can read a sentence and a constraint and say they disagree.

    What IS checkable is that the sentence exists. A shape with no comment cannot be compared to
    its constraints at all, by a reader or by anyone auditing later, and one had none:
    `orexis:WorldVersionShape`, alone among every shape in the repo.

    Blank-node shapes are excluded on purpose: an `sh:property [ … ]` is a constraint rather than
    a shape somebody names, and it carries an `sh:message` where it needs to say something.
    """
    import rdflib

    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    files = sorted(pathlib.Path("agent").glob("shapes.ttl")) + \
        sorted(pathlib.Path("packages").rglob("shapes.ttl"))
    assert files, "no shapes files found — the globs stopped matching"

    silent, seen = [], 0
    for path in files:
        graph = rdflib.Graph().parse(path)
        for shape in graph.subjects(rdflib.RDF.type, SH.NodeShape):
            if not isinstance(shape, rdflib.URIRef):
                continue
            seen += 1
            if not str(graph.value(shape, rdflib.RDFS.comment) or "").strip():
                silent.append(f"{path}: {str(shape).rsplit('#', 1)[-1]}")
    assert seen, "no named node shapes found — the type scan stopped matching"
    assert not silent, (
        "a shape that says nothing about itself — a reader meets it by its name alone, and a "
        "name is the thing that drifts (#275):\n  " + "\n  ".join(silent))
