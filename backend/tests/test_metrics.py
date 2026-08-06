"""What an agent says about itself, and what it refuses to say.

The interesting cases are the absences. A sensor that has never delivered must not report an age,
because zero would be a claim that a reading had just arrived and seconds-since-boot would be a
claim about the wrong thing. An agent that states no interval must not report at all. Both are
the difference between "I do not know" and "the answer is nothing", which is the distinction the
whole design keeps making.
"""

from __future__ import annotations

import pytest

from agora.beliefs import BeliefError, Block
from agora.metrics import SELF_REPORTING_BLOCK, Metrics, SelfReportingBeliefs, _tree_bytes

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
    """A test agent never called run(), so nothing was started — and report() must not reach for
    a network on the strength of being called."""
    agent.metrics.report()  # no writer, no raise, no I/O


def test_an_in_memory_store_has_no_size_on_disk():
    assert _tree_bytes(None) is None
    assert _tree_bytes("/nonexistent/belief/base") is None


# --- the belief, whose absence is a decision -------------------------------------------------

def test_an_agent_that_states_no_interval_reports_nothing(agent):
    """`read_optional` returns None for a wholly absent block, and run() then starts nothing.
    Refusing to boot over instrumentation would be disproportionate."""
    absent = Block(capability=SELF_REPORTING_BLOCK.capability,
                   cls=SelfReportingBeliefs,
                   terms={"interval_s": "noSuchTermAnyoneAuthored"})
    assert agent.beliefs.read_optional(absent) is None


def test_a_stated_interval_is_read(agent):
    """Every world's agents now state one, so this is the live path rather than a fixture."""
    held = agent.beliefs.read_optional(SELF_REPORTING_BLOCK)
    assert held is not None and held.interval_s > 0


def test_half_a_block_is_still_an_error(agent):
    """Absence is a decision; a partial answer is an authoring slip, and must still refuse."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class TwoFields:
        interval_s: int
        other: int

    partial = Block(capability=SELF_REPORTING_BLOCK.capability, cls=TwoFields,
                    terms={"interval_s": "metricsIntervalS", "other": "noSuchTerm"})
    with pytest.raises(BeliefError):
        agent.beliefs.read_optional(partial)


@pytest.fixture
def agent(monkeypatch):
    return build_agent("fern", monkeypatch=monkeypatch)


def test_a_delivered_sensor_is_reported_even_when_not_wired(agent):
    """A simulated sensor is wired with ag:models, a sub-property of ag:polls that SPARQL does
    not follow — so `me.sensors` is empty for a simulated agent while it records readings every
    few seconds. Reporting only the wired set omitted every one of them."""
    agent.metrics.reading_recorded(_Sensor("sim_moisture_fern"))
    assert "sim_moisture_fern" in agent.metrics.sensors_seen()


def test_a_wired_sensor_is_reported_before_it_has_ever_delivered(agent):
    """The other half: zero readings is the signal that a board has never been heard from."""
    wired = {s.local_id for s in agent.me.sensors}
    assert wired <= agent.metrics.sensors_seen()
