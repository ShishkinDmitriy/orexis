"""The greenhouse played by its simulator: the bed dries, the grower notices, doses it through the
pump, and the simulator's next reading answers the step — the whole loop on one fake broker, with
the simulator reading the world's physics from the world."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.runtime import UNFINISHED, Runtime, boot
from agent.sensing.received import STUCK_AFTER
from agent.store import rows
from agent.transport.mqtt.driver import Mqtt
from simulation.simulator import Simulator

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"

#  EVERY SENSOR THE GROWER SAID STUCK OF ANY PERCEPT IT KEEPS — sensing's rule concludes it of the
#  percept arriving, in that percept's revision, of sensing's kind too (#944).
_STUCK_Q = """
SELECT DISTINCT ?sensor WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a sensing:ObservationGraph }
  GRAPH ?g { ?sensor sensing:stuckOn ?number } }"""


class Bus:
    """One broker: what the simulator publishes reaches the grower, what the grower publishes
    reaches the simulator, and every command is kept."""

    def __init__(self):
        self.runtime = self.simulator = None
        self.commands = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        if topic.startswith("sensors/"):
            self.runtime.deliver(topic, payload, clock.now())
        else:
            self.commands.append((topic, payload))
            self.simulator.command(topic, payload)


def test_a_bed_that_dries_below_its_floor_is_dosed_and_the_next_reading_answers(monkeypatch):
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(WORLD, bus, now=NOW)
    bus.runtime = Runtime(boot(WORLD, "grower"), "grower", transport=Mqtt(GH + "grower", bus))
    assert bus.simulator.open() == ["actuators/heater/command", "actuators/pump/command"]

    bus.simulator.step(NOW)                                         # 0.31 and 21: comfortable
    assert bus.simulator.due_in(NOW) == 600.0 and bus.simulator.due_in(NOW + timedelta(minutes=10)) == 0.0, \
        "the process sleeps until the next reading is due, in the world's time"
    assert bus.runtime.run(passes=1, poll_s=0) == UNFINISHED and bus.commands == []

    time["at"] = NOW + timedelta(days=1)                            # 0.27: below the floor of 0.30
    bus.simulator.step(time["at"])
    bus.runtime.run(passes=1, poll_s=0)
    assert [t for t, _ in bus.commands] == ["actuators/pump/command"]
    assert len(bus.runtime.parts["execution"].executor.walking()) == 1

    time["at"] += timedelta(minutes=10)                             # the next reading: 0.45, after 360 ml
    bus.simulator.step(time["at"])
    bus.runtime.run(passes=2, poll_s=0)
    assert bus.runtime.parts["execution"].executor.walking() == [], "the simulator's reading answered the dose"
    assert len(bus.commands) == 1


def test_the_bed_is_dosed_within_a_cadence_of_crossing_its_floor(monkeypatch):
    """The bed from where the world starts it, a reading at a time: the first reading below the floor
    is answered by a dose within a cadence, and not a day later. It was a day: each reading rewrote
    the forecast, a stretch the shorter forecast no longer had was forgotten without its revisions,
    and that orphan said `below` for the old horizon in every world the dose made — the search
    exhausted until the orphan's period ran out."""
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(WORLD, bus, now=NOW)
    bus.runtime = Runtime(boot(WORLD, "grower"), "grower", transport=Mqtt(GH + "grower", bus))
    bus.simulator.open()
    crossed = None
    for _ in range(40):                                             # a day, half an hour at a time
        published = bus.simulator.step(time["at"])
        reading = next((v for t, v in published if "moisture" in t), None)
        if crossed is None and reading is not None and reading < 0.30:
            crossed = time["at"]
        bus.runtime.run(passes=1, poll_s=0)
        if bus.commands:
            break
        time["at"] += timedelta(minutes=30)
    assert crossed is not None and [t for t, _ in bus.commands] == ["actuators/pump/command"]
    assert time["at"] - crossed <= timedelta(minutes=30), f"crossed at {crossed}, dosed at {time['at']}"


def test_no_sensor_of_a_quiet_bed_is_said_stuck(monkeypatch):
    """The bed from where the world starts it, a reading every ten minutes for longer than the grower's
    stuck limit, nobody heating the air: the grower says no sensor stuck. It said the thermometer
    stuck an hour in — the model read 21.0 at every cadence, exactly, and the simulator published it
    exactly — which is what a simulated instrument's jitter is for (#879). The probe was never at
    risk, since the bed dries by three counts a cadence."""
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(WORLD, bus, now=NOW)
    bus.runtime = Runtime(boot(WORLD, "grower"), "grower", transport=Mqtt(GH + "grower", bus))
    bus.simulator.open()
    air = []
    for _ in range(STUCK_AFTER + 2):
        air.extend(v for t, v in bus.simulator.step(time["at"]) if "thermometer" in t)
        bus.runtime.run(passes=1, poll_s=0)
        time["at"] += timedelta(minutes=10)
    stuck = [r["sensor"].rsplit("#", 1)[-1] for r in rows(bus.runtime.beliefs, _STUCK_Q, ())]
    assert stuck == [], f"a quiet instrument is not a stuck one, and the grower says {stuck} stuck"
    assert len(air) == STUCK_AFTER + 2 and len(set(air)) > 1, air
    assert bus.commands == [], "the bed stayed comfortable through the hour, so nothing was commanded"
