"""One mind on the lane: the lane's own documents with ONE agent playing both drivers, two vans and two
parcels in a yard off the road, and the courier's constraint that no two vans stand at one position (#567,
ported onto the lane by #1004). Every drive is a command to the van, the simulator has the van there
forty-five seconds on, its fix reports it and the courier's transition concludes where it stands, so where
a van is comes from outside and is never posed (knowledge/domain/courier/position.md). What this is held
to is what was MEASURED on it, the dispatcher's figures, which the world answering the drives leaves as
they were, since the search sees the same declarations:

- the two vans are ONE scope, joined through the parcels, since a parcel standing where either van could
  stand is a filling value of both vans' Pick (a-scope-is-a-predicate-on-a-key, the two-vans seam);
- two parcels astray are ONE want where a constraint can make their plans collide, and on an infinite
  grid a constraint over a position couples every parcel, since two vans can always meet (one-mind-couples-
  the-wants-a-constraint-can-make-collide, the-grid-is-infinite-and-a-position-is-two-coordinates): one want
  about both, one search, the joint ten-step plan optimal for both by construction. Its estimate is the
  desire's sum over both parcels, ten, which is what the plan costs; what the coupling costs is the
  product, 328 candidates against 20 each for a van alone, and a budget of 128 cuts it short;
- a want's estimate never overstates what its plan cost, held as a gate over the yard, the corridor, a
  van alone and a van parked in the way;
- A WORLD THAT VIOLATES THE CONSTRAINT IS IMPOSSIBLE: weighed in every possible world the search weighs,
  and a world with two vans at one position is marked `planning:impossible` on its own row, off the
  frontier and never an achiever; walked, the joint plan puts two vans at one position at no act, and a
  van parked across the other's only shortest path is not driven through: the one mind delivers with the
  parked van, or moves it aside;
- two vans at one position AS THE FIXES REPORT is a contradiction, not a want: said in the log by the
  pass, answered by `Planner.contradictions`, and nothing is minted from it. Onboarding refuses such a
  world only where it is POSED, and the lane poses no van, so that half is the driver world's
  (`world/driver/tests/test_driver.py`);
- A PARCEL ARRIVING MID-WALK REOPENS THE WALKING WANT where the constraint couples it (#905, commitment),
  searched from the ground van A's step in flight lands in, that step answered by the world and never
  cancelled;
- A BELIEF THAT MAKES THE WALKING PLAN'S NEXT WORLD IMPOSSIBLE REOPENS IT TOO (#921): a peer's van foreseen,
  or SEEN by van A's receiver once the world puts it there (#922), on the position van A drives to next;
  a peer's van foreseen where the plan never goes reopens nothing;
- A VAN WAITS FOR A PEER'S ROUTE LAID AS A FORECAST (#920): the planning package's wait lands where the next
  ground begins, so van A waits a cell short while van B crosses ahead, and waits out van B standing.

THE YARD. The dispatcher's four-by-four, posed eight columns west of the lane's mouth, where no radar ever
has a hedge in range, so what the radars report is nothing and the figures are the search's alone; every
place in these tests is said in the yard's coordinates, and `_road` and `_yard` turn one into the other.
A van the agent does not drive is a peer's, believed only where van A's receiver has it within four cells.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.execution.ontology import COMMITTED_STEP_GRAPH
from agent.hash_named_graph import hash_named_graph
from agent.ontology import BELIEF, OREXIS, FORECAST, SELF_GRAPH
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import entry, graphs_of, rows, update
from agent.transport.mqtt.driver import Mqtt
from onboarding import reading
from simulation.simulator import Simulator

LANE = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
L = "http://example.org/orexis/world/lane#"
AGENT = "courier_a"
CADENCE_S = 10
#  WHERE THE YARD LIES on the road: its column 0 is the road's column -8, so the nearest hedge, at the road's
#  (2, 0), is seven columns off the yard's east side, past every radar's one and every receiver's four.
WEST = -8
#  THE ONE WANT THE TWO PARCELS ARE where the constraint couples them, named for both.
JOINT = "every_parcel_delivered.pursued.parcel_a.parcel_b"
A = "every_parcel_delivered.pursued.parcel_a"
B = "every_parcel_delivered.pursued.parcel_b"
#  THE CONSTRAINTS the lane holds (`constraints.ttl`): no two vans at one position, and no van on an
#  obstacle, which nothing in the yard ever is.
COURIER = "http://example.org/orexis/courier#"
CONSTRAINT = "no_two_vans_at_one_position"
OBSTACLE = "no_van_on_an_obstacle"
#  THE DRIVE'S BAND, as the courier declares it (#901): a drive lands between half a minute and a minute
#  after it is taken; a pick and a drop at once. The executor's patience past the latest landing is its own.
DRIVE_LEAST_S, DRIVE_MOST_S = 30, 60
PATIENCE_S = 60
#  WHAT THE COUPLED SEARCH NEEDS: 328 candidates in the yard and 318 on the corridor, measured
#  (measure-the-search), past the lane's 256; so every pose here where one agent drives both vans states
#  512 in the agent's self graph, the dispatcher's figure, and the corridor states 1024.
BOTH_BUDGET, CORRIDOR_BUDGET = 512, 1024

_MEMBERS_Q = "SELECT ?m ?s WHERE { GRAPH ?g { ?m planning:inScope ?s } }"
_WANTS_Q = "SELECT ?w ?d WHERE { GRAPH ?g { ?w a planning:Want ; prov:wasDerivedFrom ?d } }"
_PLANS_Q = """
SELECT ?want ?outcome (COUNT(?step) AS ?steps) WHERE {
  GRAPH ?p { ?p a planning:Plan ; planning:outcome ?outcome ; planning:for ?want .
             OPTIONAL { ?step a execution:Step ; execution:partOf ?p } } }
GROUP BY ?want ?outcome"""
_STEPS_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?want ?a ?van ?parcel ?tx ?ty WHERE {
  GRAPH ?p { ?p planning:for ?want . ?step a execution:Step ; execution:partOf ?p ; planning:fills ?a .
             OPTIONAL { ?step courier:van ?van } OPTIONAL { ?step courier:parcel ?parcel }
             OPTIONAL { ?step courier:toX ?tx ; courier:toY ?ty } } }"""
#  THE POSSIBLE WORLDS WEIGHED PER WANT — the figure measure-the-search tabulates; a candidate passed
#  over is weighed too and is not counted here.
_WEIGHED_Q = """
SELECT ?for (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?w .
    ?w a planning:PossibleGraph } }
GROUP BY ?for"""
#  WHAT A WANT'S SEARCH SPENT — every weighing but a ground's, a candidate passed over among them: the
#  unit the budget is stated in, and the runbook's "candidates".
_SPENT_Q = """
SELECT ?for (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?u .
    FILTER NOT EXISTS { ?u a planning:GroundGraph } } }
GROUP BY ?for"""
#  WHAT EACH WANT'S ESTIMATE READ IN THE PRESENT GROUND.
_REMAINING_Q = """
SELECT ?for ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?g ;
    planning:remaining ?left . ?g a planning:GroundGraph } }"""
#  WHAT EACH WANT'S PLAN SPENT — the cost the search found, which the estimate at the root may never exceed.
_COSTS_Q = """
SELECT ?want ?spent WHERE { GRAPH ?p { ?p a planning:Plan ; planning:for ?want ; planning:spent ?spent } }"""
_WORLDS_Q = "SELECT ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph } }"
#  WHAT A WANT'S SEARCH SAYS OF EACH POSSIBLE WORLD IT WEIGHED, and what the WORLD says of itself.
_JUDGED_Q = """
SELECT ?w ?impossible ?open ?expanded ?met WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for $want ; planning:weighs ?w .
    ?w a planning:PossibleGraph .
    OPTIONAL { ?w planning:impossible ?impossible } OPTIONAL { ?x planning:open ?open }
    OPTIONAL { ?x planning:expanded ?expanded } OPTIONAL { ?x planning:met ?met } } }"""
#  EVERY POSSIBLE WORLD MARKED IMPOSSIBLE, and by which constraint.
_IMPOSSIBLE_Q = """
SELECT ?w ?by WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph ; planning:impossible ?by } }"""
#  TWO VANS AT ONE POSITION, in one graph's facts: the vans' kinds are common and the world's facts its own.
_SHARED_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT DISTINCT ?x ?y WHERE { GRAPH $w { ?a courier:x ?x ; courier:y ?y . ?b courier:x ?x ; courier:y ?y }
                              GRAPH ?h { ?a a courier:Van . ?b a courier:Van } FILTER(?a != ?b) }"""
#  WHERE THINGS STAND, and in which graph: a published plan's steps state the positions they predict in graphs
#  of their own, and a read over every graph took a van's predicted position for its present one; `_present`
#  says which graphs hold now. A place a parcel is owed at is authored and never moves.
_AT_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?s ?p ?v ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?s ?p ?v }
  VALUES ?p { courier:x courier:y } FILTER NOT EXISTS { GRAPH ?h { ?d courier:destination ?s } } }"""
