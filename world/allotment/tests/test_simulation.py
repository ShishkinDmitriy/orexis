"""The allotment played by its simulator: the rose's plot dries below its floor, its grower buys
water on the supplier's venue, the supplier serves the claim through the valve over the plot, and
the simulator's next reading answers the grower — three agents and the simulator on one fake broker,
the physics read from the world."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.runtime import Runtime, boot
from agent.transport.mqtt.driver import Mqtt, matches
from simulation.simulator import Simulator

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AL = "http://example.org/orexis/world/allotment#"


class Bus:
    """One broker: a publish reaches every agent subscribed to a matching pattern, and a command to
    a valve reaches the simulator and is kept."""

    def __init__(self):
        self.subscribers, self.simulator, self.commands = [], None, []

    def client(self, runtime_of):
        bus = self

        class Client:
            def __init__(self):
                self.patterns = []
                bus.subscribers.append((self, runtime_of))

            def subscribe(self, pattern):
                self.patterns.append(pattern)

            def publish(self, topic, payload, retain=False):
                bus.publish(topic, payload, retain)

        return Client()

    def subscribe(self, pattern):
        pass                                    # the simulator's own client: it hears commands directly

    def publish(self, topic, payload, retain=False):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        if topic.startswith("actuators/"):
            self.commands.append(topic)
            self.simulator.command(topic, payload)
            return
        for client, runtime_of in self.subscribers:
            if any(matches(p, topic) for p in client.patterns):
                runtime_of().deliver(topic, payload, clock.now())


def test_a_plot_that_dries_below_its_floor_is_watered_with_bought_water(monkeypatch):
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(WORLD, bus, now=NOW)
    agents = {}
    for name in ("supplier", "rose_grower", "fern_grower"):
        client = bus.client(lambda name=name: agents[name])
        agents[name] = Runtime(boot(WORLD, name), name, transport=Mqtt(AL + name, client))
    assert bus.simulator.open() == ["actuators/fern_valve/command", "actuators/rose_valve/command"]

    def run(times=3):
        for _ in range(times):
            for runtime in agents.values():
                runtime.run(passes=1, poll_s=0)

    time["at"] = NOW + timedelta(days=3)          # the rose at 0.25, below its floor; the fern at 0.31
    bus.simulator.step(time["at"])
    run()
    assert bus.commands == [], "a round is open, and nothing is served before it clears"
    time["at"] += timedelta(seconds=31)
    run()
    assert bus.commands == ["actuators/rose_valve/command"], "the rose bought the lot and it was served"
    time["at"] += timedelta(minutes=10)
    bus.simulator.step(time["at"])
    run()
    assert agents["rose_grower"].executor.walking() == [], "the simulator's reading answered the presentation"
    assert bus.commands == ["actuators/rose_valve/command"]
