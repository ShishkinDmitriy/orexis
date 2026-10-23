"""The lane, played by its simulator: two couriers on the road, a van each, whose drives the world answers
(#1002, #1004). A courier plans its parcel's delivery, each drive is a command to its van, the simulator has
the van on the cell forty-five seconds on, the fix reports it, the courier's transitions conclude the cell,
and the step lands — the whole loop on one fake broker both agents and the simulator share, with the
simulator reading the road's hedges off the domain the world imports. Each courier sees the other through a
contact within four cells (#1003), and holds the courier's constraints, so neither plans onto the other's position;
and where both want one position, they ask each other, draw lots for it and the loser gives way (#923).

Held to `world/lane/`: two minds on one road, each optimizing alone and meeting by what it senses; the one
mind with a van parked in its way is `world/layby/`, on the same road
(a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules, navigation-is-a-body-a-mover-and-a-move §5).
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

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
L = "http://example.org/orexis/world/lane#"
CADENCE_S = 10

#  WHERE EVERYTHING THE COURIER BELIEVES STANDS: every thing with two coordinates in its beliefs, by local name,
#  save where a parcel is owed, which is authored and never moves.
_AT_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?s ?x ?y WHERE { ?s courier:x ?x ; courier:y ?y . FILTER(isIRI(?s)) FILTER NOT EXISTS { ?p courier:destination ?s } }"""
ROAD = "http://example.org/orexis/road#"
#  THE HEDGES EITHER SIDE OF THE LANE, which a radar slot sees beside the van as it passes and nothing types: the road's own.
HEDGES = {(2, 0), (3, 0), (4, 0), (2, 2), (4, 2)}


class Bus:
    """One broker: what the simulator publishes reaches every courier, what a courier publishes reaches the
    simulator, and every command is kept."""

    def __init__(self):
        self.runtimes: dict[str, Runtime] = {}
        self.simulator = None
        self.commands: list[tuple[str, dict]] = []
        self.told: list[tuple[str, bytes]] = []

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
        elif topic.startswith("agents/"):
            self.told.append((topic, payload))
            agent = topic.split("/")[1]
            if agent in self.runtimes:
                self.runtimes[agent].deliver(topic, payload, clock.now())
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


def test_two_couriers_each_drive_their_own_van_and_see_the_other_within_four_cells(monkeypatch):
    """A drives six cells east along the lane to its parcel's destination while B, with nothing to deliver,
    stands on the eastern road: each courier reads its own fix, commands its own van, and believes the other's
    van only while its receiver has it within four cells. A asks B what its constraints read and B answers that
    nothing of its meets: no conflict, and no draw."""
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
    assert "contact_1" not in a and "contact_3" not in a, f"no hedge is beside the van, so the radar sees nothing: {a}"
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
    #  it, four cells either way, and at its coordinates from then on; the radar slot, with B identified by the
    #  receiver, sees the hedges beside the lane as the van passes them, and nothing else; the two slots see both
    #  hedges a cell has beside it at once, the second slot only there.
    first = next(i for i, at in enumerate(seen) if "van_b" in at)
    assert all("van_b" not in at for at in seen[:first]) and seen[first]["van_a"] == (2, 1), seen[first]
    assert all(at["van_b"] == (6, 0) for at in seen[first:]), "once seen, where it is"
    radar = {at.get(slot) for at in seen for slot in ("contact_1", "contact_3")}
    assert radar <= {None, *HEDGES} and HEDGES <= radar, f"the radar saw every hedge beside the lane and nothing else: {radar}"
    assert any(at.get("contact_1") in HEDGES and at.get("contact_3") in HEDGES for at in seen), "two at once, beside one cell"
    #  THE OTHER MIND (#1004): B saw A only within four cells of (6, 0), from (2, 1) on, and holds it at its cell.
    b = _at(bus.runtimes["courier_b"].beliefs)
    assert (b["van_b"], b["parcel_b"], b["van_a"]) == ((6, 0), (6, 0), (6, 1)), b
    assert bus.commands and all(t == "actuators/van_a/command" for t, _ in bus.commands), "B commanded nothing"
    told = [(payload["to"]["x"], payload["to"]["y"]) for _, payload in bus.commands]
    assert told[0] == (1, 1) and told[-1] == (6, 1) and len(told) == 6, f"six drives, east along the lane: {told}"
    assert not set(told) & HEDGES, f"no hedge was driven: {told}"
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip([(0, 1), *told], told)), "each a neighbour of the last"
    assert bus.simulator.position(L + "van_a") == (6, 1), "the simulator's van is at the eastern end: nobody wrote it there"
    assert (time["at"] - NOW) <= timedelta(minutes=8), f"walked within eight minutes of the world's time: {time['at'] - NOW}"
    #  THE COST OF NO CONFLICT (#923): A asked B each time its holdings changed while B was in range, B answered
    #  each, and nothing B said carried a holding — B is going nowhere — so neither drew.
    said = [(topic.split("/")[1], payload.decode()) for topic, payload in bus.told]
    asked = [p for to, p in said if to == "courier_b" and "coordination#Question" in p]
    answered = [p for to, p in said if to == "courier_a" and "coordination#Answer" in p]
    assert asked and len(answered) == len(asked), f"every question answered: {len(asked)} asked, {len(answered)} answered"
    assert not any("coordination#holding" in p for p in answered), "B's answers carried nothing"
    assert not any(to == "courier_a" and "coordination#Question" in p for to, p in said), \
        "B, whose plan touches nothing of the constraint, asked nothing though A was in range"
    assert not any("draw#" in p for _, p in said), "and no draw was committed to"


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