#  WHAT A WEIGHING IN A GROUND SAYS IS IN TROUBLE, and where: each witness's instance and the value that offended.
_WITNESSES_Q = """
SELECT ?x ?cell WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:Weighing ; planning:for $d ; planning:weighs ?g ; planning:violation ?v .
               ?g a planning:GroundGraph . ?v planning:instance ?x ; planning:offending ?cell } }"""
#  THE PLAN'S STEPS WITH THEIR INSTANTS, along the chain, and the period of the world each reaches.
_PLACED_Q = """
SELECT ?step ?a ?nb ?la ?na ?ws ?we WHERE {
  GRAPH ?p { ?p a planning:Plan ; planning:for $want . ?step a execution:Step ; execution:partOf ?p ; planning:fills ?a ;
             planning:of ?by ; execution:notBefore ?nb ; execution:landsAt ?la . OPTIONAL { ?step execution:notAfter ?na } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w planning:by ?by ; dcterms:temporal ?period . ?period orexis:start ?ws ; orexis:end ?we } }
ORDER BY ?nb ?la"""
#  THE COMMITTED STEPS' WINDOWS in the beliefs, with the two lengths each states.
_WINDOWS_Q = """
SELECT ?g ?s ?e ?within ?by WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a execution:CommittedStepGraph ; dcterms:temporal ?p . ?p orexis:start ?s ; orexis:end ?e }
  GRAPH ?g { ?step execution:landsWithinS ?within ; execution:answeredWithinS ?by } }
ORDER BY ?s ?g"""
_INTENTIONS_Q = "SELECT (COUNT(?i) AS ?n) WHERE { GRAPH ?g { ?i a execution:Intention } }"
#  WHAT A WANT'S MET-TEST TARGETS — one node per instance a coupled want is about.
_TARGETS_Q = "SELECT ?t WHERE { GRAPH ?g { $w planning:metWhen ?m . ?m sh:targetNode ?t } }"

#  EVERY TEST HERE WALKS A WORLD'S AGENT through the world's time: run where CI runs, never in the local gate.
pytestmark = pytest.mark.walk


#  THE LANE AS ONE MIND: how the shipped lane's documents are rewritten. Van A's fix and van B's, as the lane
#  poses them, each line the place a pose puts its number.
_FIX = {("a", "x"): "sim:initialValue 0 ; sim:jitter 0 ] ;    # van A column 0",
        ("a", "y"): "sim:initialValue 1 ; sim:jitter 0 ] ;    # van A row 1",
        ("b", "x"): "sim:initialValue 6 ; sim:jitter 0 ] ;    # van B column 6",
        ("b", "y"): "sim:initialValue 0 ; sim:jitter 0 ] ;    # van B row 0"}
_DRIVES_A = "    orexis:actsFor :van_a ;\n    orexis:plays :driver_a ;"
_DRIVES_B = "    orexis:actsFor :van_b ;\n    orexis:plays :driver_b ;\n"
_SENSORS_A = ":fix_a_column , :fix_a_row , :receiver_b_column , :receiver_b_row , :radar_1_column , :radar_1_row , :radar_3_column , :radar_3_row"
_BUDGET_A = ":courier_a planning:budget 256 ."
_PARCEL_A = (':parcel_a a courier:Parcel ; courier:destination :east_end ; rdfs:label "the parcel owed at the eastern end" .\n'
             ':parcel_a courier:x 1 ; courier:y 1 .\n'
             ':east_end courier:x 6 ; courier:y 1 ; rdfs:label "the eastern end of the lane, where parcel A is owed" .')
_RADAR = {"a": ("radar_1", "radar_3"), "b": ("radar_2", "radar_4")}
_OTHER = {"a": "b", "b": "a"}


def _road(x: int, y: int) -> tuple[int, int]:
    """A place in the yard, on the road."""
    return (x + WEST, y)


def _yard(x: int, y: int) -> tuple[int, int]:
    """A place on the road, in the yard."""
    return (x - WEST, y)


def pose(tmp_path: Path, name: str, *, vans: dict, parcels: dict, drives: str = "ab", budget: int | None = None) -> Path:
    """The lane with one agent, courier A, driving the vans named in `drives` — acting for each, playing its
    driver, reading its fix and its radar — and believing any other van only by van A's receiver, as the
    lane's courier does a peer's. `vans` says where each van's fix starts, in the yard; a van not named stands
    where the lane poses it, far off on the road. `parcels` are courier A's own, each `(at, owed)`: a place,
    a van that carries it, or None for a parcel known and not yet anywhere. A copy, since a world imports
    its domains by the tree's shape; the lane's second courier is left unbooted and plays no driver one agent here does."""
    world = tmp_path / name / "world" / "lane"
    shutil.copytree(LANE, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / name / "domains").symlink_to(LANE.parents[1] / "domains")

    def edit(file: str, pairs) -> None:
        text = (world / file).read_text()
        for old, new in pairs:
            assert old in text, f"{file} no longer says {old!r}"
            text = text.replace(old, new)
        (world / file).write_text(text)

    pairs = []
    for van, place in vans.items():
        for axis, value in zip("xy", _road(*place)):
            old = _FIX[van, axis]
            pairs.append((old, f"sim:initialValue {value} ; sim:jitter 0 ] ;    # van {van.upper()} {'column' if axis == 'x' else 'row'} {value}"))
    pairs.append((_DRIVES_A, "    orexis:actsFor " + " , ".join(f":van_{v}" for v in drives) + " ;\n"
                             "    orexis:plays " + " , ".join(f":driver_{v}" for v in drives) + " ;"))
    if "b" in drives:
        pairs.append((_DRIVES_B, ""))
    edit("world.ttl", pairs)
    sensors = [s for v in drives for s in (f":fix_{v}_column", f":fix_{v}_row", *(f":{r}_{a}" for r in _RADAR[v] for a in ("column", "row")))]
    sensors += [s for v in drives if _OTHER[v] not in drives for s in (f":receiver_{_OTHER[v]}_column", f":receiver_{_OTHER[v]}_row")]
    edit("beliefs/courier_a.self.ttl", [(_SENSORS_A, " , ".join(sensors)),
                                        (_BUDGET_A, f":courier_a planning:budget {budget or (BOTH_BUDGET if len(drives) == 2 else 256)} .")])
    lines = []
    for parcel, (at, owed) in parcels.items():
        door = "door_" + parcel.rsplit("_", 1)[-1]
        lines.append(f":{parcel} a courier:Parcel" + (f" ; courier:destination :{door} ." if owed else " ."))
        if isinstance(at, str):
            lines.append(f":{parcel} courier:carriedBy :{at} .")
        elif at:
            lines.append(f":{parcel} courier:x {_road(*at)[0]} ; courier:y {_road(*at)[1]} .")
        if owed:
            lines.append(f":{door} courier:x {_road(*owed)[0]} ; courier:y {_road(*owed)[1]} .")
    edit("beliefs/courier_a.state.ttl", [(_PARCEL_A, "\n".join(lines))])
    return world


#  THE YARD AS THE DISPATCHER SHIPPED IT: each van at the foot of its own column, its parcel one cell up it,
#  owed at the top. Five steps each, and the two chains share no position.
YARD = dict(vans={"a": (0, 0), "b": (3, 0)}, parcels={"parcel_a": ((0, 1), (0, 3)), "parcel_b": ((3, 1), (3, 3))})
#  THE CORRIDOR: van A drives parcel A along the second row, van B drives parcel B down the third column, and
#  the two shortest chains meet at (2, 1), each van's third step.
CORRIDOR = dict(vans={"a": (0, 1), "b": (2, 3)}, parcels={"parcel_a": ((1, 1), (3, 1)), "parcel_b": ((2, 2), (2, 0))},
                budget=CORRIDOR_BUDGET)
#  ONE VAN AND ITS PARCEL ALONE, either half of the yard; the other van is a peer's, far off on the road.
HALF_A = dict(vans={"a": (0, 0)}, parcels={"parcel_a": ((0, 1), (0, 3))}, drives="a")
HALF_B = dict(vans={"b": (3, 0)}, parcels={"parcel_b": ((3, 1), (3, 3))}, drives="b")
#  BOTH VANS AT ONE POSITION as the fixes first report them.
TOGETHER = dict(vans={"a": (0, 0), "b": (0, 0)}, parcels=YARD["parcels"])
#  VAN B PARKED ACROSS THE ONLY SHORTEST PATH: van A at (0, 1), parcel A at (1, 1) owed at (3, 1) — two drives
#  through (2, 1), four round it — and van B standing on (2, 1) with no parcel of its own.
PARKED = dict(vans={"a": (0, 1), "b": (2, 1)}, parcels={"parcel_a": ((1, 1), (3, 1))})
#  THE SAME WITH PARCEL A ALREADY ABOARD VAN A at (1, 1), so only van A can deliver it.
CARRYING = dict(vans={"a": (1, 1), "b": (2, 1)}, parcels={"parcel_a": ("van_a", (3, 1))})


