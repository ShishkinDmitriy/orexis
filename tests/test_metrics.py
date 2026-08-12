"""What an agent says about itself, and what it refuses to say.

The interesting cases are the absences. A sensor that has never delivered must not report an age,
because zero would be a claim that a reading had just arrived and seconds-since-boot would be a
claim about the wrong thing — the difference between "I do not know" and "the answer is nothing",
which is the distinction the whole design keeps making.

An agent's own silence is NOT one of those cases, and used to be. A missing interval meant an
agent reporting nothing, and that is gone: reporting is a mandatory capability now, so a missing
interval refuses at boot like any other missing belief. An agent permitted to be silent is one
that cannot be told from a dead one.
"""

from __future__ import annotations

import pytest
from agent.ontology import term

from agent.beliefs import BeliefError, Block
from packages.capability.reporting.beliefs import REPORTING_BLOCK, ReportingBeliefs
from packages.capability.reporting.terms import term as reporting_term
from agent.metrics import Metrics, tree_bytes

from conftest import build_agent


class _Sensor:
    def __init__(self, local_id):
        self.local_id = local_id


def test_a_sensor_that_never_delivered_reports_no_age(agent):
    """None, not zero. An agent that has never heard from its board has a different problem from
    one whose board went quiet, and a number for both would hide the first."""
    m = agent.metrics
    assert m.reading_age_s("moisture_sensor_fern") is None
    assert m.readings.get("moisture_sensor_fern", 0) == 0


def test_recording_a_reading_starts_the_clock(agent):
    m = agent.metrics
    m.reading_recorded(_Sensor("moisture_sensor_fern"))
    assert m.readings["moisture_sensor_fern"] == 1
    age = m.reading_age_s("moisture_sensor_fern")
    assert age is not None and age < 5


def test_the_swallowed_write_failures_are_counted(agent):
    """observation.py catches both and logs. Logging alone is what made a store that had quietly
    stopped accepting writes look exactly like one that was working."""
    m = agent.metrics
    assert m.agent_fields()["influx_write_failures"] == 0
    m.influx_failed()
    m.influx_failed()
    m.sensed_failed()
    assert m.agent_fields()["influx_write_failures"] == 2
    assert m.agent_fields()["sensed_write_failures"] == 1


def test_the_first_connect_is_not_a_reconnect(agent):
    m = Metrics(agent)
    assert m.agent_fields()["mqtt_reconnects"] == 0
    m.connected()
    assert m.agent_fields()["mqtt_connected"] == 1
    assert m.agent_fields()["mqtt_reconnects"] == 0
    m.disconnected()
    m.connected()
    assert m.agent_fields()["mqtt_reconnects"] == 1


def test_it_reports_the_world_version_it_is_running(agent):
    """Not the one on disk. A world can be re-ratified while agents keep running what they
    booted with, and nothing else at runtime shows the difference."""
    assert agent.metrics.agent_fields()["world_version"] == agent.world.version


def test_reporting_without_a_writer_is_silent(agent):
    """A test agent never called run(), so no module started — and report() must not reach for
    a network on the strength of being called.

    Asked of the MODULE now rather than of `Metrics`: counting stayed in the kernel and the sink
    moved to `capabilities/reporting/`, which is the split that makes reporting a capability at
    all. `Metrics` no longer has a `report()` to call.
    """
    reporting = next(m for m in agent.modules if m.name == "reporting")
    reporting.report()  # no writer, no raise, no I/O


def test_an_in_memory_store_has_no_size_on_disk():
    assert tree_bytes(None) is None
    assert tree_bytes("/nonexistent/belief/base") is None


# --- the belief, which is required ------------------------------------------------------------

def test_an_agent_that_states_no_interval_refuses(agent):
    """It used to report nothing and carry on. That was the defect, not the design.

    An agent permitted to fall silent is indistinguishable from a dead one, and #53 — a broker
    session lost for days with nothing saying so — is unfixable for exactly the agents that
    cannot speak for themselves. So a missing interval is now an ordinary missing belief and
    refuses at boot, the same way one of a bidder's would.
    """
    absent = Block(capability=REPORTING_BLOCK.capability,
                   cls=ReportingBeliefs,
                   terms={"interval_s": reporting_term("NoSuchTermAnyoneAuthored")})
    with pytest.raises(BeliefError):
        agent.beliefs.read(absent)


def test_a_stated_interval_is_read(agent):
    """Every world's agents state one, so this is the live path rather than a fixture."""
    held = agent.beliefs.read(REPORTING_BLOCK)
    assert held.interval_s > 0


def test_half_a_block_is_still_an_error(agent):
    """A partial answer was always an authoring slip, and still refuses."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class TwoFields:
        interval_s: int
        other: int

    partial = Block(capability=REPORTING_BLOCK.capability, cls=TwoFields,
                    terms={"interval_s": reporting_term("metricsIntervalS"),
                           "other": reporting_term("noSuchTerm")})
    with pytest.raises(BeliefError):
        agent.beliefs.read(partial)


@pytest.fixture
def agent(monkeypatch):
    return build_agent("fern", monkeypatch=monkeypatch)


def test_a_delivered_sensor_is_reported_even_when_not_wired(agent):
    """A simulated sensor is wired with ag:models, a sub-property of perception:polls that SPARQL does
    not follow — so `me.sensors` is empty for a simulated agent while it records readings every
    few seconds. Reporting only the wired set omitted every one of them."""
    agent.metrics.reading_recorded(_Sensor("sim_moisture_fern"))
    assert "sim_moisture_fern" in agent.metrics.sensors_seen()


def test_a_wired_sensor_is_reported_before_it_has_ever_delivered(agent):
    """The other half: zero readings is the signal that a board has never been heard from."""
    wired = {s.local_id for s in agent.me.sensors}
    assert wired <= agent.metrics.sensors_seen()
