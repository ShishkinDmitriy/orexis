"""A simulated device is a device, and nothing an agent runs may notice otherwise.

The claim these defend is narrow and load-bearing: `world/simulation` must exercise the SAME
code as a world with real boards. It used to exercise a parallel implementation — the agent held
a model and reimplemented perceiving — which meant the simulation could pass while the real path
was broken. That is the weakest possible form of simulation, and the reason it went unnoticed for
so long is that nothing asserted the opposite.

So the first test here is the whole point of the change, expressed as the only thing that can go
wrong quietly: an agent in the simulated world deriving something other than what an agent
wired to hardware derives.
"""

import rdflib

from agent.ontology import WORLD_GRAPH
from agent.store import bindings

from conftest import WORLDS_ROOT, genesis_store, load_wired
from test_shapes import _conforms, _flatten

AG = "http://example.org/orexis#"
SIM = "http://example.org/orexis/sim#"   # what stands in for hardware nobody built

_CAPS_Q = f"""
SELECT ?id ?cap WHERE {{ 
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{AG}hasCapability> ?cap  }}"""


def _caps(world: str) -> dict[str, set[str]]:
    st = genesis_store(world=world)
    out: dict[str, set[str]] = {}
    for row in bindings(st.query(_CAPS_Q)):
        out.setdefault(row["id"], set()).add(row["cap"].rsplit("#", 1)[-1])
    return out


def test_a_simulated_sensor_derives_the_ordinary_capability():
    """The point of the exercise. `fern` polls a device that does not exist and still comes out
    sensing:Subscribing — the same capability, running the same module, as a fern on a real board."""
    assert "Subscribing" in _caps("simulation")["fern"]


def test_no_agent_derives_a_simulated_sensing():
    """There is no such capability any more, and nothing may quietly reintroduce one.

    A world that grew a `SimulatedSensing` back would be a second sensing implementation,
    which is exactly the thing that let a broken real path go undetected.
    """
    for world in ("sensing", "simulation"):
        for agent, caps in _caps(world).items():
            assert not any("Simulated" in c and "Sensing" in c for c in caps), \
                f"{world}/{agent} derived {caps}"


def test_the_simulated_world_derives_what_a_wired_one_does():
    """If these ever diverge, the simulation has stopped standing in for anything.

    This compared `simulation` to `society` — two market worlds with the same wiring shape, one
    simulated and one not — and asserted the two ferns derived exactly the same set. `society`
    is gone, and the only world left with real devices is `sensing`, which has no market. So
    equality is the wrong assertion: a fern that cannot bid is not a divergence, it is a
    different world.

    What survives is sharper. Everything `sensing`'s fern derives, `simulation`'s fern derives
    too, and what the market world adds follows from its fern having a STAKE: `ag:actsFor` a
    plant that states what it needs buys both the desire and the standing to bid for it, and
    neither is a fact about the hardware. Pinning the difference rather than asserting sameness
    is what still catches the failure this was written for: if a simulated probe ever stopped
    deriving `Subscribing` the way a real one does, it would fall out of the subset.
    """
    wired, simulated = _caps("sensing")["fern"], _caps("simulation")["fern"]
    assert wired <= simulated, (
        f"the wired fern derives {wired - simulated} that the simulated one does not — "
        f"the simulation has stopped standing in for hardware")
    #  `Reflex`, `Keeping` and `Deducing` were all in this difference and none is a capability
    #  any more — deciding, committing and wanting are the kernel's, granted by nothing. What a
    #  stake still buys is the SHAPES it must satisfy and the regions it holds, not a module;
    #  the one grant left in the difference is the market position.
    assert simulated - wired == {"Bidding"}, \
        "the simulated world differs by something other than its fern having a stake"


# --- the shapes, each proved to reject something ----------------------------

def _mutate_simulation(update: str) -> rdflib.Graph:
    st = genesis_store(world="simulation")
    st.update("PREFIX ag: <http://example.org/orexis#>\n" + update)
    return _flatten(st, WORLDS_ROOT / "simulation")


def test_the_shipped_simulation_conforms():
    assert _conforms(_flatten(genesis_store(world="simulation"), WORLDS_ROOT / "simulation"))


def test_a_stand_in_that_is_on_no_bus_is_refused():
    """Without mqtt:onBus it gets no credential and no container, so it would never publish —
    and a sensor that is permanently silent reads exactly like hardware that is not there."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:onBus ?b }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:onBus ?b }} }}"""))