def _local(iri: str | None) -> str | None:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1] if iri else None


def _place(r: dict) -> tuple[int, int] | None:
    """Where a step drives, in the yard — None for a pick or a drop, which take no place."""
    return _yard(int(r["tx"]), int(r["ty"])) if r.get("tx") is not None else None


def _dt(instant: str) -> datetime:
    return datetime.fromisoformat(instant)


def _present(beliefs) -> list[str]:
    """What courier A believes holds at the world's instant: every belief graph holding then, the world's and
    its own — a reading's revision among them, which is where its transition concluded a van's position —
    save its self graph, a committed step and a forecast, which say what the agent is and what will hold."""
    aside = set(graphs_of(beliefs, SELF_GRAPH, COMMITTED_STEP_GRAPH, FORECAST))
    return [g for g in graphs_of(beliefs, BELIEF, at=clock.now()) if g not in aside]


def _at(beliefs) -> dict[str, tuple[int, int]]:
    """Where each van and parcel courier A believes it now, in the yard, off the graphs holding now. A van's
    two coordinates are two readings, its fix's column and its fix's row, so each is concluded in the
    revision of its own reading and a position is assembled across graphs; one value per coordinate, since
    a coordinate read twice is two beliefs about one key."""
    present = set(_present(beliefs))
    found: dict[str, dict[str, int]] = {}
    for r in rows(beliefs, _AT_Q, ()):
        name, axis = _local(r["s"]), _local(r["p"])
        if r["g"] in present and r["s"].startswith(L) and name.startswith(("van_", "parcel_")):
            value = int(r["v"])
            assert found.setdefault(name, {}).setdefault(axis, value) == value, f"{name} believed at two {axis}: {found[name][axis]} and {value}"
    return {name: _yard(c["x"], c["y"]) for name, c in found.items() if "x" in c and "y" in c}


def _together(beliefs) -> list[tuple[int, int]]:
    """The positions two vans courier A believes now stand at, in the yard."""
    vans = [place for name, place in _at(beliefs).items() if name.startswith("van_")]
    return sorted({p for p in vans if vans.count(p) > 1})


def _shared(store, graphs) -> dict[str, list[tuple[int, int]]]:
    """Per graph among `graphs`, the positions two vans stand at in it, in the yard — only those holding one."""
    found = {_local(g): sorted(_yard(int(r["x"]), int(r["y"])) for r in rows(store, _SHARED_Q, (), w=g)) for g in graphs}
    return {g: places for g, places in found.items() if places}


class Bus:
    """One broker: what the simulator publishes reaches courier A, what courier A publishes reaches the
    simulator, and every command is kept."""

    def __init__(self):
        self.runtime = None
        self.simulator = None
        self.commands: list[tuple[str, dict]] = []
        self.told: list[str] = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        if topic.startswith("sensors/"):
            self.runtime.deliver(topic, payload, clock.now())
        elif topic.startswith("agents/"):
            self.told.append(topic)                 # to the other courier, which no case here boots
        else:
            self.commands.append((topic, json.loads(payload)))
            self.simulator.command(topic, payload)


class Lane:
    """Courier A on the lane, its simulator and the world's time, which moves only when the test says."""

    def __init__(self, world: Path, budget: int | None = None, lay=None):
        self.at = NOW
        clock.now = lambda: self.at
        self.bus = Bus()
        self.bus.simulator = Simulator(world, self.bus, now=NOW)
        self.beliefs = boot(world, AGENT)
        if lay:
            lay(self.beliefs)
        self.runtime = self.bus.runtime = Runtime(self.beliefs, AGENT, transport=Mqtt(L + AGENT, self.bus), budget=budget)
        self.bus.simulator.open()
        self.executor = self.runtime.parts["execution"].executor
        self.planner = self.runtime.parts["planning"].planner

    @property
    def imaginarium(self):
        """The courier's scope's imaginarium: the one its drives are in, beside the draw's, which the world
        imports for two couriers and this one mind never takes."""
        (scope,) = {r["s"] for r in rows(self.beliefs, _MEMBERS_Q, ()) if _local(r["m"]) == "Drive"}
        return self.planner.imaginaria[scope]

    def tick(self) -> str:
        """The simulator reports what has fallen due at the world's instant, and courier A runs one pass."""
        self.bus.simulator.step(self.at)
        return self.runtime.run(passes=1, poll_s=0)

    def place(self, van: str, at: tuple[int, int]) -> None:
        """The world puts `van` at `at`, in the yard: the test's hand on the simulator, as a peer driving
        there would."""
        column, row, _ = self.bus.simulator.vans[L + van]
        x, y = _road(*at)
        self.bus.simulator.sensors[column]["value"], self.bus.simulator.sensors[row]["value"] = float(x), float(y)


@pytest.fixture(autouse=True)
def _the_clock(monkeypatch):
    """Every case sets the world's time through `Lane`; this puts the clock back after it."""
    monkeypatch.setattr(clock, "now", clock.now)


def _pass(world: Path, budget: int | None = None, lay=None) -> Lane:
    """Courier A's first pass, once the first fixes have reported where the vans stand, at the budget the
    world's self graph states unless the case is about another."""
    lane = Lane(world, budget, lay)
    lane.tick()
    return lane


def _wants(im) -> dict[str, str]:
    return {_local(r["w"]): _local(r["d"]) for r in rows(im, _WANTS_Q, ())}


def _plans(im) -> dict[str, tuple[str, int]]:
    return {_local(r["want"]): (_local(r["outcome"]), int(r["steps"])) for r in rows(im, _PLANS_Q, ())}


def _steps(im) -> dict[str, set[tuple]]:
    out: dict[str, set] = {}
    for r in rows(im, _STEPS_Q, ()):
        out.setdefault(_local(r["want"]), set()).add((_local(r["a"]), _local(r.get("van")), _local(r.get("parcel")), _place(r)))
    return out


def _weighed(im) -> dict[str, int]:
    return {_local(r["for"]): int(r["n"]) for r in rows(im, _WEIGHED_Q, ())}


def _spent(im) -> dict[str, int]:
    return {_local(r["for"]): int(r["n"]) for r in rows(im, _SPENT_Q, ())}


def _remaining(im) -> dict[str, float]:
    return {_local(r["for"]): float(r["left"]) for r in rows(im, _REMAINING_Q, ())}


def _costs(im) -> dict[str, float]:
    return {_local(r["want"]): float(r["spent"]) for r in rows(im, _COSTS_Q, ())}


def _targets(im, want: str) -> set[str]:
    return {_local(r["t"]) for r in rows(im, _TARGETS_Q, (), w=L + want)}


def _impossible(im) -> dict[str, int]:
    """Per constraint, how many possible worlds it marked impossible — on the worlds' own rows."""
    out: dict[str, int] = {}
    for r in rows(im, _IMPOSSIBLE_Q, ()):
        out[_local(r["by"])] = out.get(_local(r["by"]), 0) + 1
    return out


def _possible(im, want: str) -> None:
    """THE CONSTRAINT'S PROMISE, asserted of one want's search: no world holding two vans at one position
    was opened, is open, or is an achiever — every such world the search made is marked impossible by the
    constraint, or was passed over by hash as a repeat of one, and a want's weighing of an impossible world
    is bare. The loop is held to judging at least one world."""
    judged = {r["w"]: r for r in rows(im, _JUDGED_Q, (), want=L + want)}
    assert judged
    colliding = {g for g in (r["w"] for r in rows(im, _WORLDS_Q, ())) if rows(im, _SHARED_Q, (), w=g)}
    for w in colliding:
        row = judged.get(w)
        assert row is None or (_local(row.get("impossible")) == CONSTRAINT
                               and not row.get("open") and not row.get("expanded") and row.get("met") is None), \
            f"a world holding two vans was neither marked impossible nor passed over: {_local(w)} {row}"
    for w, row in judged.items():
        if row.get("impossible"):
            assert w in colliding, f"marked impossible, and holding no two vans: {_local(w)}"
            assert not row.get("open") and not row.get("expanded") and row.get("met") is None, \
                f"impossible and still judged for the want: {_local(w)} {row}"


def _run(world: Path, limit: int = 120):
    """Courier A over `world`, ten seconds of the world's time between passes, the simulator answering every
    drive, until no intention stands or `limit` passes are spent; every step taken traced as (step, van A's
    position, van B's, the positions two vans share) read off the beliefs the moment it was taken."""
    lane = Lane(world)
    trace: list[tuple] = []

    def traced(event):
        at = _at(lane.beliefs)
        trace.append((_local(event.step), at.get("van_a"), at.get("van_b"), _together(lane.beliefs)))
        return []
    lane.executor.step_taken.connect(traced)
    outcome = lane.tick()
    for _ in range(limit - 1):
        if outcome != UNFINISHED or not lane.executor.standing():
            break
        lane.at += timedelta(seconds=CADENCE_S)
        outcome = lane.tick()
    return lane, outcome, trace


