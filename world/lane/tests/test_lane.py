"""The lane, played by its simulator: one van whose drives the world answers (#1002). The courier plans
the parcel's delivery, each drive is a command to the van itself, the simulator has the van on the cell
forty-five seconds on, the fix reports it, the courier's transition concludes the cell, and the step
lands — the whole loop on one fake broker, with the simulator reading the grid from the world.

Held to `world/lane/`: a world a van is driven through, not written into. A fictive drive would have
the courier write its own van's cell; here nothing moves the van but the command the world answers, and
a plan is walked only as far as the fix shows it (a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules,
navigation-is-a-body-a-mover-and-a-move §5).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.runtime import Runtime, boot
from agent.store import graphs_of, rows
from agent.transport.mqtt.driver import Mqtt
from simulation.simulator import Simulator

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
L = "http://example.org/orexis/world/lane#"
CADENCE_S = 10

#  WHERE EVERYTHING THE COURIER BELIEVES STANDS: every `courier:at` in its beliefs, by local name.
_AT_Q = "PREFIX courier: <http://example.org/orexis/courier#> SELECT ?s ?c WHERE { ?s courier:at ?c }"


class Bus:
    """One broker: what the simulator publishes reaches the courier, what the courier publishes reaches
    the simulator, and every command is kept."""

    def __init__(self):
        self.runtime = self.simulator = None
        self.commands: list[tuple[str, dict]] = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        if topic.startswith("sensors/"):
            self.runtime.deliver(topic, payload, clock.now())
        else:
            self.commands.append((topic, json.loads(payload)))
            self.simulator.command(topic, payload)


def _at(beliefs) -> dict[str, str]:
    return {r["s"].rsplit("#", 1)[-1]: r["c"].rsplit("#", 1)[-1]
            for r in rows(beliefs, _AT_Q, graphs_of(beliefs, "http://example.org/orexis#BeliefGraph"))}


def _lane(monkeypatch):
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(WORLD, bus, now=NOW)
    bus.runtime = Runtime(boot(WORLD, "courier_a"), "courier_a", transport=Mqtt(L + "courier_a", bus))
    return bus, time


def test_the_van_is_driven_by_command_and_lands_where_the_fix_shows_it(monkeypatch):
    """Six drives, a pick and a drop from the western road to the eastern end, each drive sent to the van
    as the number of the cell to reach, and each landing shown by the fix within the drive's band before
    the next is taken: the courier never writes its van's cell, the simulator moves it."""
    bus, time = _lane(monkeypatch)
    assert bus.simulator.open() == ["actuators/van_a/command"]
    assert bus.simulator.vans and bus.simulator.cells[19] == (6, 1), "the van and the grid read off the world"
    bus.simulator.step(NOW)                                             # the fix: the van on cell 1
    bus.runtime.run(passes=1, poll_s=0)
    assert _at(bus.runtime.beliefs) == {"van_a": "c0_1", "parcel_a": "c1_1"}, _at(bus.runtime.beliefs)
    assert len(bus.runtime.parts["execution"].executor.walking()) == 1, "a plan for the parcel is walked"
    assert [t for t, _ in bus.commands] == ["actuators/van_a/command"], "the first drive is sent to the van"
    assert bus.commands[0][1] == {"to": 4}, "to the parcel's cell, by its number"
    #  THE WORLD ANSWERS: ten seconds at a time, the fix reporting the van's cell, until the plan is walked.
    for _ in range(90):
        time["at"] += timedelta(seconds=CADENCE_S)
        bus.simulator.step(time["at"])
        bus.runtime.run(passes=1, poll_s=0)
        if not bus.runtime.parts["execution"].executor.walking():
            break
    assert bus.runtime.parts["execution"].executor.walking() == [], "the plan was walked to its end"
    assert _at(bus.runtime.beliefs) == {"van_a": "c6_1", "parcel_a": "c6_1"}, _at(bus.runtime.beliefs)
    told = [payload["to"] for _, payload in bus.commands]
    assert told[0] == 4 and told[-1] == 19 and len(told) == 6, f"six drives, east along the lane: {told}"
    assert all(abs(bus.simulator.cells[a][0] - bus.simulator.cells[b][0]) + abs(bus.simulator.cells[a][1] - bus.simulator.cells[b][1]) == 1
               for a, b in zip([1, *told], told)), "each a neighbour of the last"
    assert bus.simulator.sensors[L + "fix_a"]["value"] == 19.0, "the simulator's van is at the eastern end: nobody wrote it there"
    assert (time["at"] - NOW) <= timedelta(minutes=8), f"walked within eight minutes of the world's time: {time['at'] - NOW}"


def test_a_van_told_a_cell_that_is_no_neighbour_refuses_and_stays(monkeypatch, caplog):
    bus, time = _lane(monkeypatch)
    bus.simulator.open()
    bus.simulator.step(NOW)
    bus.simulator.command("actuators/van_a/command", b'{"to": 19}')
    assert "no neighbour" in caplog.text
    time["at"] += timedelta(seconds=60)
    bus.simulator.step(time["at"])
    assert bus.simulator.sensors[L + "fix_a"]["value"] == 1.0
