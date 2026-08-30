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
from orexis_agent_progression.ontology import term

from orexis_agent_deliberation.beliefs import BeliefError, Picks
from orexis_capability_reporting.beliefs import REPORTING_PICKS, ReportingBeliefs
from orexis_capability_reporting.terms import term as reporting_term
from agent.metrics import Metrics
from orexis_agent_progression.upkeep import tree_bytes
from conftest import sensing_of

from conftest import build_agent, wired_sensors


class _Sensor:
    def __init__(self, local_id):
        self.local_id = local_id


def test_a_sensor_that_never_delivered_reports_no_age(agent):
    """None, not zero. An agent that has never heard from its board has a different problem from
    one whose board went quiet, and a number for both would hide the first."""
    m = sensing_of(agent).observations   # the counters are sensing's (metrics-are-an-aspect)
    assert m.reading_age_s("moisture_sensor_fern") is None
    assert m.readings.get("moisture_sensor_fern", 0) == 0


def test_recording_a_reading_starts_the_clock(agent):
    m = sensing_of(agent).observations
    m.reading_recorded(_Sensor("moisture_sensor_fern"))
    assert m.readings["moisture_sensor_fern"] == 1
    age = m.reading_age_s("moisture_sensor_fern")
    assert age is not None and age < 5


def test_the_swallowed_write_failures_are_counted(agent):
    """observation.py catches both and logs. Logging alone is what made a store that had quietly
    stopped accepting writes look exactly like one that was working."""
    reporting, sensing = agent.module("reporting"), sensing_of(agent)
    assert reporting.reports()["influx_write_failures"] == 0
    assert sensing.reports()["sensed_write_failures"] == 0

    class Refusing:
        def write_reading(self, *a, **k):
            raise RuntimeError("store down")

    #  Each package counts its own refusals (metrics-are-an-aspect): the sink's are
    #  reporting's, the belief base's are sensing's.
    reporting._writer = Refusing()
    agent.tell("http://example.org/orexis/reporting#record", 0.5, None, sensor="x")
    agent.tell("http://example.org/orexis/reporting#record", 0.6, None, sensor="x")
    assert reporting.reports()["influx_write_failures"] == 2
    monkeypatch_write = sensing.observations.sensed.write
    sensing.observations.sensed.write = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("refused"))
    sensor = wired_sensors(agent)[0]
    sensing.observations.record(sensing.log, sensor, 0.3)
    sensing.observations.sensed.write = monkeypatch_write
    assert sensing.reports()["sensed_write_failures"] == 1


def test_the_first_connect_is_not_a_reconnect(monkeypatch):
    """The session's figures are the transport's own `reports()` — the kernel has no mailbox
    and counts no connection. The first connect is not a RE-connect."""
    from conftest import build_agent, genesis_store

    link = build_agent("fern", genesis_store(), monkeypatch).module("mqtt")
    assert link.reports() == {"link_connected": 1, "link_reconnects": 0}   # connected once
    link._on_disconnect(0)
    assert link.reports()["link_connected"] == 0
    link._on_connect()
    assert link.reports()["link_reconnects"] == 1


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


# --- the story beside the figures (#125) -------------------------------------------------------

def test_an_event_is_buffered_with_its_instant_and_drained_once(agent):
    """Counting is the kernel's, so the buffer is too: whoever the transition happens to tells
    this object, and the reporting capability drains it on its own tick."""
    m = agent.metrics
    m.event("adopted", "bid 0.4L to close my deficit", means="Acquiring", property="SoilMoisture")
    events = m.take_events()
    assert len(events) == 1
    at, kind, text, tags = events[0]
    assert kind == "adopted" and text == "bid 0.4L to close my deficit"
    assert tags == {"means": "Acquiring", "property": "SoilMoisture"}
    assert at is not None
    assert m.take_events() == []