def test_two_vans_are_one_scope_and_where_each_stands_is_what_its_fix_says(tmp_path):
    """One scope, and both vans in it with the parcels' class: nothing van A does reads a fact of van B, but a
    parcel is a filling value of either van's Pick, so the parcels join the vans — by key as by predicate.
    Booted, courier A believes no van anywhere; its first pass has each where its fix reports it."""
    world = pose(tmp_path, "yard", **YARD)
    lane = Lane(world)
    assert _at(lane.beliefs) == {"parcel_a": (0, 1), "parcel_b": (3, 1)}, "no van is posed: where a van is comes from outside"
    members: dict[str, set] = {}
    for r in rows(lane.beliefs, _MEMBERS_Q, ()):
        members.setdefault(_local(r["m"]), set()).add(r["s"])
    scopes = {s for m in ("van_a", "van_b", "Drive", "Pick", "Drop") for s in members[m]}
    assert len(scopes) == 1, f"two vans in one courier vocabulary are one scope: {scopes}"
    assert {"van_a", "van_b", "Parcel", "Drive", "Pick", "Drop", "x", "y", "carriedBy"} <= set(members), \
        "the vans the world states, and the parcels by their class, since they are courier A's own beliefs and a type pattern reads its class"
    lane.tick()
    assert _at(lane.beliefs) == {"van_a": (0, 0), "parcel_a": (0, 1), "van_b": (3, 0), "parcel_b": (3, 1)}


def test_two_parcels_the_constraint_can_make_collide_are_one_want_and_one_ten_step_plan(tmp_path):
    """ONE want about both parcels, targeting both, and one plan of ten steps over both vans. The constraint
    reads a van's position, a value a drive computes and so reachable anywhere, so a plan for either parcel
    can collide with a plan for the other, and the derivation couples the two. THE ESTIMATE IS THE DESIRE'S SUM
    OVER BOTH: ten in the present ground, the five each van alone reads added, which is the joint plan's own
    cost — the A* key the coupled search wants, admissible and tight. WHAT THE COUPLING COSTS IS THE
    PRODUCT: 328 candidates weighed, 248 of them worlds, against 20 for a van alone; at a budget of 128 the
    search is cut short and the passes after would finish it, so the agent states 512 of itself. In the
    yard no world the search visits holds two vans at one position, so the constraint marks nothing, and
    both constraints are weighed in every world the want is. Walked, the world answers every drive and both
    parcels are delivered."""
    yard = pose(tmp_path, "yard", **YARD)
    cut = _pass(yard, budget=128).imaginarium
    assert _plans(cut) == {JOINT: ("Exhausted", 0)} and _spent(cut)[JOINT] == 128, \
        "a budget of 128 cuts the coupled search short; the passes after finish it"
    im = _pass(yard).imaginarium
    assert _wants(im) == {JOINT: "every_parcel_delivered"}
    assert _targets(im, JOINT) == {"parcel_a", "parcel_b"}, "a coupled want's met-test targets each instance"
    plans, steps = _plans(im), _steps(im)
    assert plans == {JOINT: ("Satisfied", 10)}
    assert {van for _, van, _, _ in steps[JOINT] if van} == {"van_a", "van_b"}
    assert {parcel for _, _, parcel, _ in steps[JOINT] if parcel} == {"parcel_a", "parcel_b"}
    assert _shared(im, [r["w"] for r in rows(im, _WORLDS_Q, ())]) == {}, "no world the search visits holds two vans at one position"
    paid, left, spent = _weighed(im), _remaining(im), _spent(im)
    halves_paid, halves_left = {}, {}
    for name, half in (("a", HALF_A), ("b", HALF_B)):
        alone = _pass(pose(tmp_path, f"half_{name}", **half)).imaginarium
        (want,) = _plans(alone)
        assert _plans(alone)[want] == ("Satisfied", 5)
        halves_paid[want] = _weighed(alone)[want]
        halves_left[want] = _remaining(alone)[want]
    assert left[JOINT] == sum(halves_left.values()) == 10.0, f"the coupled want's estimate is the sum of its instances': {left} against {halves_left}"
    assert halves_paid == {A: 20, B: 20}, halves_paid
    assert (spent[JOINT], paid[JOINT]) == (328, 248), f"the product's price, measured: {spent} candidates, {paid} worlds"
    assert _impossible(im) == {} and paid[CONSTRAINT] == paid[OBSTACLE] == 248, "both constraints weighed in every world, marking none: " + str(paid)
    lane, outcome, trace = _run(yard)
    assert outcome == UNFINISHED and len(trace) == 10, "a desire holds the agent, and the one plan is walked"
    assert all(van_a and van_b for _, van_a, van_b, _ in trace), f"both vans believed where they stand at every act: {trace}"
    assert _at(lane.beliefs) == {"van_a": (0, 3), "parcel_a": (0, 3), "van_b": (3, 3), "parcel_b": (3, 3)}
    assert lane.bus.simulator.position(L + "van_a") == _road(0, 3) and lane.bus.simulator.position(L + "van_b") == _road(3, 3), \
        "the simulator's vans are where the agent believes them: nobody wrote them there"
    assert int(rows(lane.executor.intentions, _INTENTIONS_Q, ())[0]["n"]) == 1 and lane.executor.walking() == [], \
        "one plan, one intention, done"


def test_corridor_the_coupled_search_marks_the_worlds_holding_two_vans_impossible_and_the_joint_plan_shares_no_position(tmp_path):
    """One want, one plan of ten steps over both vans. The search REACHES worlds holding two vans at one
    position — a van driven onto the position the other stands at — and every one is IMPOSSIBLE, marked on
    its own row and bare for the want; thirteen are marked, three more were passed over by hash as repeats.
    No world opened, open or met holds two vans. Walked, the joint plan puts both vans at one position at no
    act. The corridor's search is past the 512 one agent driving both vans states, so it states 1024."""
    corridor = pose(tmp_path, "corridor", **CORRIDOR)
    im = _pass(corridor).imaginarium
    plans, steps = _plans(im), _steps(im)
    assert _wants(im) == {JOINT: "every_parcel_delivered"}
    assert plans == {JOINT: ("Satisfied", 10)}
    assert _spent(im)[JOINT] == 318, f"measured: {_spent(im)}"
    assert _weighed(im) == {JOINT: 242, CONSTRAINT: 242, OBSTACLE: 242}, "the constraints are weighed in every world the want is: " + str(_weighed(im))
    assert ("Drive", "van_a", None, (2, 1)) in steps[JOINT] and ("Drive", "van_b", None, (2, 1)) in steps[JOINT], \
        "both chains still cross the shared position, one van at a time"
    held = _shared(im, [r["w"] for r in rows(im, _WORLDS_Q, ())])
    assert len(held) == 16 and {p for places in held.values() for p in places} == {(1, 1), (2, 0), (2, 1), (2, 2), (3, 1)}, \
        f"worlds the coupled search reached with two vans at one position: {held}"
    assert _impossible(im) == {CONSTRAINT: 13}, f"marked impossible by the constraint, measured: {_impossible(im)}"
    _possible(im, JOINT)
    lane, outcome, trace = _run(corridor)
    assert outcome == UNFINISHED and len(trace) == 10
    assert [(step, shared) for step, _, _, shared in trace if shared] == [], \
        f"walked, the joint plan puts two vans at one position at no act — the constraint's promise: {trace}"
    assert _at(lane.beliefs) == {"van_a": (3, 1), "parcel_a": (3, 1), "van_b": (2, 0), "parcel_b": (2, 0)}


@pytest.mark.parametrize("name, layout, steps, spent, impossible, by, at", [
    ("parked", PARKED, 5, 62, 7, {"van_b"}, {"van_a": (0, 1), "van_b": (3, 1), "parcel_a": (3, 1)}),
    ("carrying", CARRYING, 4, 72, 5, {"van_a", "van_b"}, {"van_a": (3, 1), "van_b": (2, 0), "parcel_a": (3, 1)}),
])
def test_a_van_parked_across_the_only_shortest_path_is_not_driven_through(tmp_path, name, layout, steps, spent, impossible, by, at):
    """Van B stands on (2, 1) with nothing to do, parcel A is owed at (3, 1) from (1, 1), and the only
    two-drive route runs through B. Every world that puts van A on B's position is impossible, and the ONE
    MIND holding both vans does better than the route round: PARKED, with the parcel on the ground beside
    van B, it delivers with van B itself in five steps and van A never moves; CARRYING, with the parcel
    already aboard van A so only A can deliver it, it moves van B aside first and drives A through — four
    steps, where the route round is five. Walked, the vans share no position at any act."""
    world = pose(tmp_path, name, **layout)
    im = _pass(world).imaginarium
    assert _wants(im) == {A: "every_parcel_delivered"}
    assert _plans(im) == {A: ("Satisfied", steps)}
    assert {van for _, van, _, _ in _steps(im)[A] if van} == by, _steps(im)[A]
    assert (_spent(im)[A], _impossible(im)) == (spent, {CONSTRAINT: impossible}), f"measured: {_spent(im)} {_impossible(im)}"
    _possible(im, A)
    lane, outcome, trace = _run(world)
    assert outcome == UNFINISHED and len(trace) == steps
    assert [(step, shared) for step, _, _, shared in trace if shared] == [], f"two vans at one position at an act: {trace}"
    assert _at(lane.beliefs) == at