def test_an_initial_value_outside_the_range_is_refused():
    """It is a fraction of the observed property. 45 instead of 0.45 is the obvious slip, and
    it would clamp to 1.0 and look like a permanently soaking pot."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:initialValue 0.45 }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:initialValue 45.0 }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:initialValue 0.45 }} }}"""))


def test_a_tick_of_zero_seconds_is_refused():
    """A push device would spin its clock at zero and publish without pause."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:tickSeconds 3 }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:tickSeconds 0 }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:tickSeconds 3 }} }}"""))


# --- one board, several properties -------------------------------------------
#
# `world/sensing` has stated this shape for real hardware since #51: a KY-015 reports two
# properties down one line, one peripheral owns the connection, and its neighbour shares the
# wire without minting a principal. The simulation world was left behind by that change — it
# had three boards reporting one value each — so nothing ever put a multi-value message on a
# broker. These are about the simulated world catching up.

def test_a_stand_in_may_share_a_neighbours_wire_without_a_bus_of_its_own():
    """`<http://example.org/orexis/world/simulation#air_temp_fern>` states no mqtt:onBus, and the shipped world conforms.

    A second credential for a client that never connects is exactly what the hardware world
    refuses, and demanding one here would have forced the simulation to model something real
    boards do not do. Reachability is the test, not ownership: its neighbour publishes for it.
    """
    st = genesis_store(world="simulation")
    rows = bindings(st.query(f"""
        SELECT ?id WHERE {{ ?s <{AG}localId> ?id ; <{SIM}simulatedBy> ?m .
                            FILTER NOT EXISTS {{ ?s <http://example.org/orexis/mqtt#onBus> ?b }} }}"""))
    assert [r["id"] for r in rows] == ["air_temp_fern"], \
        "the world that this test is about no longer has a stand-in sharing a wire"


def test_a_stand_in_with_no_bus_and_no_publishing_peer_is_refused():
    """The rule the old one stated, kept: reachable, or permanently silent — and permanently
    silent reads exactly like hardware that is not there."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:onBus ?b }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:onBus ?b }} }}"""))


def test_an_initial_value_outside_a_models_own_range_is_refused():
    """45 where 0.45 was meant, in a model that says it runs 0..1 — the slip the old rule was
    written for. It is caught by the model's OWN range now, so it is caught in a thermometer
    too, where a rule that said `0..1` could not look."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:initialValue 21.0 }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:initialValue 210.0 }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?m sim:initialValue 21.0 }} }}"""))


def test_a_temperature_is_not_refused_for_not_being_a_fraction():
    """The assumption this had to stop making. 21.0 degrees is a legitimate initial value and
    the old shape refused it, because it held every model to 0..1."""
    st = genesis_store(world="simulation")
    rows = bindings(st.query(f"""
        SELECT ?initial WHERE {{ <http://example.org/orexis/world/simulation#air_temp_fern> <{SIM}simulatedBy> ?m .
                                 ?m <{SIM}initialValue> ?initial }}"""))
    assert rows, "air_temp_fern states no initial value; this test has lost its subject"
    assert float(rows[0]["initial"]) == 21.0


def test_a_second_sensor_on_an_existing_topic_mints_no_principal():
    """The payload grew; the channel did not. A stand-in that publishes nothing of its own is
    a value inside its neighbour's process, not a client — so it gets no credential, exactly as
    `<http://example.org/orexis/world/simulation#air_temp_fern>` gets none on the real board."""
    from onboarding import mqtt as mqtt_admin

    agents, devices = mqtt_admin.grants("simulation")
    assert "moisture_sensor_fern" in devices, "this test has lost its subject"
    assert "air_temp_fern" not in devices and "air_temp_fern" not in agents


def test_a_generated_stand_in_knows_what_a_litre_is_worth():
    """The dose join, held to matching. `_SIMULATED_Q` anchors ?litres on the term the domain
    denominates its valuation on — and when #120 moved that from water:hasTarget to
    water:litresPerFraction, the interpolated IRI here went on compiling and matching nothing:
    every generated SIM_VALUES lost its "litres", every dose moved nothing, and the first live
    run of the verification arc flagged the world for false knowledge. The detector worked;
    this makes the generator answerable too, because a stand-in that cannot drink is a world
    whose water is a lie."""
    import json

    from onboarding.compose import _SIMULATED_Q, _values
    from agent import ratified

    rows = ratified.rows(ratified.dataset("simulation"), _SIMULATED_Q)
    fern_rows = [r for r in rows if r["id"] == "moisture_sensor_fern"]
    assert fern_rows, "the query stopped matching the simulated world at all"
    values = json.loads(_values(fern_rows))
    moisture = next(v for v in values if v["pointer"] == "/moisture")
    assert moisture.get("litres") == 2.0, \
        "the litres join is dead — a dose will move nothing and every end will be UNMET"


