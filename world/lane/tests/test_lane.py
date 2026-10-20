"""The lane, played by its simulator: two couriers, a van each, whose drives the world answers (#1002,
#1004). A courier plans its parcel's delivery, each drive is a command to its van, the simulator has the van
on the cell forty-five seconds on, the fix reports it, the courier's transitions conclude the cell, and the
step lands — the whole loop on one fake broker both agents and the simulator share, with the simulator
reading the grid from the world. Each courier sees the other through a contact within two cells (#1003).

Held to `world/lane/`: a world a van is driven through, not written into. A fictive drive would have
the courier write its own van's cell; here nothing moves the van but the command the world answers, and
a plan is walked only as far as the fix shows it (a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules,
navigation-is-a-body-a-mover-and-a-move §5).
"""

from __future__ import annotations

import json
import shutil
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
    """One broker: what the simulator publishes reaches every courier, what a courier publishes reaches the
    simulator, and every command is kept."""

    def __init__(self):
        self.runtimes: dict[str, Runtime] = {}
        self.simulator = None
        self.commands: list[tuple[str, dict]] = []

    @property
    def runtime(self) -> Runtime:
        return self.runtimes["courier_a"]

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        if topic.startswith("sensors/"):
            for runtime in self.runtimes.values():
                runtime.deliver(topic, payload, clock.now())
        else:
            self.commands.append((topic, json.loads(payload)))
            self.simulator.command(topic, payload)


def _at(beliefs) -> dict[str, str]:
    return {r["s"].rsplit("#", 1)[-1]: r["c"].rsplit("#", 1)[-1]
            for r in rows(beliefs, _AT_Q, graphs_of(beliefs, "http://example.org/orexis#BeliefGraph"))}


def _lane(monkeypatch, world: Path = WORLD):
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(world, bus, now=NOW)
    for name in ("courier_a", "courier_b"):
        bus.runtimes[name] = Runtime(boot(world, name), name, transport=Mqtt(L + name, bus))
    return bus, time


def variant(tmp_path: Path, name: str, edits: dict) -> Path:
    """The lane with its documents rewritten — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / name / "world" / "lane"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / name / "domains").symlink_to(WORLD.parents[1] / "domains")
    for file, pairs in edits.items():
        text = (world / file).read_text()
        for old, new in pairs:
            assert old in text, f"{file} no longer says {old!r}"
            text = text.replace(old, new)
        (world / file).write_text(text)
    return world


def _walk(bus, time, limit: int, of: str = "courier_a") -> list[dict[str, str]]:
    """Ten seconds at a time, the simulator reporting and both couriers planning and walking, until nothing
    of `of`'s is walking: what `of` believed stands where, after each step."""
    seen = []
    for _ in range(limit):
        time["at"] += timedelta(seconds=CADENCE_S)
        bus.simulator.step(time["at"])
        for runtime in bus.runtimes.values():
            runtime.run(passes=1, poll_s=0)
        seen.append(_at(bus.runtimes[of].beliefs))
        if not bus.runtimes[of].parts["execution"].executor.walking():
            break
    return seen