@pytest.mark.parametrize("name, layout, tight", [("yard", YARD, True), ("corridor", CORRIDOR, True),
                                                 ("half_a", HALF_A, True), ("parked", PARKED, True),
                                                 ("carrying", CARRYING, False)])
def test_a_wants_estimate_at_the_present_never_exceeds_what_its_plan_cost(tmp_path, name, layout, tight):
    """THE ONE PROMISE AN ESTIMATE MAKES, as a gate: what a want's estimate read in the present ground is at
    most what the plan the search found spent. Every want with a plan here is judged, and the loop is held
    to judging at least one. Mostly the figure is TIGHT — ten against ten for the coupled want, five against
    five for a van alone. NOT WHERE THE CONSTRAINT COSTS A STEP THE WANT DOES NOT OWE: with the parcel aboard
    van A and van B parked on the only short route, the estimate reads three and the plan costs four, since
    moving van B aside is a step the constraint makes necessary and the parcel does not owe (#902)."""
    im = _pass(pose(tmp_path, name, **layout)).imaginarium
    left, costs = _remaining(im), _costs(im)
    judged = {w: (left[w], costs[w]) for w in costs if w in left}
    assert judged and set(judged) == {w for w, (outcome, _) in _plans(im).items() if outcome == "Satisfied"}, \
        f"every want the search found a plan for has an estimate at the present: {left} against {costs}"
    assert all(estimate <= cost for estimate, cost in judged.values()), f"an estimate never overstates what the plan cost: {judged}"
    assert all((estimate == cost) == tight for estimate, cost in judged.values()), \
        f"{'tight, each certain step counted once' if tight else 'loose by the step the bound costs'}: {judged}"


def test_a_drive_lands_within_its_band_and_the_steps_and_worlds_advance_along_the_path(tmp_path):
    """THE COURIER'S LANDING BAND (#901), probed on the plan it places. Each step of the joint plan opens where
    the step before it lands, a drive lands half a minute after it opens at the earliest and a minute after
    the plan's latest so far at the latest, and a pick or a drop lands at once; so the six drives land at six
    distinct instants, the plan's last step lands between three and six minutes after the root, and every
    possible world holds over the period its step's two ends say (a-landing-is-a-band-and-a-world-holds-over-a-
    period). ADOPTED, each committed step is believed from its opening to its latest landing plus the
    patience, with `landsWithinS` the band's least and `answeredWithinS` the window's whole length. The
    world answering the drive changes none of it: the band is the courier's declaration, and the van being
    there forty-five seconds on is inside it."""
    lane = _pass(pose(tmp_path, "yard", **YARD))
    placed = rows(lane.imaginarium, _PLACED_Q, (), want=L + JOINT)
    assert len(placed) == 10
    least = {"Drive": DRIVE_LEAST_S, "Pick": 0, "Drop": 0}
    most = {"Drive": DRIVE_MOST_S, "Pick": 0, "Drop": 0}
    opens, latest = NOW, NOW
    landings = []
    for r in placed:
        action, nb, la, na = _local(r["a"]), _dt(r["nb"]), _dt(r["la"]), _dt(r["na"])
        assert nb == opens, f"a step opens where the one before it lands: {action} {nb} against {opens}"
        assert la == nb + timedelta(seconds=least[action]) and na == latest + timedelta(seconds=most[action]), \
            f"the band, summed along the path: {action} opens {nb}, lands {la}, latest {na}"
        assert (_dt(r["ws"]), _dt(r["we"])) == (la, na), "the world a step reaches holds over the period the step's two ends say"
        if action == "Drive":
            landings.append(la)
        opens, latest = la, na
    assert len(landings) == len(set(landings)) == 6, f"six drives, six distinct landings: {landings}"
    assert (opens, latest) == (NOW + timedelta(minutes=3), NOW + timedelta(minutes=6)), "the plan's last step lands between three and six minutes out"
    assert len(lane.bus.commands) == 1, "the pass takes the first drive, which has not landed when the pass ends"
    windows = rows(lane.beliefs, _WINDOWS_Q, ())
    assert len(windows) == 10, "every step of the adopted plan is a belief over its window"
    for w in windows:
        length, within, by = (_dt(w["e"]) - _dt(w["s"])).total_seconds(), float(w["within"]), float(w["by"])
        assert within in (0.0, float(DRIVE_LEAST_S)) and by == length and length > PATIENCE_S, f"a window is its step's band plus the patience: {w}"
    assert sum(1 for w in windows if float(w["within"]) == DRIVE_LEAST_S) == 6 and len({w["s"] for w in windows}) == 7, \
        "six drives land within the least; a pick or a drop opens where its drive landed"


#  PARCEL B ARRIVES MID-WALK (#905). Courier A knows parcel B a parcel and nothing else of it — a parcel at no
#  position and owed nowhere conforms to `courier:delivered` — so the first passes see parcel A astray alone
#  and van A walks a plan for it; between two passes the test writes into the state where parcel B stands and
#  where it is owed, as a consignment arriving at the depot would be written.
ARRIVING = dict(vans=YARD["vans"], parcels={"parcel_a": ((0, 1), (0, 3)), "parcel_b": (None, None)})
#  THE CORRIDOR, B ARRIVING: van A drives parcel A along the second row through (2, 1), and parcel B arrives at
#  (2, 2) owed at (2, 0), so van B's road runs down the third column through the position van A is crossing.
CORRIDOR_ARRIVING = dict(vans=CORRIDOR["vans"], parcels={"parcel_a": ((1, 1), (3, 1)), "parcel_b": (None, None)},
                         budget=CORRIDOR_BUDGET)
_PUBLISHED_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?step ?a ?van ?parcel ?tx ?ty ?nb WHERE { GRAPH $p { ?step a execution:Step ; planning:fills ?a ; execution:notBefore ?nb .
  OPTIONAL { ?step courier:van ?van } OPTIONAL { ?step courier:parcel ?parcel }
  OPTIONAL { ?step courier:toX ?tx ; courier:toY ?ty } } }
ORDER BY ?nb ?step"""
#  WHEN A STEP WAS TAKEN, off its act, and when its plan placed it: due, and to land.
_ACT_Q = """SELECT ?taken ?due ?lands WHERE { GRAPH ?i { ?act execution:of $step ; execution:taken true ; execution:takenAt ?taken }
  GRAPH ?p { $step execution:notBefore ?due ; execution:landsAt ?lands } }"""
_ACTS_OF_Q = "SELECT ?act WHERE { GRAPH ?g { ?act execution:of $step } }"
_ADOPTED_Q = "SELECT ?at WHERE { GRAPH ?g { $i execution:adoptedAt ?at } }"


def _parcel_b(at: tuple[int, int], owed: tuple[int, int]):
    """Parcel B ARRIVING at `at`, owed at `owed`, written into the state as a consignment arriving at the
    depot would be: what `_arrival` writes for soft commitment's first trigger."""
    def arrive(lane, walking):
        (state,) = {r["g"] for r in rows(lane.beliefs, f"SELECT ?g WHERE {{ GRAPH ?g {{ <{L}parcel_b> a <{COURIER}Parcel> }} }}", ())}    # courier A's state document
        x, y = _road(*at)
        ox, oy = _road(*owed)
        update(lane.beliefs, f"""PREFIX courier: <http://example.org/orexis/courier#>
INSERT DATA {{ GRAPH <{state}> {{ <{L}parcel_b> courier:x {x} ; courier:y {y} ; courier:destination <{L}door_arriving> .
                               <{L}door_arriving> courier:x {ox} ; courier:y {oy} }} }}""")
        hash_named_graph(lane.beliefs, state)
        return [state]
    return arrive


