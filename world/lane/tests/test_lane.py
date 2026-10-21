"""The lane, played by its simulator: two couriers on the road, a van each, whose drives the world answers
(#1002, #1004). A courier plans its parcel's delivery, each drive is a command to its van, the simulator has
the van on the cell forty-five seconds on, the fix reports it, the courier's transitions conclude the cell,
and the step lands — the whole loop on one fake broker both agents and the simulator share, with the
simulator reading the road's hedges off the domain the world imports. Each courier sees the other through a
contact within two cells (#1003), and holds the courier's constraints, so neither plans onto the other's position.

Held to `world/lane/`: two minds on one road, each optimizing alone and meeting by what it senses; the one
mind with a van parked in its way is `world/layby/`, on the same road
(a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules, navigation-is-a-body-a-mover-and-a-move §5).
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

#  WHERE EVERYTHING THE COURIER BELIEVES STANDS: every thing with two coordinates in its beliefs, by local name,
#  save where a parcel is owed, which is authored and never moves.
_AT_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?s ?x ?y WHERE { ?s courier:x ?x ; courier:y ?y . FILTER(isIRI(?s)) FILTER NOT EXISTS { ?p courier:destination ?s } }"""
ROAD = "http://example.org/orexis/road#"
#  THE HEDGES EITHER SIDE OF THE LANE, which a radar slot sees as it passes and nothing types: the road's own.
HEDGES = {(2, 0), (3, 0), (4, 0), (2, 2), (4, 2)}


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


def _at(beliefs) -> dict[str, tuple[int, int]]:
    return {r["s"].rsplit("#", 1)[-1]: (int(r["x"]), int(r["y"]))
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


def test_two_couriers_each_drive_their_own_van_and_see_the_other_within_two_cells(monkeypatch):
    """A drives six cells east along the lane to its parcel's destination while B, with nothing to deliver,
    stands on the eastern road: each courier reads its own fix, commands its own van, and believes the other's
    van only while its receiver has it within two cells."""
    bus, time = _lane(monkeypatch)
    assert bus.simulator.open() == ["actuators/van_a/command", "actuators/van_b/command"]
    assert len(bus.simulator.vans) == 2 and bus.simulator.position(ROAD + "hedge_2_0") == (2, 0), \
        "the vans read off the world, the road's hedges off the domain it imports"
    bus.simulator.step(NOW)                                             # the fixes: van A at (0, 1), van B at (6, 0)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    a, b = _at(bus.runtime.beliefs), _at(bus.runtimes["courier_b"].beliefs)
    assert a["van_a"] == (0, 1) and a["parcel_a"] == (1, 1) and "van_b" not in a and "parcel_b" not in a, \
        f"van B, six cells off, is believed nowhere; parcel B is B's own: {a}"
    assert a["contact_1"] == (2, 0), f"the hedge two cells on is seen, and nothing knows it is a hedge: {a}"
    assert b["van_b"] == (6, 0) and b["parcel_b"] == (6, 0) and "van_a" not in b, f"and B, with nothing to deliver, knows nothing of A yet: {b}"
    assert bus.runtimes["courier_b"].parts["execution"].executor.walking() == [], "B wants nothing: its parcel is where it is owed"
    assert len(bus.runtime.parts["execution"].executor.walking()) == 1, "a plan for the parcel is walked"
    assert [t for t, _ in bus.commands] == ["actuators/van_a/command"], "the first drive is sent to the van"
    assert bus.commands[0][1] == {"to": {"x": 1, "y": 1}}, "to the parcel's cell, by its coordinates"
    #  THE WORLD ANSWERS: ten seconds at a time, the fix reporting the van's cell, until the plan is walked.
    seen = _walk(bus, time, 90)
    assert bus.runtime.parts["execution"].executor.walking() == [], "the plan was walked to its end"
    at = _at(bus.runtime.beliefs)
    assert (at["van_a"], at["parcel_a"], at["van_b"]) == ((6, 1), (6, 1), (6, 0)), at
    #  THE CONTACT (#1003): van B at (6, 0) is believed nowhere until van A comes within the receiver's range of
    #  it, two cells either way, and at its coordinates from then on; the radar slot, with B identified by the
    #  receiver, sees the hedges beside the lane as the van passes them, and nothing else.
    first = next(i for i, at in enumerate(seen) if "van_b" in at)
    assert all("van_b" not in at for at in seen[:first]) and seen[first]["van_a"] == (4, 1), seen[first]
    assert all(at["van_b"] == (6, 0) for at in seen[first:]), "once seen, where it is"
    assert {at.get("contact_1") for at in seen} <= {None, *HEDGES} and any(at.get("contact_1") in HEDGES for at in seen), \
        "the radar saw the hedges beside the lane and nothing else"
    #  THE OTHER MIND (#1004): B saw A only within two cells of (6, 0), from (5, 1) on, and holds it at its cell.
    b = _at(bus.runtimes["courier_b"].beliefs)
    assert (b["van_b"], b["parcel_b"], b["van_a"]) == ((6, 0), (6, 0), (6, 1)), b
    assert bus.commands and all(t == "actuators/van_a/command" for t, _ in bus.commands), "B commanded nothing"
    told = [(payload["to"]["x"], payload["to"]["y"]) for _, payload in bus.commands]
    assert told[0] == (1, 1) and told[-1] == (6, 1) and len(told) == 6, f"six drives, east along the lane: {told}"
    assert not set(told) & HEDGES, f"no hedge was driven: {told}"
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip([(0, 1), *told], told)), "each a neighbour of the last"
    assert bus.simulator.position(L + "van_a") == (6, 1), "the simulator's van is at the eastern end: nobody wrote it there"
    assert (time["at"] - NOW) <= timedelta(minutes=8), f"walked within eight minutes of the world's time: {time['at'] - NOW}"