#  THE PASSING PLACE (#1016): parcel A owed at (3, 2), between the hedges at (2, 2) and (4, 2), so the way in is
#  from (3, 1); a plan found before the hedges are seen goes round by (2, 2).
_PASSING_PLACE = {"beliefs/courier_a.state.ttl": [(":east_end courier:x 6 ; courier:y 1 ;", ":east_end courier:x 3 ; courier:y 2 ;")]}


def test_a_van_never_drives_onto_a_hedge_its_radar_has_shown(monkeypatch, tmp_path):
    """Courier A delivers into the passing place without standing on a hedge: what the radar shows is taken
    into account before a head is taken, the walk the reading wakes included, since the take-time check asks
    the held constraints of the world the head lands in (#1016)."""
    bus, time = _lane(monkeypatch, variant(tmp_path, "passing_place", _PASSING_PLACE))
    bus.simulator.open()
    bus.simulator.step(NOW)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    on_a_hedge = []
    for _ in range(60):
        time["at"] += timedelta(seconds=CADENCE_S)
        bus.simulator.step(time["at"])
        for runtime in bus.runtimes.values():
            runtime.run(passes=1, poll_s=0)
        if bus.simulator.position(L + "van_a") in HEDGES:
            on_a_hedge.append((time["at"], bus.simulator.position(L + "van_a")))
        if _at(bus.runtime.beliefs).get("parcel_a") == (3, 2) and not bus.runtime.parts["execution"].executor.walking():
            break
    assert not on_a_hedge, f"van A stood on a hedge: {on_a_hedge}"
    assert _at(bus.runtime.beliefs)["parcel_a"] == (3, 2), "delivered into the passing place"
    told = [(p["to"]["x"], p["to"]["y"]) for t, p in bus.commands if t == "actuators/van_a/command"]
    assert not set(told) & HEDGES and told[-1] == (3, 2), f"no hedge was driven: {told}"

#  HEAD ON (#923): van B starts on the lane at (6, 1) and its parcel is owed at the western end of the road, so
#  the two vans drive at each other down row 1. Each courier's secret is stated in its self graph, so the draw is
#  the same every run: with these two, B goes first.
_HEAD_ON = {"world.ttl": [("sim:initialValue 0 ; sim:jitter 0 ] ;    # van B row 0", "sim:initialValue 1 ; sim:jitter 0 ] ;    # van B row 1")],
            "beliefs/courier_b.state.ttl": [(":parcel_b courier:x 6 ; courier:y 0 .", ":parcel_b courier:x 5 ; courier:y 1 ."),
                                            (":east_road courier:x 6 ; courier:y 0 ;", ":east_road courier:x 0 ; courier:y 0 ;")],
            "beliefs/courier_a.self.ttl": [(":courier_a planning:budget 256 .", f':courier_a planning:budget 256 ; coordination:secret "{"1" * 64}" .')],
            "beliefs/courier_b.self.ttl": [(":courier_b planning:budget 256 .", f':courier_b planning:budget 256 ; coordination:secret "{"2" * 64}" .')]}