def _arrival(world: Path, arrive, *, after: int = 2, limit: int = 160) -> dict:
    """Courier A over `world`, ten seconds of the world's time between passes, until van A's plan has had
    `after` steps answered; then, at the next instant and before the simulator reports, a belief ARRIVES —
    `arrive(lane, walking)` writes it and answers the graphs it wrote, which are said written, or puts a
    thing where the world will report it and answers none — so the step van A's walk took in the pass before
    is still in flight when the arrival is planned for. Then on until no intention stands. What happened,
    in order: every step taken with where the vans stood, every verdict, every intention resolved, every
    plan published, every reconsideration, every search said, and what the first search after the arrival
    weighed."""
    lane = Lane(world)
    seen: dict = {"events": [], "trace": [], "searched": [], "planned": []}

    def heard(kind):
        def handler(event):
            seen["events"].append((kind, event))
            if kind == "taken":
                at = _at(lane.beliefs)
                seen["trace"].append((_local(event.step), at.get("van_a"), at.get("van_b"), _together(lane.beliefs)))
            return []
        return handler
    lane.executor.step_taken.connect(heard("taken"))
    lane.executor.step_answered.connect(heard("answered"))
    lane.executor.intention_resolved.connect(heard("resolved"))
    lane.planner.plan_published.connect(heard("published"))
    lane.planner.reconsidered.connect(heard("reconsidered"))
    lane.planner.rerooted.connect(heard("rerooted"))
    lane.planner.searched.connect(lambda e: seen["searched"].append(e) or [])
    lane.planner.planned.connect(lambda e: seen["planned"].append(e) or [])
    outcome = lane.tick()
    for n in range(limit):
        if "arrived" in seen and "weighed" not in seen["arrived"] and len(seen["searched"]) > len(seen["before"]):
            #  WHAT THE PASS THE ARRIVAL WAS SEARCHED FOR IN WEIGHED AND SPENT, before a later pass re-roots it away.
            im = lane.imaginarium
            seen["arrived"].update(weighed=_weighed(im), spent=_spent(im), impossible=_impossible(im), planned=seen["planned"][-1])
        if "arrived" in seen and (outcome != UNFINISHED or not lane.executor.standing()):
            break
        lane.at += timedelta(seconds=CADENCE_S)
        if "arrived" not in seen and sum(1 for k, e in seen["events"] if k == "answered" and e.landed) >= after:
            seen["before"] = list(seen["searched"])
            (walking,) = lane.executor.standing()
            seen["arrived"] = {"at": lane.at, "events": len(seen["events"]), "intention": walking.uri,
                               "adopted": rows(lane.beliefs, _ADOPTED_Q, (), i=walking.uri)[0]["at"], "head": walking.at}
            written = arrive(lane, walking)
            if written:
                lane.runtime.wrote(written)
        outcome = lane.tick()
    seen["arrived"]["searched"] = seen["searched"][len(seen["before"]):]
    seen.update(lane=lane, beliefs=lane.beliefs, passes=n + 1)
    return seen


def _published(seen) -> dict[str, list[tuple]]:
    """Per want, the steps of every plan published for it after the arrival, in the order placed."""
    out: dict[str, list] = {}
    for kind, event in seen["events"][seen["arrived"]["events"]:]:
        if kind == "published":
            out[_local(event.want)] = [(_local(r["a"]), _local(r.get("van")), _local(r.get("parcel")), _place(r), _dt(r["nb"]))
                                        for r in rows(seen["beliefs"], _PUBLISHED_Q, (), p=event.plan)]
    return out


def _of(seen, kind: str, since_arrival: bool = True) -> list:
    return [e for k, e in seen["events"][seen["arrived"]["events"] if since_arrival else 0:] if k == kind]


def _in_flight(seen):
    """The step in flight when the belief arrived, and the instant it lands: its `landsAt`, shifted by how
    late it was taken — the executor's own reading."""
    arrived = seen["arrived"]
    (act,) = rows(seen["beliefs"], _ACT_Q, (), step=arrived["head"])
    assert _dt(act["taken"]) < arrived["at"], "the step reconsidered around was in flight when the belief arrived"
    return arrived["head"], _dt(act["lands"]) + max(timedelta(0), _dt(act["taken"]) - _dt(act["due"]))


def _ended_after_its_step_in_flight(seen, head, plan=None, want=None) -> None:
    """The step in flight is answered by the world, never cancelled; the reconsidered intention ends after
    it, `superseded`; the replacement's first step is taken only then; and none of the untaken steps of
    the intention that ended is ever taken."""
    arrived, order = seen["arrived"], seen["events"][seen["arrived"]["events"]:]
    answered = next(i for i, (k, e) in enumerate(order) if k == "answered" and e.step == head)
    assert order[answered][1].landed, "the step in flight is answered by the world, never cancelled"
    ended = next(i for i, (k, e) in enumerate(order) if k == "resolved" and e.intention == arrived["intention"])
    assert order[ended][1].outcome == "superseded" and answered < ended, "the intention ends AFTER its step in flight"
    first = next(i for i, (k, e) in enumerate(order) if k == "taken" and (e.step.startswith(plan) if plan else _local(e.want) == want))
    assert ended < first, "the replacement's first step is taken once the step in flight has landed"
    untaken = [s for s in rows(seen["beliefs"], "SELECT ?s WHERE { GRAPH ?g { $i execution:step ?s } }", (), i=arrived["intention"])
               if not rows(seen["beliefs"], _ACTS_OF_Q, (), step=s["s"])]
    assert untaken, "the reconsidered intention had untaken steps, and none of them was ever taken"
    assert sorted(e.outcome for e in _of(seen, "resolved")) == ["done", "superseded"]


@pytest.mark.parametrize("name, layout, place, owed, candidates, worlds, impossible, at", [
    ("yard", ARRIVING, (3, 1), (3, 3), 157, 125, {},
     {"van_a": (0, 3), "parcel_a": (0, 3), "van_b": (3, 3), "parcel_b": (3, 3)}),
    ("corridor", CORRIDOR_ARRIVING, (2, 2), (2, 0), 127, 102, {CONSTRAINT: 7},
     {"van_a": (3, 1), "parcel_a": (3, 1), "van_b": (2, 0), "parcel_b": (2, 0)}),
])
def test_a_parcel_arriving_mid_walk_reopens_the_walking_want_and_the_joint_plan_replaces_its_untaken_steps_after_the_step_in_flight(
        tmp_path, name, layout, place, owed, candidates, worlds, impossible, at):
    """SOFT COMMITMENT'S ONE TRIGGER, AND THE HARD GRAIN UNDER IT (#905, commitment). Van A has walked two steps
    of its plan for parcel A — a drive and the pick — and its next drive is IN FLIGHT, told to the van and
    not yet reported, when parcel B arrives where van B can reach it: the constraint couples B to A, so the
    cluster is both parcels and it REOPENS the walking want. The coupled want is searched from the ground in
    which the step in flight has landed — the joint plan's first step opens exactly there. The joint plan
    does not BEGIN with van A's untaken steps, so van A's intention ends AFTER its step in flight,
    `superseded`, and the joint plan is adopted whole. The step in flight is never cancelled: the world
    answers it, and only then does the intention resolve. On the corridor van B's road crosses (2, 1) as van
    A leaves it, and walked, the vans share no position at any act; both parcels are delivered. The
    re-search costs what the coupled search from that ground costs, measured."""
    seen = _arrival(pose(tmp_path, name, **layout), _parcel_b(place, owed))
    head, landing = _in_flight(seen)
    (reconsidered,) = _of(seen, "reconsidered")
    assert (reconsidered.step, _local(reconsidered.want), _local(reconsidered.by)) == (head, A, JOINT)
    published = _published(seen)
    assert list(published) == [JOINT], f"one plan, the coupled want's, published whole: {published}"
    assert published[JOINT][0][4] == landing, \
        f"the joint plan begins where the step in flight lands, not at the present: {published[JOINT][0]} against {landing}"
    assert {van for _, van, _, _, _ in published[JOINT] if van} == {"van_a", "van_b"}, "the joint plan drives both vans"
    _ended_after_its_step_in_flight(seen, head, want=JOINT)
    assert [t for t in seen["trace"] if t[3]] == [], f"walked, two vans at one position at no act: {seen['trace']}"
    assert _at(seen["beliefs"]) == at, "both parcels delivered"
    arrived = seen["arrived"]
    searched = {_local(e.want): e.weighed for e in arrived["searched"]}
    assert (searched, arrived["weighed"].get(JOINT), arrived["impossible"]) == ({JOINT: candidates}, worlds, impossible), \
        f"the coupled re-search, measured: {searched} candidates, {arrived['weighed']} worlds, {arrived['impossible']} impossible"