# --- the world's clock, its weather, and its meddler ------------------------------------------


def test_a_generated_stand_in_runs_at_the_worlds_pace():
    """sim:timeScale rides into every stand-in's environment, and the physics arrive per
    simulated day — the per-tick drift is gone from the spec entirely."""
    import json

    from agent import ratified
    from onboarding.compose import _SIMULATED_Q, _values

    rows = ratified.rows(ratified.dataset("simulation"), _SIMULATED_Q)
    fern_rows = [r for r in rows if r["id"] == "moisture_sensor_fern"]
    assert fern_rows and fern_rows[0]["scale"] == "144"
    values = json.loads(_values(fern_rows))
    moisture = next(v for v in values if v["pointer"] == "/moisture")
    assert moisture.get("loses") == 0.12
    assert "drift" not in moisture
    temperature = next(v for v in values if v["pointer"] == "/temperature")
    assert temperature.get("swing") == 4.0


def test_the_pot_is_the_only_statement_of_its_own_drying():
    """#164 closed the other way round: water:driesPerDay on the PLANT is the physics, the
    closure entails the kernel term the generation reads, and the moisture models state no
    copy — one fact, one place. The join rides the denomination (the property water moves is
    the property that dries), so the thermometer on the same wire gains no drying."""
    import json

    from agent import ratified
    from agent.ontology import AG, WORLD_GRAPH
    from onboarding.compose import _SIMULATED_Q, _values

    ds = ratified.dataset("simulation")
    models = ratified.rows(ds, f"""SELECT ?m WHERE {{
        ?m a <{SIM}Model> . ?m <{SIM}losesPerDay> ?v }}""")
    assert not models, "a moisture model restating the pot's physics is the copy #164 retired"

    rows = ratified.rows(ds, _SIMULATED_Q)
    for sim_id, rate in (("moisture_sensor_fern", 0.12), ("moisture_sensor_tomato", 0.2),
                         ("moisture_sensor_succulent", 0.04)):
        own = [r for r in rows if r["id"] == sim_id]
        values = json.loads(_values(own))
        moisture = next(v for v in values if v["pointer"] in ("/moisture", "/value"))
        assert moisture.get("loses") == rate, f"{sim_id}: the pot's own physics must arrive"
        for v in values:
            if v is not moisture:
                assert "loses" not in v, "the loss rate leaked past the denomination join"


def test_a_model_stating_its_own_drying_overrides_the_pot():
    """The kernel term survives as an OVERRIDE: a model that states drying directly is a
    deliberate second opinion and wins over the subject's physics."""
    import json

    from agent import ratified
    from agent.ontology import AG, WORLD_GRAPH
    from onboarding.compose import _SIMULATED_Q, _values

    ds = ratified.dataset("simulation")
    ds.update(f"""INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?m <{SIM}losesPerDay> 0.5 }} }}
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
    ?s <{AG}localId> "moisture_sensor_fern" ; <{SIM}simulatedBy> ?m }} }}""")
    rows = [r for r in ratified.rows(ds, _SIMULATED_Q) if r["id"] == "moisture_sensor_fern"]
    values = json.loads(_values(rows))
    moisture = next(v for v in values if v["pointer"] == "/moisture")
    assert moisture.get("loses") == 0.5, "an explicit model figure is a deliberate override"


def test_the_meddler_is_its_own_service_with_its_own_credential():
    """A pot must not water itself: the rain comes from a separate container on a separate
    image, listed in compose only because the world states sim:strayDoseMeanDays."""
    from onboarding.compose import render

    compose = render("simulation")
    assert "sim-meddler:" in compose
    assert "orexis-meddler:local" in compose
    assert '"rain/fern"' in compose and '"rain/tomato"' in compose
    assert 'MEDDLER_MEAN_DAYS: "2"' in compose
    assert "mqtt-meddler.env" in compose


def test_the_meddler_may_write_rain_and_nothing_else():
    """The worst a compromised meddler can do is be over-generous with water."""
    from onboarding import mqtt as mqtt_admin

    _, devices = mqtt_admin.grants("simulation")
    meddler = devices["meddler"]
    assert all(access == "write" and topic.startswith("rain/")
               for access, topic in meddler.grants), meddler.grants
    assert len(meddler.grants) == 3  # one pot, one channel, no wildcards