def test_two_couriers_meeting_head_on_draw_lots_and_the_loser_gives_way(monkeypatch, tmp_path):
    """A drives east to (6, 1) and B west to (0, 0), each down the one row both stand on. Each sees the other
    four cells off, asks what its constraints read, and is answered with the positions the other's plan will hold
    that its own will too: each concludes the conflict itself, commits to its number and reveals it, and both
    conclude alike that B goes first. B drives on; A lays B's holdings, gives way off the row, and goes round. No
    two vans ever stand at one position, and both parcels are delivered."""
    bus, time = _lane(monkeypatch, variant(tmp_path, "head_on", _HEAD_ON))
    bus.simulator.open()
    bus.simulator.step(NOW)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    together, positions = [], []
    for _ in range(100):
        time["at"] += timedelta(seconds=CADENCE_S)
        bus.simulator.step(time["at"])
        for runtime in bus.runtimes.values():
            runtime.run(passes=1, poll_s=0)
        a, b = bus.simulator.position(L + "van_a"), bus.simulator.position(L + "van_b")
        positions.append((a, b))
        if a == b:
            together.append((time["at"], a))
        if (a, b) == ((6, 1), (0, 0)) and not any(r.parts["execution"].executor.walking() for r in bus.runtimes.values()):
            break                           # both delivered: an intention refused and not yet re-planned is no end
    assert not together, f"two vans stood at one position: {together}"
    assert positions[-1] == ((6, 1), (0, 0)), f"both vans where their parcels are owed: {positions[-1]}"
    assert _at(bus.runtime.beliefs)["parcel_a"] == (6, 1) and _at(bus.runtimes["courier_b"].beliefs)["parcel_b"] == (0, 0)
    #  EACH CONCLUDED THE SAME WINNER, from its own documents.
    won = {name: {r["w"] for r in rows(rt.beliefs, _WON_Q, graphs_of(rt.beliefs, "http://example.org/orexis#BeliefGraph"))}
           for name, rt in bus.runtimes.items()}
    assert won == {"courier_a": {L + "courier_b"}, "courier_b": {L + "courier_b"}}, won
    #  THE COST OF A CONFLICT (#923): every question each asked while the other was in range — one per change of
    #  its holdings — was answered, and the draw, decided in its first round, cost each agent two documents, a
    #  commitment and a reveal; measured 2026-10-23 at 16 questions from A and 12 from B over 61 ticks.
    said = [(topic.split("/")[1], payload.decode()) for topic, payload in bus.told]
    for asker, answerer in (("courier_a", "courier_b"), ("courier_b", "courier_a")):
        asked = [p for to, p in said if to == answerer and "coordination#Question" in p]
        answered = [p for to, p in said if to == asker and "coordination#Answer" in p]
        assert asked and len(answered) == len(asked), f"{asker} asked {len(asked)} and was answered {len(answered)} times"
        assert sum(1 for to, p in said if to == answerer and "draw#Commitment" in p) == 1, f"{asker} committed once"
        assert sum(1 for to, p in said if to == answerer and "draw#Reveal" in p) == 1, f"{asker} revealed once"
    #  THE LOSER GAVE WAY: off row 1 and round, while B, the winner, drove straight down it to its parcel's road.
    told_a = [(p["to"]["x"], p["to"]["y"]) for t, p in bus.commands if t == "actuators/van_a/command"]
    told_b = [(p["to"]["x"], p["to"]["y"]) for t, p in bus.commands if t == "actuators/van_b/command"]
    assert any(y != 1 for _, y in told_a), f"A gave way off the row: {told_a}"
    assert told_b == [(5, 1), (4, 1), (3, 1), (2, 1), (1, 1), (0, 1), (0, 0)], f"B drove straight down the row: {told_b}"
    assert not (set(told_a) | set(told_b)) & HEDGES, f"no hedge was driven: {told_a}, {told_b}"


_WON_Q = "SELECT ?w WHERE { ?draw <http://example.org/orexis/coordination#wonBy> ?w }"