#  Van A from the north-western corner with its parcel at the southern end of the western road.
_FROM_THE_CORNER = {"world.ttl": [("sim:initialValue 1 ; sim:jitter 0 ] ;    # van A row 1", "sim:initialValue 0 ; sim:jitter 0 ] ;    # van A row 0")],
                    "beliefs/courier_a.state.ttl": [(":parcel_a courier:x 1 ; courier:y 1 .", ":parcel_a courier:x 0 ; courier:y 2 .")]}


#  A PEER STANDING ON THE WAY (#922, #1004): van B, its courier idle, stands at (0, 1) with its parcel where it
#  is owed, and van A starts at (0, 0) with its parcel at (0, 2). A's receiver sees B one cell off from the
#  start, and the constraint that no two vans stand at one position keeps every plan of A's off B's, whatever
#  was or was not said: a way round, two drives longer, is the one taken. B, for its part, sees A the whole while it
#  is within two cells and loses it down the lane.
_PEER_ON_THE_WAY = {**_FROM_THE_CORNER,
                    "world.ttl": [*_FROM_THE_CORNER["world.ttl"],
                                  ("sim:initialValue 6 ; sim:jitter 0 ] ;    # van B column 6", "sim:initialValue 0 ; sim:jitter 0 ] ;    # van B column 0"),
                                  ("sim:initialValue 0 ; sim:jitter 0 ] ;    # van B row 0", "sim:initialValue 1 ; sim:jitter 0 ] ;    # van B row 1")],
                    "beliefs/courier_b.state.ttl": [(":parcel_b courier:x 6 ; courier:y 0 .", ":parcel_b courier:x 0 ; courier:y 1 ."),
                                                    (":east_road courier:x 6 ; courier:y 0 ;", ":east_road courier:x 0 ; courier:y 1 ;")]}


def test_a_peer_seen_standing_on_a_cell_keeps_the_plan_out_of_it(monkeypatch, tmp_path):
    bus, time = _lane(monkeypatch, variant(tmp_path, "peer_on_the_way", _PEER_ON_THE_WAY))
    bus.simulator.open()
    bus.simulator.step(NOW)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    a, b = _at(bus.runtime.beliefs), _at(bus.runtimes["courier_b"].beliefs)
    assert (a["van_a"], a["parcel_a"], a["van_b"]) == ((0, 0), (0, 2), (0, 1)), f"A sees B one cell off: {a}"
    assert (b["van_b"], b["parcel_b"], b["van_a"]) == ((0, 1), (0, 1), (0, 0)), f"and B sees A: {b}"
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
    assert _at(bus.runtime.beliefs)["parcel_a"] == (6, 1)
    told = [(payload["to"]["x"], payload["to"]["y"]) for t, payload in bus.commands if t == "actuators/van_a/command"]
    assert (0, 1) not in told, f"B's cell was driven: {told}"
    #  ROUND B, four drives to the parcel where two would do through B's cell — down column 1 or down column -1,
    #  the grid being infinite and the two ways tying.
    assert told[3] == (0, 2) and told[:3] in ([(1, 0), (1, 1), (1, 2)], [(-1, 0), (-1, 1), (-1, 2)]), f"round B to the parcel: {told}"
    assert all(t == "actuators/van_a/command" for t, _ in bus.commands), "B, with nothing to deliver, commanded nothing"
    assert seen_by_b[0] is not None and seen_by_b[-1] is None, "B saw A near and lost it down the lane"