def test_the_van_is_driven_by_command_and_lands_where_the_fix_shows_it(monkeypatch):
    """Six drives, a pick and a drop from the western road to the eastern end, each drive sent to the van
    as the coordinates of the cell to reach, and each landing shown by the fix within the drive's band
    before the next is taken: the courier never writes its van's cell, the simulator moves it."""
    bus, time = _lane(monkeypatch)
    assert bus.simulator.open() == ["actuators/van_a/command", "actuators/van_b/command"]
    assert len(bus.simulator.vans) == 2 and (6, 1) in bus.simulator.cells, "the vans and the grid read off the world"
    bus.simulator.step(NOW)                                             # the fixes: van A at (0, 1), van B at (6, 0)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    assert _at(bus.runtime.beliefs) == {"van_a": "c0_1", "parcel_a": "c1_1"}, "van B, six cells off, is believed nowhere; parcel B is B's own"
    assert _at(bus.runtimes["courier_b"].beliefs) == {"van_b": "c6_0", "parcel_b": "c6_0"}, "and B, with nothing to deliver, knows nothing of A yet"
    assert bus.runtimes["courier_b"].parts["execution"].executor.walking() == [], "B wants nothing: its parcel is where it is owed"
    assert len(bus.runtime.parts["execution"].executor.walking()) == 1, "a plan for the parcel is walked"
    assert [t for t, _ in bus.commands] == ["actuators/van_a/command"], "the first drive is sent to the van"
    assert bus.commands[0][1] == {"to": {"x": 1, "y": 1}}, "to the parcel's cell, by its coordinates"
    #  THE WORLD ANSWERS: ten seconds at a time, the fix reporting the van's cell, until the plan is walked.
    seen = _walk(bus, time, 90)
    assert bus.runtime.parts["execution"].executor.walking() == [], "the plan was walked to its end"
    assert _at(bus.runtime.beliefs) == {"van_a": "c6_1", "parcel_a": "c6_1", "van_b": "c6_0"}, _at(bus.runtime.beliefs)
    #  THE CONTACT (#1003): van B, parked at (6, 0), is believed nowhere until van A comes within two cells of it
    #  and at its cell from then on; the radar slot, with nothing unidentified in range, is believed nowhere.
    first = next(i for i, at in enumerate(seen) if "van_b" in at)
    assert all("van_b" not in at for at in seen[:first]) and seen[first - 1]["van_a"] in ("c4_1", "c5_1"), seen[first - 1]
    assert all(at["van_b"] == "c6_0" for at in seen[first:]), "once seen, where it is"
    assert all("contact_1" not in at for at in seen), "nothing unidentified was in range"
    #  THE OTHER MIND (#1004): B saw A only within two cells of (6, 0), from (5, 1) on, and holds it at its cell.
    b = _at(bus.runtimes["courier_b"].beliefs)
    assert b == {"van_b": "c6_0", "parcel_b": "c6_0", "van_a": "c6_1"}, b
    assert bus.commands and all(t == "actuators/van_a/command" for t, _ in bus.commands), "B commanded nothing"
    told = [(payload["to"]["x"], payload["to"]["y"]) for _, payload in bus.commands]
    assert told[0] == (1, 1) and told[-1] == (6, 1) and len(told) == 6, f"six drives, east along the lane: {told}"
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip([(0, 1), *told], told)), "each a neighbour of the last"
    assert bus.simulator.position(L + "van_a") == (6, 1), "the simulator's van is at the eastern end: nobody wrote it there"
    assert (time["at"] - NOW) <= timedelta(minutes=8), f"walked within eight minutes of the world's time: {time['at'] - NOW}"


def test_a_van_told_a_cell_that_is_no_neighbour_refuses_and_stays(monkeypatch, caplog):
    bus, time = _lane(monkeypatch)
    bus.simulator.open()
    bus.simulator.step(NOW)
    bus.simulator.command("actuators/van_a/command", b'{"to": {"x": 6, "y": 1}}')
    assert "no neighbour" in caplog.text
    time["at"] += timedelta(seconds=60)
    bus.simulator.step(time["at"])
    assert bus.simulator.position(L + "van_a") == (0, 1)


#  A TREE ACROSS THE ROAD (#1003): van A starts at (0, 0) with its parcel at (0, 2), and a thing nothing
#  identifies lies on the direct way at (0, 1), one cell off, within the radar's two. The slot's vector lands on
#  that cell, the slot is believed there, and the constraint keeps every plan off it: the way round through
#  column 1 is two drives longer, and is the one taken.
_FROM_THE_CORNER = {"world.ttl": [("sim:initialValue 1 ; sim:jitter 0 ] ;    # van A row 1", "sim:initialValue 0 ; sim:jitter 0 ] ;    # van A row 0")],
                    "beliefs/courier_a.state.ttl": [(":parcel_a courier:at :c1_1 .", ":parcel_a courier:at :c0_2 .")]}
DETOUR = {**_FROM_THE_CORNER,
          "world.ttl": [*_FROM_THE_CORNER["world.ttl"],
                        (":driver_b a courier:Driver ;",
                         ':tree sim:simulatedBy [ a sim:Model ; sim:x 0 ; sim:y 1 ] ; rdfs:label "a fallen tree, which only the radar knows" .\n'
                         ":driver_b a courier:Driver ;")],
          "society.ttl": [(":van_a , :van_b ;", ":van_a , :van_b , :tree ;")]}