#  A CROSSING (#923): van B down column 5 from (5, -4) to its parcel's road at (5, 4), across the lane van A
#  drives east along; both are due at (5, 1) after five drives. The two secrets decide the draw: with 5s and 6s A
#  goes first, with 0s and 5s B does.
def _crossing(a: str, b: str) -> dict:
    return {"world.ttl": [("sim:initialValue 6 ; sim:jitter 0 ] ;    # van B column 6", "sim:initialValue 5 ; sim:jitter 0 ] ;    # van B column 5"),
                          ("sim:initialValue 0 ; sim:jitter 0 ] ;    # van B row 0", "sim:initialValue -4 ; sim:jitter 0 ] ;    # van B row -4")],
            "beliefs/courier_b.state.ttl": [(":parcel_b courier:x 6 ; courier:y 0 .", ":parcel_b courier:x 5 ; courier:y -4 ."),
                                            (":east_road courier:x 6 ; courier:y 0 ;", ":east_road courier:x 5 ; courier:y 4 ;")],
            "beliefs/courier_a.self.ttl": [(":courier_a planning:budget 256 .", f':courier_a planning:budget 256 ; coordination:secret "{a * 64}" .')],
            "beliefs/courier_b.self.ttl": [(":courier_b planning:budget 256 .", f':courier_b planning:budget 256 ; coordination:secret "{b * 64}" .')]}


@pytest.mark.parametrize("secrets, first", [(("5", "6"), "courier_a"), (("0", "5"), "courier_b")], ids=["a_first", "b_first"])
def test_two_couriers_at_a_crossing_draw_lots_and_the_winner_goes_first(monkeypatch, tmp_path, secrets, first):
    """A drives east down row 1 and B north up column 5, each due at (5, 1). Each asks, answers and draws, and
    both conclude alike who goes first. The winner drives straight across, its plan found again once it has won
    where it was found yielding while the draw stood; the loser waits short of the crossing until the winner has
    passed it, then drives straight on. No two vans ever stand at one position, and both parcels are delivered."""
    bus, time = _lane(monkeypatch, variant(tmp_path, f"crossing_{first}", _crossing(*secrets)))
    bus.simulator.open()
    bus.simulator.step(NOW)
    for runtime in bus.runtimes.values():
        runtime.run(passes=1, poll_s=0)
    together, positions = [], []
    for _ in range(100):
        time["at"] += timedelta(seconds=CADENCE_S)
        bus.simulator.step(time["at"])
        for runtime in bus.runtimes.values():
            runtime.run(passes=1, poll_s=0)
        a, b = bus.simulator.position(L + "van_a"), bus.simulator.position(L + "van_b")
        positions.append((a, b))
        if a == b:
            together.append((time["at"], a))
        if (a, b) == ((6, 1), (5, 4)) and not any(r.parts["execution"].executor.walking() for r in bus.runtimes.values()):
            break
    assert not together, f"two vans stood at one position: {together}"
    assert positions[-1] == ((6, 1), (5, 4)), f"both vans where their parcels are owed: {positions[-1]}"
    won = {name: {r["w"] for r in rows(rt.beliefs, _WON_Q, graphs_of(rt.beliefs, "http://example.org/orexis#BeliefGraph"))}
           for name, rt in bus.runtimes.items()}
    assert won == {"courier_a": {L + first}, "courier_b": {L + first}}, won
    told_a = [(p["to"]["x"], p["to"]["y"]) for t, p in bus.commands if t == "actuators/van_a/command"]
    told_b = [(p["to"]["x"], p["to"]["y"]) for t, p in bus.commands if t == "actuators/van_b/command"]
    assert told_a == [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1)], f"A drove straight along its row: {told_a}"
    assert told_b == [(5, y) for y in range(-3, 5)], f"B drove straight up its column: {told_b}"
    #  THE WINNER CROSSED FIRST, and the loser came to the crossing only once the winner had left it.
    if first == "courier_a":
        crossed = next(i for i, (a, _) in enumerate(positions) if a == (6, 1))
        assert all(b[1] < 1 for _, b in positions[:crossed]), "B entered the lane only once A had crossed it"
    else:
        crossed = next(i for i, (_, b) in enumerate(positions) if b[1] > 1)
        assert all(a[0] < 5 for a, _ in positions[:crossed]), "A came to the crossing only once B had crossed it"
