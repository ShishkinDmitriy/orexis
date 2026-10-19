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


def _lane(monkeypatch, world: Path = WORLD):
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(world, bus, now=NOW)
    bus.runtime = Runtime(boot(world, "courier_a"), "courier_a", transport=Mqtt(L + "courier_a", bus))
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


def _walk(bus, time, limit: int) -> list[dict[str, str]]:
    """Ten seconds at a time, the simulator reporting and the courier planning and walking, until nothing is
    walking: what the courier believed stands where, after each step."""
    seen = []
    for _ in range(limit):
        time["at"] += timedelta(seconds=CADENCE_S)
        bus.simulator.step(time["at"])
        bus.runtime.run(passes=1, poll_s=0)
        seen.append(_at(bus.runtime.beliefs))
        if not bus.runtime.parts["execution"].executor.walking():
            break
    return seen


def test_the_van_is_driven_by_command_and_lands_where_the_fix_shows_it(monkeypatch):
    """Six drives, a pick and a drop from the western road to the eastern end, each drive sent to the van
    as the coordinates of the cell to reach, and each landing shown by the fix within the drive's band
    before the next is taken: the courier never writes its van's cell, the simulator moves it."""
    bus, time = _lane(monkeypatch)
    assert bus.simulator.open() == ["actuators/van_a/command"]
    assert bus.simulator.vans and (6, 1) in bus.simulator.cells, "the van and the grid read off the world"
    bus.simulator.step(NOW)                                             # the fix: the van at (0, 1)
    bus.runtime.run(passes=1, poll_s=0)
    assert _at(bus.runtime.beliefs) == {"van_a": "c0_1", "parcel_a": "c1_1"}, "van B, six cells off, is believed nowhere"
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
    told = [(payload["to"]["x"], payload["to"]["y"]) for _, payload in bus.commands]
    assert told[0] == (1, 1) and told[-1] == (6, 1) and len(told) == 6, f"six drives, east along the lane: {told}"
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip([(0, 1), *told], told)), "each a neighbour of the last"
    assert (bus.simulator.sensors[L + "fix_a_column"]["value"], bus.simulator.sensors[L + "fix_a_row"]["value"]) == (6.0, 1.0), \
        "the simulator's van is at the eastern end: nobody wrote it there"
    assert (time["at"] - NOW) <= timedelta(minutes=8), f"walked within eight minutes of the world's time: {time['at'] - NOW}"


def test_a_van_told_a_cell_that_is_no_neighbour_refuses_and_stays(monkeypatch, caplog):
    bus, time = _lane(monkeypatch)
    bus.simulator.open()
    bus.simulator.step(NOW)
    bus.simulator.command("actuators/van_a/command", b'{"to": {"x": 6, "y": 1}}')
    assert "no neighbour" in caplog.text
    time["at"] += timedelta(seconds=60)
    bus.simulator.step(time["at"])
    assert bus.simulator.sensors[L + "fix_a_column"]["value"] == 0.0


#  A TREE ACROSS THE ROAD (#1003): van A starts at (0, 0) with its parcel at (0, 2), and a thing nothing
#  identifies lies on the direct way at (0, 1), one cell off, within the radar's two. The slot's vector lands on
#  that cell, the slot is believed there, and the constraint keeps every plan off it: the way round through
#  column 1 is two drives longer, and is the one taken.
DETOUR = {"world.ttl": [("sim:initialValue 1 ; sim:jitter 0 ] ;    # row 1", "sim:initialValue 0 ; sim:jitter 0 ] ;    # row 0"),
                        (":driver_b a courier:Driver ;",
                         ':tree sim:simulatedBy [ a sim:Model ; sim:x 0 ; sim:y 1 ] ; rdfs:label "a fallen tree, which only the radar knows" .\n'
                         ":driver_b a courier:Driver ;")],
          "society.ttl": [(":van_a , :van_b ;", ":van_a , :van_b , :tree ;")],
          "state.ttl": [(":parcel_a courier:at :c1_1 .", ":parcel_a courier:at :c0_2 .")]}


def test_a_thing_the_radar_sees_is_an_obstacle_and_the_plan_goes_round_it(monkeypatch, tmp_path):
    bus, time = _lane(monkeypatch, variant(tmp_path, "detour", DETOUR))
    bus.simulator.open()
    bus.simulator.step(NOW)
    bus.runtime.run(passes=1, poll_s=0)
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