def test_a_joint_plan_that_begins_with_the_walking_intentions_untaken_steps_leaves_it_standing(tmp_path):
    """WHERE THE JOINT PLAN AGREES, NOTHING IS ENDED. Parcel B arrives at the position van B stands at, so van B
    can pick it without moving and van A's remaining drive and drop are what the joint plan does first —
    compared by the action each fills and the values it takes, never by node. Van A's intention stands
    untouched: adopted at the instant it was, never reconsidered, and done when its drop lands; what is
    published for the coupled want is the part that is NEW, van B's five steps, opening after van A's last
    kept step lands in the joint plan. Both parcels are delivered and no intention ends but `done`."""
    seen = _arrival(pose(tmp_path, "agree", **ARRIVING), _parcel_b((3, 0), (3, 3)))
    arrived, beliefs = seen["arrived"], seen["beliefs"]
    assert _of(seen, "reconsidered") == []
    published = _published(seen)
    assert list(published) == [JOINT] and [(a, v, p, to) for a, v, p, to, _ in published[JOINT]] == [
        ("Pick", "van_b", "parcel_b", None), ("Drive", "van_b", None, (3, 1)), ("Drive", "van_b", None, (3, 2)),
        ("Drive", "van_b", None, (3, 3)), ("Drop", None, "parcel_b", None)], f"only the new part is adopted: {published}"
    _, landing = _in_flight(seen)
    assert published[JOINT][0][4] == landing + timedelta(seconds=DRIVE_LEAST_S), \
        "the new part opens where the joint plan put it: after van A's kept drive, which opens where the step in flight lands"
    assert rows(beliefs, _ADOPTED_Q, (), i=arrived["intention"])[0]["at"] == arrived["adopted"], "van A's intention, adopted when it was"
    assert {(_local(e.want), e.outcome) for e in _of(seen, "resolved")} == {(A, "done"), (JOINT, "done")}, "no intention ended but done"
    assert [t for t in seen["trace"] if t[3]] == []
    assert _at(beliefs) == {"van_a": (0, 3), "parcel_a": (0, 3), "van_b": (3, 3), "parcel_b": (3, 3)}


#  A PEER'S VAN (#921, #922): van A and parcel A alone, the parcel owed at (2, 2) so three drives remain after
#  the pick and more than one way runs there, and VAN B, a peer's — its driver nobody here plays, so the
#  drive's own filter refuses it (#903) — far off on the road, believed nowhere until a belief says where.
PEER = dict(vans={"a": (0, 0)}, parcels={"parcel_a": ((0, 1), (2, 2))}, drives="a")
#  WHERE VAN B IS FORESEEN, as a forecast laid in the beliefs: a belief holding from an instant ahead.
PEER_GRAPH = "http://example.org/orexis/graph/forecast/courier_a/van_b"
_PLAN_OF_Q = "SELECT ?p WHERE { GRAPH ?g { $i execution:adopts ?p } }"


def _next_place(beliefs, walking) -> tuple[int, int]:
    """Where van A's plan drives to first after its step in flight — the first untaken drive's, in the yard."""
    (plan,) = rows(beliefs, _PLAN_OF_Q, (), i=walking.uri)
    steps = [(r["step"], _local(r["a"]), _place(r)) for r in rows(beliefs, _PUBLISHED_Q, (), p=plan["p"])]
    at = next(i for i, (step, _, _) in enumerate(steps) if step == walking.at)
    return next(to for _, action, to in steps[at + 1:] if action == "Drive")


def _van_b(place=None, *, observed: bool = False):
    """VAN B, said to stand at `place` — or, where none is named, at the position van A's plan drives to first
    after its step in flight: OBSERVED, put there by the world, so van A's receiver reports it at the next
    reading and the courier's rules make it a belief (#922); or FORESEEN, a forecast holding from ten seconds
    on, as #923 would lay a peer's word about its route — laid where it begins (#987). What is held is what
    the agent does with such a belief once it has it."""
    def arrive(lane, walking):
        where = place or _next_place(lane.beliefs, walking)
        arrive.place = where
        if observed:
            lane.place("van_b", where)
            return []
        x, y = _road(*where)
        update(lane.beliefs, f"""PREFIX courier: <http://example.org/orexis/courier#>
INSERT DATA {{ {entry(lane.beliefs, PEER_GRAPH, FORECAST, OREXIS + "Received", L + AGENT, start=lane.at + timedelta(seconds=10))}
  GRAPH <{PEER_GRAPH}> {{ <{L}van_b> courier:x {x} ; courier:y {y} }} }}""")
        hash_named_graph(lane.beliefs, PEER_GRAPH)     # a writer stamps what it wrote, as every writer of a belief does
        return [PEER_GRAPH]
    return arrive


@pytest.mark.parametrize("observed", [False, True], ids=["foreseen", "observed"])
def test_a_belief_that_makes_the_walking_plans_next_world_impossible_reopens_it_after_the_step_in_flight(tmp_path, observed):
    """SOFT COMMITMENT'S SECOND TRIGGER (#921). Van A has driven to parcel A and picked it, and its next drive
    is IN FLIGHT, when a belief arrives that van B will stand — or stands — at the position van A's plan
    drives to next. No want arrives and nothing couples; what changed is the ground. The pass holds the
    walking plan to the grounds as now laid, and the world after the next drive holds two vans at one
    position, which the constraint makes impossible: so the walking want REOPENS ITSELF, searched from the
    ground its step in flight lands in; the intention ends AFTER that step, `superseded`, and the new plan
    opens where it lands and never drives onto van B's position. OBSERVED, van B is put there by the world
    and van A's receiver reports it, as #922 asked: the constraint alone keeps the plan out, whatever was or
    was not said. Parcel A is delivered."""
    arrive = _van_b(observed=observed)
    seen = _arrival(pose(tmp_path, "peer", **PEER), arrive)
    arrived, beliefs, blocked = seen["arrived"], seen["beliefs"], arrive.place
    head, landing = _in_flight(seen)
    (reconsidered,) = _of(seen, "reconsidered")
    assert (reconsidered.step, _local(reconsidered.want), _local(reconsidered.by)) == (head, A, A), "the walking want reopens itself"
    published = _published(seen)
    assert list(published) == [A], f"one plan, for the same want, published whole: {published}"
    assert published[A][0][4] == landing, f"the new plan opens where the step in flight lands: {published[A][0]} against {landing}"
    assert ("Drive", "van_a", None, blocked) not in [s[:4] for s in published[A]], f"the new plan never drives onto {blocked}: {published[A]}"
    (plan,) = [e.plan for k, e in seen["events"][arrived["events"]:] if k == "published"]
    _ended_after_its_step_in_flight(seen, head, plan=plan)
    walked = seen["trace"][len([k for k, _ in seen["events"][:arrived["events"]] if k == "taken"]):]
    assert walked and all(van_a != blocked for _, van_a, _, _ in walked), f"van A never stands at {blocked}: {walked}"
    assert [t for t in seen["trace"] if t[3]] == [], f"walked, two vans at one position at no act: {seen['trace']}"
    assert _at(beliefs)["parcel_a"] == (2, 2), "parcel A delivered"
    assert (blocked, [s[:4] for s in published[A]]) == ((2, 1), [
        ("Drive", "van_a", None, (1, 2)), ("Drive", "van_a", None, (2, 2)), ("Drop", None, "parcel_a", None)]), \
        f"van A was driving along the second row; it turns down the second column, found by the search and decided by nobody: {published[A]}"
    searched = {_local(e.want): e.weighed for e in arrived["searched"]}
    assert (searched, arrived["weighed"].get(A), arrived["impossible"]) == ({A: 15}, 12, {CONSTRAINT: 1}), \
        f"the re-search from the landing ground, measured: {searched} candidates, {arrived['weighed']} worlds, {arrived['impossible']} impossible"


def test_a_belief_that_touches_nothing_the_walking_plans_worlds_read_reopens_nothing(tmp_path, caplog):
    """THE SECOND TRIGGER ASKS, AND ANSWERS NO. Van B is foreseen at (3, 0), a position van A's plan enters at no
    step: a belief has arrived, so the walking plan's untaken steps are replayed and weighed for the
    constraint, and none of their worlds is impossible. The walking want is neither searched nor
    reconsidered, and van A's intention, adopted when it was, walks on to `done`."""
    with caplog.at_level(logging.DEBUG, logger="planner"):
        seen = _arrival(pose(tmp_path, "aside", **PEER), _van_b((3, 0)))
    arrived = seen["arrived"]
    asked = [r.getMessage() for r in caplog.records if "untaken steps foreseen" in r.getMessage() and A in r.getMessage()]
    assert asked, "the walking plan was held to the grounds the belief changed"
    assert _of(seen, "reconsidered") == []
    assert arrived["searched"] == [], "the walking want is not searched again"
    assert _published(seen) == {}
    assert rows(seen["beliefs"], _ADOPTED_Q, (), i=arrived["intention"])[0]["at"] == arrived["adopted"]
    assert {(_local(e.want), e.outcome) for e in _of(seen, "resolved")} == {(A, "done")}
    assert _at(seen["beliefs"])["parcel_a"] == (2, 2)