def test_a_rained_on_subjects_sensor_may_hear_the_rain():
    from onboarding import mqtt as mqtt_admin

    _, devices = mqtt_admin.grants("simulation")
    assert ("read", "rain/fern") in devices["moisture_sensor_fern"].grants
    assert ("read", "rain/tomato") in devices["moisture_sensor_tomato"].grants


# --- who holds the clock: the device, and nobody else may claim to (#96, #103) -----------------


def test_a_sensing_element_claiming_its_own_clock_is_refused():
    """The disagreement made unrepresentable: air_temp_fern rides its board's wire and has no
    clock of its own to state. Before #96 it could claim Push while its board claimed Scheduled
    — one firmware deriving two contradictory capabilities — with no shape spanning them."""
    assert not _conforms(_mutate_simulation(f"""
        PREFIX sensing: <http://example.org/orexis/sensing#>
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
          <http://example.org/orexis/world/simulation#air_temp_fern> sensing:senseMode sensing:PushProcedure }} }} WHERE {{ }}"""))


def test_a_speaking_device_that_states_no_clock_is_refused():
    """Every capability its agents derive follows from the mode — a device without one leaves
    them silently capability-less, which is the composition-of-correct-silences #103 mapped."""
    assert not _conforms(_mutate_simulation(f"""
        PREFIX sensing: <http://example.org/orexis/sensing#>
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> sensing:senseMode ?m }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> sensing:senseMode ?m }} }}"""))


def test_a_scheduled_device_without_a_command_channel_is_refused():
    """The claim needs somewhere to be received: accepting an interval is meaningless without a
    channel to accept it on. The peripheral that used to escape this check cannot exist now —
    it cannot bear a mode at all — so the device is the whole of the question."""
    assert not _conforms(_mutate_simulation(f"""
        PREFIX mqtt: <http://example.org/orexis/mqtt#>
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:commandTopic ?c }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#moisture_sensor_fern> mqtt:commandTopic ?c }} }}"""))


def test_a_peripheral_inherits_its_boards_clock():
    """The join the whole move rests on: air_temp_fern states no mode and its agent still
    derives sensing:Subscribing, because the mode is found through the shared stream."""
    from orexis_capability_sensing.terms import SCHEDULED

    fern = load_wired(genesis_store(world="simulation").query, "fern")
    air = next(s for s in fern.sensors if s.local_id == "air_temp_fern")
    assert air.sense_mode == SCHEDULED



def test_the_barrel_stands_in_on_both_sides_of_the_wire():
    """Arcs 1 and 4 in one generation: the level stand-in DRAINS on every valve that draws
    from its barrel (drains -1.0, the class-entailed dose effect) and FILLS on the city's
    valve (litres 1.0, litres-per-stored-litre through the same denomination join a pot's
    conversion rides), its ceiling arrives ENTAILED from water:capacityL (the subject's one
    statement — restating 5.0 on the model would be the #164 copy), and neither topic join
    multiplies specs. The two conversions are two KEYS now: one signed number carried both
    while no subject was ever on both sides at once, and the barrel is."""
    import json

    from agent import ratified
    from onboarding.compose import _SIMULATED_Q, _values, _simulator

    rows = [r for r in ratified.rows(ratified.dataset("simulation"), _SIMULATED_Q)
            if r["id"] == "barrel1_level"]
    values = json.loads(_values(rows))
    assert len(values) == 1, "four valve topics must not become four values"
    level = values[0]
    assert level["drains"] == -1.0, "a dispensed litre lowers the source that gave it"
    assert level["litres"] == 1.0, "a bought litre raises it — conservation's mirror, entailed"
    assert level["max"] == 5.0, "the ceiling is water:capacityL, entailed — one statement"
    assert level["initial"] == 3.0 and level["min"] == 0.0

    service = _simulator("simulation", rows)
    assert service.count("actuators/valve_") == 3, "it hears every valve drawing from it"
    assert "actuators/city_valve/status" in service, "and the one that fills it"
    # The sides must not blur: the drain set carries the plant valves, the dose set the city's.
    import re
    drain_line = re.search(r'SIM_DRAIN_TOPIC: "([^"]*)"', service).group(1)
    dose_line = re.search(r'SIM_DOSE_TOPIC: "([^"]*)"', service).group(1)
    assert drain_line.count("valve_") == 3 and "city_valve" not in drain_line
    assert dose_line == "actuators/city_valve/status"
    assert 'SIM_SENSE_MODE: "push"' in service, "a level announces; it is not commanded"
