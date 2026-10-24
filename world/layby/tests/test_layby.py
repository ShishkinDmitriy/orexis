"""The layby, played by its simulator: one courier on the road, whose drives the world answers, and a van
parked on it by a driver nobody plays (#1002, #1003). The courier plans its parcel's delivery, each drive is a
command to its van, the simulator has the van on the cell forty-five seconds on, the fix reports it, the
courier's transitions conclude the cell, and the step lands — the whole loop on one fake broker the agent and
the simulator share, with the simulator reading the road's hedges off the domain the world imports. The parked
van and whatever else comes within two cells are seen through the contacts the courier's van carries.

Held to `world/layby/`: a world a van is driven through, not written into. A fictive drive would have
the courier write its own van's cell; here nothing moves the van but the command the world answers, and
a plan is walked only as far as the fix shows it (a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules,
navigation-is-a-body-a-mover-and-a-move §5). The same road with two couriers on it is `world/lane/`.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.runtime import Runtime, boot
from agent.store import graphs_of, rows
from agent.transport.mqtt.driver import Mqtt
from simulation.simulator import Simulator

#  EVERY TEST HERE WALKS THE LAYBY'S AGENT through the world's time: run where CI runs, never in the local gate.
pytestmark = pytest.mark.walk

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
L = "http://example.org/orexis/world/layby#"
CADENCE_S = 10

#  WHERE EVERYTHING THE COURIER BELIEVES STANDS: every thing with two coordinates in its beliefs, by local name,
#  save where a parcel is owed, which is authored and never moves.
_AT_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?s ?x ?y WHERE { ?s courier:x ?x ; courier:y ?y . FILTER(isIRI(?s)) FILTER NOT EXISTS { ?p courier:destination ?s } }"""
ROAD = "http://example.org/orexis/road#"
#  THE HEDGES EITHER SIDE OF THE LANE, which a radar slot sees as it passes and nothing types: the road's own.
HEDGES = {(2, 0), (3, 0), (4, 0), (2, 2), (4, 2)}


class Bus:
    """One broker: what the simulator publishes reaches the courier, what the courier publishes reaches the
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


def _layby(monkeypatch, world: Path = WORLD):
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(world, bus, now=NOW)
    bus.runtimes["courier_a"] = Runtime(boot(world, "courier_a"), "courier_a", transport=Mqtt(L + "courier_a", bus))
    return bus, time


def variant(tmp_path: Path, name: str, edits: dict) -> Path:
    """The layby with its documents rewritten — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / name / "world" / "layby"
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
    """Ten seconds at a time, the simulator reporting and the courier planning and walking, until nothing of
    its is walking: what it believed stands where, after each step."""
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
    bus, time = _layby(monkeypatch)
    assert bus.simulator.open() == ["actuators/van_a/command"], "the parked van listens for nothing"
    assert len(bus.simulator.vans) == 1 and bus.simulator.position(ROAD + "hedge_2_0") == (2, 0), \
        "the driven van read off the world, the road's hedges off the domain it imports"
    assert bus.simulator.position(L + "van_b") == (6, 0), "the parked van stands where its model says"
    bus.simulator.step(NOW)                                             # the fix: van A at (0, 1)
    bus.runtime.run(passes=1, poll_s=0)
    at = _at(bus.runtime.beliefs)
    assert at["van_a"] == (0, 1) and at["parcel_a"] == (1, 1) and "van_b" not in at, f"van B, six cells off, is believed nowhere: {at}"
    assert at["contact_1"] == (2, 0), f"the hedge two cells on is seen, and nothing knows it is a hedge: {at}"
    assert len(bus.runtime.parts["execution"].executor.walking()) == 1, "a plan for the parcel is walked"
    assert [t for t, _ in bus.commands] == ["actuators/van_a/command"], "the first drive is sent to the van"
    assert bus.commands[0][1] == {"to": {"x": 1, "y": 1}}, "to the parcel's cell, by its coordinates"
    #  THE WORLD ANSWERS: ten seconds at a time, the fix reporting the van's cell, until the plan is walked.
    seen = _walk(bus, time, 90)
    assert bus.runtime.parts["execution"].executor.walking() == [], "the plan was walked to its end"
    at = _at(bus.runtime.beliefs)
    assert (at["van_a"], at["parcel_a"], at["van_b"]) == ((6, 1), (6, 1), (6, 0)), at
    #  THE CONTACT (#1003): van B, parked at (6, 0), is believed nowhere until van A comes within the receiver's
    #  range of it, two cells either way, and at its coordinates from then on; the radar slot, with B identified
    #  by the receiver, sees the hedges beside the lane as the van passes them, and nothing else.
    first = next(i for i, at in enumerate(seen) if "van_b" in at)
    assert all("van_b" not in at for at in seen[:first]) and seen[first]["van_a"] == (4, 1), seen[first]
    assert all(at["van_b"] == (6, 0) for at in seen[first:]), "once seen, where it is"
    assert {at.get("contact_1") for at in seen} <= {None, *HEDGES} and any(at.get("contact_1") in HEDGES for at in seen), \
        "the radar saw the hedges beside the lane and nothing else"
    assert all(t == "actuators/van_a/command" for t, _ in bus.commands), "nothing commanded the parked van"
    told = [(payload["to"]["x"], payload["to"]["y"]) for _, payload in bus.commands]
    assert told[0] == (1, 1) and told[-1] == (6, 1) and len(told) == 6, f"six drives, east along the lane: {told}"
    assert not set(told) & HEDGES, f"no hedge was driven: {told}"
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip([(0, 1), *told], told)), "each a neighbour of the last"
    assert bus.simulator.position(L + "van_a") == (6, 1), "the simulator's van is at the eastern end: nobody wrote it there"
    assert (time["at"] - NOW) <= timedelta(minutes=8), f"walked within eight minutes of the world's time: {time['at'] - NOW}"