def test_two_vans_at_one_position_as_reported_is_a_contradiction_said_and_never_a_want(tmp_path, caplog):
    """A CONSTRAINT VIOLATED IN THE PRESENT IS A CONTRADICTION, NOT A WANT. Both vans' fixes report (0, 0): the
    constraint, weighed in the present ground, yields a witness per van with the other van offending, and
    nothing is minted from it, since the derivation reads desires alone; the pass says so, a warning naming
    the constraint and its rows, and `Planner.contradictions` answers the same rows to whoever asks.
    Onboarding refuses such a world only where it is POSED, and nothing here poses a van, so it refuses
    nothing: what the fixes report is the agent's to say, in its log (the posed refusal is the driver
    world's). BESIDE IT THE TWO PARCELS ARE ONE COUPLED WANT, and from one position the joint delivery is
    thirteen steps whose product no budget tried pays — Exhausted at 128, measured — which is the record's
    seam on the product's budget; its search marks six worlds impossible, the worlds that part the vans and
    bring them together again at another position, since nothing compares a world to its parent."""
    together = pose(tmp_path, "together", **TOGETHER)
    with caplog.at_level(logging.WARNING, logger="planner"):
        lane = _pass(together, budget=128)
    im = lane.imaginarium
    assert {(_local(r["x"]), _local(r["cell"])) for r in rows(im, _WITNESSES_Q, (), d=COURIER + CONSTRAINT)} == \
        {("van_a", "van_b"), ("van_b", "van_a")}, "the constraint is judged in the present: a row per van, the other van offending"
    said = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING and "constraint" in r.getMessage()]
    assert len(said) == 1 and CONSTRAINT in said[0] and "van_a" in said[0] and "van_b" in said[0], said
    assert _wants(im) == {JOINT: "every_parcel_delivered"}, "nothing is minted from a constraint: " + str(_wants(im))
    assert _plans(im) == {JOINT: ("Exhausted", 0)}, "the product's budget: the record's seam, pinned"
    assert _weighed(im)[JOINT] == 83 and _spent(im)[JOINT] == 128, f"measured: {_weighed(im)} {_spent(im)}"
    assert _impossible(im) == {CONSTRAINT: 6}, "the worlds that meet again at another position: " + str(_impossible(im))
    _possible(im, JOINT)
    (found,) = lane.planner.contradictions(lane.at)
    assert _local(found[0]) == CONSTRAINT and {(_local(i), _local(o)) for i, _, _, o in found[1]} == {("van_a", "van_b"), ("van_b", "van_a")}
    assert reading.contradicted(together, AGENT) == [], "nothing is posed, so onboarding has nothing to refuse"
    assert _pass(pose(tmp_path, "yard", **YARD)).planner.contradictions(NOW) == [], "the yard as the fixes report it is possible"


#  A PEER'S VAN CROSSING THE POSITION AHEAD (#920, #568). Van A at (0, 1) carries parcel A, owed at (3, 1), so its
#  shortest chain drives (1, 1), (2, 1), (3, 1) and drops; van B is a PEER'S, its driver nobody here plays, so
#  no move of it is admitted (#903's filter), seen at (2, 3) by van A's receiver, and its route down the third
#  column is laid as forecasts, as speech will lay a peer's route ahead (#568). The constraint stays the
#  world's own: van B is a van.
CROSSING = dict(vans={"a": (0, 1), "b": (2, 3)}, parcels={"parcel_a": ("van_a", (3, 1))}, drives="a")
#  VAN B'S ROUTE, from the instant each position holds: the first is the present, as the receiver reports it. It
#  stands at (2, 1) from a minute to a minute and a half.
CROSSING_ROUTE = [(0, (2, 3)), (30, (2, 2)), (60, (2, 1)), (90, (2, 0))]
#  THE SAME WITH VAN B STANDING at (2, 1) from a minute to two and a half before it drives on.
STANDING_ROUTE = [(0, (2, 3)), (30, (2, 2)), (60, (2, 1)), (150, (2, 0))]
#  THE PLAN'S STEPS IN THE ORDER THEY ARE TAKEN, each with where a drive goes and the instants it may be taken
#  and lands at the earliest.
_ORDERED_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?a ?tx ?ty ?nb ?la WHERE {
  GRAPH ?p { ?p a planning:Plan ; planning:for $want . ?step a execution:Step ; execution:partOf ?p ; planning:fills ?a ;
             execution:notBefore ?nb ; execution:landsAt ?la . OPTIONAL { ?step courier:toX ?tx ; courier:toY ?ty } } }
ORDER BY ?nb ?la"""
#  THE WAITS A WANT'S SEARCH WEIGHED, and how many repeated a world already weighed.
_WAITS_Q = """
SELECT (COUNT(?x) AS ?weighed) (COUNT(?seen) AS ?repeated) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for $want ; planning:weighs ?u .
               ?u planning:by?/planning:fills planning:Wait . OPTIONAL { ?x planning:repeats ?seen } } }"""


def _route(route):
    """Van B's route laid as forecasts, one graph per position after the first, each from its instant — the
    peer's word about where it will be: received, and believed as it stands; each supersedes by key where
    it is laid (#988)."""
    def lay(beliefs) -> None:
        for n, (offset, place) in enumerate(route[1:], start=1):
            graph = f"http://example.org/orexis/graph/route/van_b/{n}"
            x, y = _road(*place)
            update(beliefs, f"""INSERT DATA {{
  GRAPH <{graph}> {{ <{L}van_b> <http://example.org/orexis/courier#x> {x} ; <http://example.org/orexis/courier#y> {y} . }}
  {entry(beliefs, graph, FORECAST, OREXIS + "Received", L + AGENT, start=NOW + timedelta(seconds=offset))} }}""")
            hash_named_graph(beliefs, graph)
    return lay


def _ordered(im, want: str) -> list[tuple]:
    """The plan's steps in order as (action, where to, seconds after the pass it may be taken, seconds after
    the pass it lands at the earliest)."""
    return [(_local(r["a"]), _place(r), (_dt(r["nb"]) - NOW).total_seconds(), (_dt(r["la"]) - NOW).total_seconds())
            for r in rows(im, _ORDERED_Q, (), want=L + want)]


def _waits(im, want: str) -> tuple[int, int]:
    """(waits weighed, of them repeats) in `want`'s search."""
    (r,) = rows(im, _WAITS_Q, (), want=L + want)
    return int(r["weighed"]), int(r["repeated"])


def test_a_van_waits_for_a_peers_van_to_clear_the_position_its_route_crosses(tmp_path):
    """WAIT, THEN DRIVE. Van A, a cell short of (2, 1) at half a minute, would land on it straight on at a
    minute, when van B does — a world the constraint makes impossible — so it waits for the next ground,
    where van B has moved onto (2, 1), and drives in landing at a minute and a half, when van B has gone on
    to (2, 0). Four acts and a tenth spent against an estimate of four: the tenth is the wait,
    `planning:Wait`, which no document of this world names (#920)."""
    lane = _pass(pose(tmp_path, "crossing", **CROSSING), lay=_route(CROSSING_ROUTE))
    im = lane.imaginarium
    assert _at(lane.beliefs)["van_b"] == (2, 3), "van B where van A's receiver has it"
    assert _plans(im) == {A: ("Satisfied", 5)}
    assert _ordered(im, A) == [("Drive", (1, 1), 0, 30), ("Wait", None, 30, 60), ("Drive", (2, 1), 60, 90),
                               ("Drive", (3, 1), 90, 120), ("Drop", None, 120, 120)], _ordered(im, A)
    assert _costs(im) == {A: 4.1} and _remaining(im)[A] == 4.0
    assert (_spent(im)[A], _weighed(im)[A]) == (34, 30), f"measured: {_spent(im)} {_weighed(im)}"
    assert _impossible(im) == {CONSTRAINT: 2}
    assert _waits(im, A) == (4, 1), "one wait of four repeated a world: " + str(_waits(im, A))
    _possible(im, A)


def test_a_van_waits_out_a_peer_standing_on_the_position_ahead(tmp_path):
    """A wait lands where the next ground begins, so one wait spans the whole of van B's standing: a drive, a
    wait to the minute van B arrives, a wait to the instant it leaves, two drives and the drop."""
    im = _pass(pose(tmp_path, "standing", **CROSSING), lay=_route(STANDING_ROUTE)).imaginarium
    assert _plans(im) == {A: ("Satisfied", 6)}, _plans(im)
    assert _ordered(im, A) == [("Drive", (1, 1), 0, 30), ("Wait", None, 30, 60), ("Wait", None, 60, 150),
                               ("Drive", (2, 1), 150, 180), ("Drive", (3, 1), 180, 210),
                               ("Drop", None, 210, 210)], _ordered(im, A)
    assert _costs(im) == {A: 4.2}
    assert (_spent(im)[A], _weighed(im)[A]) == (39, 31), f"measured: {_spent(im)} {_weighed(im)}"
    assert _impossible(im) == {CONSTRAINT: 2}
    assert _waits(im, A) == (4, 1), str(_waits(im, A))
    _possible(im, A)
