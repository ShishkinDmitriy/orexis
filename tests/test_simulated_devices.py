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

from conftest import WORLDS_ROOT, genesis_store
from test_shapes import _conforms, _flatten

AG = "http://example.org/agora#"

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
    perception:Subscribing — the same capability, running the same module, as a fern on a real board."""
    assert "Subscribing" in _caps("simulation")["fern"]


def test_no_agent_derives_a_simulated_perception():
    """There is no such capability any more, and nothing may quietly reintroduce one.

    A world that grew a `SimulatedSensing` back would be a second perception implementation,
    which is exactly the thing that let a broken real path go undetected.
    """
    for world in ("society", "sensing", "simulation"):
        for agent, caps in _caps(world).items():
            assert not any("Simulated" in c and "Sensing" in c for c in caps), \
                f"{world}/{agent} derived {caps}"


def test_the_simulated_world_derives_what_the_real_one_does():
    """Same wiring shape, same capabilities. If these ever diverge, the simulation has stopped
    standing in for anything."""
    assert _caps("simulation")["fern"] == _caps("society")["fern"]


# --- the shapes, each proved to reject something ----------------------------

def _mutate_simulation(update: str) -> rdflib.Graph:
    st = genesis_store(world="simulation")
    st.update("PREFIX ag: <http://example.org/agora#>\n" + update)
    return _flatten(st, WORLDS_ROOT / "simulation")


def test_the_shipped_simulation_conforms():
    assert _conforms(_flatten(genesis_store(world="simulation"), WORLDS_ROOT / "simulation"))


def test_a_stand_in_that_is_on_no_bus_is_refused():
    """Without mqtt:onBus it gets no credential and no container, so it would never publish —
    and a sensor that is permanently silent reads exactly like hardware that is not there."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:sensor_fern mqtt:onBus ?b }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:sensor_fern mqtt:onBus ?b }} }}"""))


def test_an_initial_value_outside_the_range_is_refused():
    """It is a fraction of the observed property. 45 instead of 0.45 is the obvious slip, and
    it would clamp to 1.0 and look like a permanently soaking pot."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelInitialValue 0.45 }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelInitialValue 45.0 }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelInitialValue 0.45 }} }}"""))


def test_a_tick_of_zero_seconds_is_refused():
    """A push device would spin its clock at zero and publish without pause."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelTickSeconds 3 }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelTickSeconds 0 }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelTickSeconds 3 }} }}"""))


# --- one board, several properties -------------------------------------------
#
# `world/sensing` has stated this shape for real hardware since #51: a KY-015 reports two
# properties down one line, one peripheral owns the connection, and its neighbour shares the
# wire without minting a principal. The simulation world was left behind by that change — it
# had three boards reporting one value each — so nothing ever put a multi-value message on a
# broker. These are about the simulated world catching up.

def test_a_stand_in_may_share_a_neighbours_wire_without_a_bus_of_its_own():
    """`ag:air_fern` states no mqtt:onBus, and the shipped world conforms.

    A second credential for a client that never connects is exactly what the hardware world
    refuses, and demanding one here would have forced the simulation to model something real
    boards do not do. Reachability is the test, not ownership: its neighbour publishes for it.
    """
    st = genesis_store(world="simulation")
    rows = bindings(st.query(f"""
        SELECT ?id WHERE {{ ?s <{AG}localId> ?id ; <{AG}simulatedBy> ?m .
                            FILTER NOT EXISTS {{ ?s <http://example.org/agora/mqtt#onBus> ?b }} }}"""))
    assert [r["id"] for r in rows] == ["air_fern"], \
        "the world that this test is about no longer has a stand-in sharing a wire"


def test_a_stand_in_with_no_bus_and_no_publishing_peer_is_refused():
    """The rule the old one stated, kept: reachable, or permanently silent — and permanently
    silent reads exactly like hardware that is not there."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:sensor_fern mqtt:onBus ?b }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:sensor_fern mqtt:onBus ?b }} }}"""))


def test_an_initial_value_outside_a_models_own_range_is_refused():
    """45 where 0.45 was meant, in a model that says it runs 0..1 — the slip the old rule was
    written for. It is caught by the model's OWN range now, so it is caught in a thermometer
    too, where a rule that said `0..1` could not look."""
    assert not _conforms(_mutate_simulation(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelInitialValue 21.0 }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelInitialValue 210.0 }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?m ag:modelInitialValue 21.0 }} }}"""))


def test_a_temperature_is_not_refused_for_not_being_a_fraction():
    """The assumption this had to stop making. 21.0 degrees is a legitimate initial value and
    the old shape refused it, because it held every model to 0..1."""
    st = genesis_store(world="simulation")
    rows = bindings(st.query(f"""
        SELECT ?initial WHERE {{ ag:air_fern <{AG}simulatedBy> ?m .
                                 ?m <{AG}modelInitialValue> ?initial }}"""))
    assert rows, "air_fern states no initial value; this test has lost its subject"
    assert float(rows[0]["initial"]) == 21.0


def test_a_second_sensor_on_an_existing_topic_mints_no_principal():
    """The payload grew; the channel did not. A stand-in that publishes nothing of its own is
    a value inside its neighbour's process, not a client — so it gets no credential, exactly as
    `ag:air_temp_fern` gets none on the real board."""
    from onboarding import mqtt as mqtt_admin

    agents, devices = mqtt_admin.grants("simulation")
    assert "sensor_fern" in devices, "this test has lost its subject"
    assert "air_fern" not in devices and "air_fern" not in agents