def test_a_van_told_a_cell_that_is_no_neighbour_refuses_and_stays(monkeypatch, caplog):
    bus, time = _layby(monkeypatch)
    bus.simulator.open()
    bus.simulator.step(NOW)
    bus.simulator.command("actuators/van_a/command", b'{"to": {"x": 6, "y": 1}}')
    assert "no neighbour" in caplog.text
    time["at"] += timedelta(seconds=60)
    bus.simulator.step(time["at"])
    assert bus.simulator.position(L + "van_a") == (0, 1)


#  A TREE ACROSS THE ROAD (#1003): van A starts at (0, 0) with its parcel at (0, 2), and a thing nothing
#  identifies lies on the direct way at (0, 1), one cell off, within the radar's range. The slot's vector
#  lands there, the slot is believed there, and the constraint keeps every plan off it: a way round, two
#  drives longer, is the one taken.
_FROM_THE_CORNER = {"world.ttl": [("sim:initialValue 1 ; sim:jitter 0 ] ;    # van A row 1", "sim:initialValue 0 ; sim:jitter 0 ] ;    # van A row 0")],
                    "beliefs/courier_a.state.ttl": [(":parcel_a courier:x 1 ; courier:y 1 .", ":parcel_a courier:x 0 ; courier:y 2 .")]}
DETOUR = {**_FROM_THE_CORNER,
          "world.ttl": [*_FROM_THE_CORNER["world.ttl"],
                        (":driver_b a courier:Driver ;",
                         ':tree sim:simulatedBy [ a sim:Model ; sim:x 0 ; sim:y 1 ] ; rdfs:label "a fallen tree, which only the radar knows" .\n'
                         ":driver_b a courier:Driver ;")],
          "society.ttl": [(":van_a , :van_b ,", ":van_a , :van_b , :tree ,")]}


def test_a_thing_the_radar_sees_is_an_obstacle_and_the_plan_goes_round_it(monkeypatch, tmp_path):
    bus, time = _layby(monkeypatch, variant(tmp_path, "detour", DETOUR))
    bus.simulator.open()
    bus.simulator.step(NOW)
    bus.runtime.run(passes=1, poll_s=0)
    at = _at(bus.runtime.beliefs)
    assert at["van_a"] == (0, 0) and at["contact_1"] == (0, 1) and "van_b" not in at, at
    seen = _walk(bus, time, 120)
    assert bus.runtime.parts["execution"].executor.walking() == [], "the plan was walked to its end"
    assert _at(bus.runtime.beliefs)["parcel_a"] == (6, 1), _at(bus.runtime.beliefs)
    told = [(payload["to"]["x"], payload["to"]["y"]) for _, payload in bus.commands]
    assert (0, 1) not in told, f"the obstacle's position was driven: {told}"
    #  ROUND THE TREE, four drives to the parcel where two would do through it — down column 1 or down column
    #  -1, the grid being infinite and the two ways tying.
    assert told[3] == (0, 2) and told[:3] in ([(1, 0), (1, 1), (1, 2)], [(-1, 0), (-1, 1), (-1, 2)]), f"round the tree to the parcel: {told}"
    assert {at.get("contact_1") for at in seen} <= {None, (0, 1), *HEDGES}, "the slot saw the tree where it is, and the hedges, and nothing else"
    assert seen[-1].get("contact_1") != (0, 1), "and the tree is no longer seen from the eastern end"