def test_events_a_reporter_could_not_write_go_back_in_order(agent):
    """A figure missed is superseded by the next tick's; a transition missed is gone — so a
    failed write hands the drained events back, ahead of anything newer."""
    m = agent.metrics
    m.event("adopted", "one")
    m.event("satisfied", "two")
    taken = m.take_events()
    m.event("dropped", "three")
    m.requeue_events(taken)
    assert [text for _, _, text, _ in m.take_events()] == ["one", "two", "three"]


def test_the_reporter_writes_the_story_through_the_same_writer(agent):
    """Same tick, same token, same bucket — nothing new is granted for the events to land."""
    reporting = next(m for m in agent.modules if m.name == "reporting")
    written = []

    class _Writer:
        def write_agent_health(self, *a, **k): pass
        def write_events(self, agent_id, events): written.append((agent_id, events))

    reporting._writer = _Writer()
    agent.metrics.event("adopted", "why", action="Observing", property="SoilMoisture")
    reporting.report()
    assert len(written) == 1
    assert written[0][0] == agent.id
    assert [text for _, _, text, _ in written[0][1]] == ["why"]
    assert agent.metrics.take_events() == [], "written events must leave the buffer"


def test_a_failed_report_keeps_the_story_for_the_next_tick(agent):
    reporting = next(m for m in agent.modules if m.name == "reporting")

    class _Writer:
        def write_agent_health(self, *a, **k):
            raise RuntimeError("sink down")
        def write_events(self, *a, **k):
            raise AssertionError("must not be reached when health already failed")

    reporting._writer = _Writer()
    agent.metrics.event("adopted", "kept safe")
    reporting.report()  # must not raise — instrumentation never takes an agent down
    assert [text for _, _, text, _ in agent.metrics.take_events()] == ["kept safe"]


# --- the belief, which is required ------------------------------------------------------------

def test_an_agent_that_states_no_interval_refuses(agent):
    """It used to report nothing and carry on. That was the defect, not the design.

    An agent permitted to fall silent is indistinguishable from a dead one, and #53 — a broker
    session lost for days with nothing saying so — is unfixable for exactly the agents that
    cannot speak for themselves. So a missing interval is now an ordinary missing belief and
    refuses at boot, the same way one of a bidder's would.
    """
    absent = Picks(capability=REPORTING_PICKS.capability,
                   cls=ReportingBeliefs,
                   terms={"interval_s": reporting_term("NoSuchTermAnyoneAuthored")})
    with pytest.raises(BeliefError):
        agent.beliefs.read(absent)


def test_a_stated_interval_is_read(agent):
    """Every world's agents state one, so this is the live path rather than a fixture."""
    held = agent.beliefs.read(REPORTING_PICKS)
    assert held.interval_s > 0


def test_half_a_block_is_still_an_error(agent):
    """A partial answer was always an authoring slip, and still refuses."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class TwoFields:
        interval_s: int
        other: int

    partial = Picks(capability=REPORTING_PICKS.capability, cls=TwoFields,
                    terms={"interval_s": reporting_term("metricsIntervalS"),
                           "other": reporting_term("noSuchTerm")})
    with pytest.raises(BeliefError):
        agent.beliefs.read(partial)


@pytest.fixture
def agent(monkeypatch):
    return build_agent("fern", monkeypatch=monkeypatch)


def test_a_delivered_sensor_is_reported_even_when_not_wired(agent):
    """A simulated sensor is wired with ag:models, a sub-property of sensing:polls that SPARQL does
    not follow — so `me.sensors` is empty for a simulated agent while it records readings every
    few seconds. Reporting only the wired set omitted every one of them."""
    sensing_of(agent).observations.reading_recorded(_Sensor("sim_moisture_fern"))
    assert "sim_moisture_fern" in sensing_of(agent).observations.sensors_seen()


def test_a_wired_sensor_is_reported_before_it_has_ever_delivered(agent):
    """The other half: zero readings is the signal that a board has never been heard from."""
    wired = {s.local_id for s in wired_sensors(agent)}
    assert wired <= sensing_of(agent).observations.sensors_seen()
