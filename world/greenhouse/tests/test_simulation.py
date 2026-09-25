"""The greenhouse played by its simulator: the bed dries, the grower notices, doses it through the
pump, and the simulator's next reading answers the step — the whole loop on one fake broker, with
the simulator reading the world's physics from the world."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.runtime import UNFINISHED, Runtime, boot
from agent.transport.mqtt.driver import Mqtt
from simulation.simulator import Simulator

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"


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

    bus.simulator.step(NOW)                                         # 0.40 and 21: comfortable
    assert bus.runtime.run(passes=1, poll_s=0) == UNFINISHED and bus.commands == []

    time["at"] = NOW + timedelta(days=3)                            # 0.28: below the floor of 0.30
    bus.simulator.step(time["at"])
    bus.runtime.run(passes=1, poll_s=0)
    assert [t for t, _ in bus.commands] == ["actuators/pump/command"]
    assert len(bus.runtime.executor.walking()) == 1

    time["at"] += timedelta(minutes=10)                             # the next reading: 0.53
    bus.simulator.step(time["at"])
    bus.runtime.run(passes=2, poll_s=0)
    assert bus.runtime.executor.walking() == [], "the simulator's reading answered the dose"
    assert len(bus.commands) == 1