def test_a_thing_the_radar_sees_is_an_obstacle_and_the_plan_goes_round_it(monkeypatch, tmp_path):
    bus, time = _lane(monkeypatch, variant(tmp_path, "detour", DETOUR))
    bus.simulator.open()
    bus.simulator.step(NOW)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    at = _at(bus.runtime.beliefs)
    assert at["van_a"] == "c0_0" and at["contact_1"] == "c0_1" and "van_b" not in at, at
    seen = _walk(bus, time, 120)
    assert bus.runtime.parts["execution"].executor.walking() == [], "the plan was walked to its end"
    assert _at(bus.runtime.beliefs)["parcel_a"] == "c6_1", _at(bus.runtime.beliefs)
    told = [(payload["to"]["x"], payload["to"]["y"]) for _, payload in bus.commands]
    assert (0, 1) not in told, f"the obstacle's cell was driven: {told}"
    assert told[:4] == [(1, 0), (1, 1), (1, 2), (0, 2)], f"round through column 1 to the parcel: {told}"
    assert all("contact_1" not in at or at["contact_1"] == "c0_1" for at in seen), "the tree stays where it is while seen"
    assert "contact_1" not in seen[-1], "and is believed nowhere once two cells behind"


#  A PEER STANDING ON THE WAY (#922, #1004): van B, its courier idle, stands at (0, 1) with its parcel where it
#  is owed, and van A starts at (0, 0) with its parcel at (0, 2). A's receiver sees B one cell off from the
#  start, and the constraint that no cell holds two vans keeps every plan of A's off B's cell, whatever was or
#  was not said: the way round through column 1 is the one taken. B, for its part, sees A the whole while it
#  is within two cells and loses it down the lane.
_PEER_ON_THE_WAY = {**_FROM_THE_CORNER,
                    "world.ttl": [*_FROM_THE_CORNER["world.ttl"],
                                  ("sim:initialValue 6 ; sim:jitter 0 ] ;    # van B column 6", "sim:initialValue 0 ; sim:jitter 0 ] ;    # van B column 0"),
                                  ("sim:initialValue 0 ; sim:jitter 0 ] ;    # van B row 0", "sim:initialValue 1 ; sim:jitter 0 ] ;    # van B row 1")],
                    "beliefs/courier_b.state.ttl": [("courier:destination :c6_0", "courier:destination :c0_1"),
                                                    (":parcel_b courier:at :c6_0 .", ":parcel_b courier:at :c0_1 .")]}


def test_a_peer_seen_standing_on_a_cell_keeps_the_plan_out_of_it(monkeypatch, tmp_path):
    bus, time = _lane(monkeypatch, variant(tmp_path, "peer_on_the_way", _PEER_ON_THE_WAY))
    bus.simulator.open()
    bus.simulator.step(NOW)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    assert _at(bus.runtime.beliefs) == {"van_a": "c0_0", "parcel_a": "c0_2", "van_b": "c0_1"}, "A sees B one cell off"
    assert _at(bus.runtimes["courier_b"].beliefs) == {"van_b": "c0_1", "parcel_b": "c0_1", "van_a": "c0_0"}, "and B sees A"
    seen_by_b = []
    for _ in range(120):
        time["at"] += timedelta(seconds=CADENCE_S)
        bus.simulator.step(time["at"])
        for runtime in bus.runtimes.values():
            runtime.run(passes=1, poll_s=0)
        seen_by_b.append(_at(bus.runtimes["courier_b"].beliefs).get("van_a"))
        if not bus.runtime.parts["execution"].executor.walking():
            break
    assert bus.runtime.parts["execution"].executor.walking() == [], "A's plan was walked to its end"
    assert _at(bus.runtime.beliefs)["parcel_a"] == "c6_1"
    told = [(payload["to"]["x"], payload["to"]["y"]) for t, payload in bus.commands if t == "actuators/van_a/command"]
    assert (0, 1) not in told, f"B's cell was driven: {told}"
    assert told[:4] == [(1, 0), (1, 1), (1, 2), (0, 2)], f"round through column 1 to the parcel: {told}"
    assert all(t == "actuators/van_a/command" for t, _ in bus.commands), "B, with nothing to deliver, commanded nothing"
    assert seen_by_b[0] is not None and seen_by_b[-1] is None, "B saw A near and lost it down the lane"
