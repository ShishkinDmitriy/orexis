"""The simulator plays a world's simulated systems from the world's own words.

It is NOT a pretend board. A board is told its topics and knows nothing else; the simulator is the
environment the agents act in — the bed drying, the pump pouring, the heater warming — so it reads
the world as an agent boots it (`agent.runtime.world_of`) and takes every fact from there — the
world graph and the society graph, both public, and never the deployment graph, since the broker's
address reaches it as environment, as an agent's does:

- which systems to play: every one marked `sim:simulatedBy`, and a sensor's starting reading and
  bounds from its `sim:Model` (the world graph);
- where each speaks: the topic a sensor publishes on and the topic an actuator listens to, by the
  patterns of the MQTT4SSN filters that match them (the society onboarding derived beside the
  society); how often a sensor reports, from its `ssn-system:Frequency`;
- the physics: a subject's soil dries `climate:driesPerDay`; a dose of `dose_ml` on a valve that
  `actuation:actuates` a subject raises the property it `actuation:actuatesProperty` by the litres
  over the subject's `climate:litresPerFraction`; a heating of `heat_s` on a heater that
  `climate:warms` a subject raises the property it `climate:warmsProperty` at `climate:degreesPerHour`
  for as long as it runs.

A topic is a board's, and a board publishes ONE document on it at its heartbeat: every sensor it
hosts, each number at the pointer the world binds the sensor to (`sensing:readingPointer`, `/value`
where it binds none), which is what sensing reads it by. Time is the one timeline, `clock.now()`; `step` is called with the present and
advances everything from the last step.

THE NUMBER PUBLISHED IS THE INSTRUMENT'S, NOT THE MODEL'S (#879). The physics moves only what a
flow or a running heater moves, so a model nothing touches — the air of a greenhouse nobody heats,
a probe clamped at its bound — reads the same to the fourth place at every cadence, and sensing,
whose stuck detector is premised on a live instrument's count moving by at least one within a few
readings, said such a sensor stuck an hour into its world. So each published number is the model's
reading with the instrument's noise: a draw within the model's `sim:jitter` either way (`JITTER`
where it states none, one count of the `PLACES` the simulator publishes to), rounded as a board
would round, and never the number this sensor published last — the premise the detector states,
held to rather than left to a draw that could repeat. The draw is seeded, so a test and a run are
reproducible, and the noise is the instrument's alone: the model's reading is untouched by it, and
the model's bounds bound the reading, not the number.

A VAN IS PLAYED AS A BODY THAT MOVES ON COMMAND (#1002): a `courier:Van` marked `sim:simulatedBy`, told
`{"to": {"x": <column>, "y": <row>}}` on the topic it listens to, is on that cell `sim:delayS` later, and
the position fix it hosts — two sensors observing `courier:Column` and `courier:Row` — reports the
coordinates from then on. The grid is infinite, and a van refuses only a cell that is no neighbour of the
one it stands on; the cells the world's agents know are read off it for where out of range is pretended to
be. So the pilot never writes its own van's cell, and there is a true position for a contact to be played from.

A CONTACT IS PLAYED FROM THE TRUE POSITIONS (#1003): a `sosa:Sample` a van carries, with two sensors
observing `courier:RelativeColumn` and `courier:RelativeRow`, reports the vector from the carrying van
to what it stands for - the peer it `isSampleOf`, or, standing for nothing named, the nearest thing no
receiver of that van identifies - while that is within the sensors' model's `sim:radius`, |dx| + |dy|
in cells; beyond it, a vector landing one cell past the far corner of the known cells, where no agent knows one.
A thing's true position is its fix's if it has one, else where its model says it stands (`sim:x`, `sim:y`).
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta

from agent import clock
from agent.runtime import world_of
from agent.sensing.pipeline import DEFAULT_POINTER
from agent.store import graphs_of, rows

log = logging.getLogger("simulation")

BELIEF = "http://example.org/orexis#BeliefGraph"
SIM = "http://example.org/orexis/sim#"
CLIMATE = "http://example.org/orexis/climate#"
ACTUATION = "http://example.org/orexis/actuation#"
SENSING = "http://example.org/orexis/sensing#"
COURIER = "http://example.org/orexis/courier#"
MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"
_SECONDS = {"SEC": 1, "MIN": 60, "HR": 3600, "HUR": 3600, "DAY": 86400}

#  WHAT A BOARD WOULD PUBLISH: the decimal places a number is rounded to, and how far the published
#  number strays from the model's reading either way where the model states no `sim:jitter` — one
#  count of those places, the least a live instrument moves by.
PLACES = 4
JITTER = 10.0 ** -PLACES

_SENSORS_Q = f"""
SELECT ?sensor ?subject ?property ?start ?lo ?hi ?jitter ?pattern ?every ?unit ?pointer WHERE {{
  ?sensor a sosa:Sensor ; <{SIM}simulatedBy> ?model ; sosa:isHostedBy ?subject ; sosa:observes ?property ;
          <{MQTT4SSN}observesTopic> ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern .
  FILTER(!CONTAINS(?pattern, "+") && !CONTAINS(?pattern, "#"))
  OPTIONAL {{ ?model <{SIM}initialValue> ?start }}
  OPTIONAL {{ ?model <{SIM}minValue> ?lo }} OPTIONAL {{ ?model <{SIM}maxValue> ?hi }}
  OPTIONAL {{ ?model <{SIM}jitter> ?jitter }}
  OPTIONAL {{ ?sensor <{SENSING}readingPointer> ?pointer }}
  OPTIONAL {{ ?sensor ssn-system:hasSystemCapability/ssn-system:hasSystemProperty ?f .
             ?f a ssn-system:Frequency ; schema:value ?every ; schema:unitCode ?unit }} }}
ORDER BY ?sensor"""

_ACTUATORS_Q = f"""
SELECT ?actuator ?pattern WHERE {{
  ?actuator <{SIM}simulatedBy> ?model ; <{MQTT4SSN}listensToTopic> ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }} ORDER BY ?actuator"""

_DOSES_Q = f"""
SELECT ?subject ?property ?litres WHERE {{
  $actuator <{ACTUATION}actuates> ?subject ; <{ACTUATION}actuatesProperty> ?property .
  ?subject <{CLIMATE}litresPerFraction> ?litres }}"""

_HEATS_Q = f"""
SELECT ?subject ?property ?rate WHERE {{
  $actuator <{CLIMATE}warms> ?subject ; <{CLIMATE}warmsProperty> ?property ; <{CLIMATE}degreesPerHour> ?rate }}"""

_DRIES_Q = f"""SELECT ?subject ?rate WHERE {{ ?subject <{CLIMATE}driesPerDay> ?rate }}"""

#  EVERY VAN PLAYED, the two sensors of its position fix and how long a drive takes to show (#1002): a van
#  told a cell is there `sim:delayS` later, and its fix reports the cell's coordinates from then on.
_VANS_Q = f"""
SELECT ?van ?column ?row ?delay WHERE {{
  ?van a <{COURIER}Van> ; <{SIM}simulatedBy> ?model .
  ?column a sosa:Sensor ; sosa:isHostedBy ?van ; sosa:observes <{COURIER}Column> .
  ?row a sosa:Sensor ; sosa:isHostedBy ?van ; sosa:observes <{COURIER}Row> .
  OPTIONAL {{ ?model <{SIM}delayS> ?delay }} }}"""

#  THE CELLS THE WORLD'S AGENTS KNOW: the grid is infinite and a cell any pair of coordinates, so a van is
#  driven to any neighbour of the one it stands on, on the road or off it, and what keeps it on the road is
#  its courier planning over the cells it knows; the cells are read only for where a contact out of range is
#  pretended to be, past the far corner of them, where no agent knows a cell.
_CELLS_Q = f"""SELECT ?x ?y WHERE {{ ?cell a <{COURIER}Cell> ; <{COURIER}x> ?x ; <{COURIER}y> ?y }}"""

#  EVERY CONTACT PLAYED (#1003): the van carrying it, the peer it stands for where it stands for one, its two
#  sensors and how far they see.
_CONTACTS_Q = f"""
SELECT ?contact ?van ?peer ?column ?row ?radius WHERE {{
  ?contact a sosa:Sample ; sosa:isHostedBy ?van .
  ?column a sosa:Sensor ; sosa:isHostedBy ?contact ; sosa:observes <{COURIER}RelativeColumn> ; <{SIM}simulatedBy> ?model .
  ?row a sosa:Sensor ; sosa:isHostedBy ?contact ; sosa:observes <{COURIER}RelativeRow> .
  OPTIONAL {{ ?contact sosa:isSampleOf ?peer }}
  OPTIONAL {{ ?model <{SIM}radius> ?radius }} }} ORDER BY ?contact"""

#  WHERE A THING WITH NO INSTRUMENT STANDS, as its model says: a parked van, a fallen tree.
_POSED_Q = f"""SELECT ?thing ?x ?y WHERE {{ ?thing <{SIM}simulatedBy> ?model . ?model <{SIM}x> ?x ; <{SIM}y> ?y }}"""


class Simulator:
    """The world's simulated systems, their state, and one client on the world's broker."""

    def __init__(self, world, client, now: datetime | None = None, seed: int = 0):
        self.store = world_of(world)
        self.client = client
        self.at = now or clock.now()
        self.rng = random.Random(seed)             # the instruments' noise, reproducible under the seed
        self.sensors: dict[str, dict] = {}
        for r in self._rows(_SENSORS_Q):
            every = float(r["every"]) * _SECONDS.get((r.get("unit") or "").rsplit("/", 1)[-1], 1) if r.get("every") else 60.0
            self.sensors[r["sensor"]] = {
                "subject": r["subject"], "property": r["property"], "topic": r["pattern"],
                "value": float(r.get("start") or 0.0), "every": every, "due": self.at,
                "lo": float(r["lo"]) if r.get("lo") is not None else None,
                "hi": float(r["hi"]) if r.get("hi") is not None else None,
                "jitter": float(r["jitter"]) if r.get("jitter") is not None else JITTER, "last": None,
                "pointer": r.get("pointer") or DEFAULT_POINTER}
        self.listening = {r["pattern"]: r["actuator"] for r in self._rows(_ACTUATORS_Q)
                          if "+" not in r["pattern"] and "#" not in r["pattern"]}
        self.dries = {r["subject"]: float(r["rate"]) for r in self._rows(_DRIES_Q)}
        self.heating: dict[str, datetime] = {}
        #  THE VANS, each with the two sensors of its fix and the delay a drive takes; and the drives under
        #  way, each the instant it shows and the cell it shows.
        self.vans = {r["van"]: (r["column"], r["row"], float(r["delay"]) if r.get("delay") is not None else 0.0)
                     for r in self._rows(_VANS_Q) if r["column"] in self.sensors and r["row"] in self.sensors}
        self.cells = {(int(r["x"]), int(r["y"])) for r in self._rows(_CELLS_Q)}
        self.moving: dict[str, tuple[datetime, tuple[int, int]]] = {}
        #  THE CONTACTS each van carries, in the world's order, and where the things with no fix stand.
        self.contacts = {r["contact"]: (r["van"], r.get("peer"), r["column"], r["row"],
                                        int(r["radius"]) if r.get("radius") is not None else None)
                         for r in self._rows(_CONTACTS_Q) if r["column"] in self.sensors and r["row"] in self.sensors}
        self.posed = {r["thing"]: (int(r["x"]), int(r["y"])) for r in self._rows(_POSED_Q)}

    def _rows(self, text: str, **values) -> list[dict]:
        return rows(self.store, text, graphs_of(self.store, BELIEF, common=True), **values)

    def open(self) -> list[str]:
        """Listen for the commands every simulated actuator takes; the topics."""
        for topic in sorted(self.listening):
            self.client.subscribe(topic)
        return sorted(self.listening)

    def _of(self, subject: str, observed: str):
        return [s for s in self.sensors.values() if s["subject"] == subject and s["property"] == observed]

    def _move(self, sensor: dict, by: float) -> None:
        v = sensor["value"] + by
        if sensor["lo"] is not None:
            v = max(sensor["lo"], v)
        if sensor["hi"] is not None:
            v = min(sensor["hi"], v)
        sensor["value"] = v

    def _read(self, sensor: dict) -> float:
        """The number `sensor` publishes now: the model's reading with the instrument's noise — a draw
        within its jitter either way, rounded to `PLACES` — and never the number it published last,
        redrawn where the draw repeats it. A jitter of nought is the exception that proves the rule:
        nothing to redraw with, so the model's reading goes out exactly, and sensing says what it says
        of a number that never moves."""
        value = sensor["value"]
        for _ in range(16):
            value = round(sensor["value"] + self.rng.uniform(-sensor["jitter"], sensor["jitter"]), PLACES) + 0.0
            if value != sensor["last"]:
                break
        sensor["last"] = value
        return value

    def command(self, topic: str, payload: bytes) -> None:
        """A command on an actuator's topic: a dose pours at once, a heating runs for its seconds, a van
        is at the cell it is told after its delay."""
        actuator = self.listening.get(topic)
        if actuator is None:
            return
        said = json.loads(payload)
        if "dose_ml" in said:
            for r in self._rows(_DOSES_Q, actuator=actuator):
                for sensor in self._of(r["subject"], r["property"]):
                    self._move(sensor, (float(said["dose_ml"]) / 1000.0) / float(r["litres"]))
            log.info("%s poured %s ml", actuator.rsplit("#", 1)[-1], said["dose_ml"])
        if "heat_s" in said:
            self.heating[actuator] = self.at + timedelta(seconds=float(said["heat_s"]))
            log.info("%s heats for %s s", actuator.rsplit("#", 1)[-1], said["heat_s"])
        if "to" in said and actuator in self.vans:
            self._drive(actuator, (int(said["to"]["x"]), int(said["to"]["y"])))

    def _drive(self, van: str, to: tuple[int, int]) -> None:
        """A van told a cell's coordinates: it is there `sim:delayS` later, where the cell is a neighbour of
        the one it stands on — |dx| + |dy| = 1, the drive's own rule — and it refuses anything else in the
        log, as a van cannot reach a cell two away in one drive. The grid is infinite, so a neighbour off the
        road is driven to like any other: the agent, knowing only the road, never asks for one. A van already
        under way is told again."""
        column, row, delay = self.vans[van]
        here = (int(round(self.sensors[column]["value"])), int(round(self.sensors[row]["value"])))
        if abs(to[0] - here[0]) + abs(to[1] - here[1]) != 1:
            log.error("%s: told %s from %s, which is no neighbour", van.rsplit("#", 1)[-1], to, here)
            return
        self.moving[van] = (self.at + timedelta(seconds=delay), to)
        log.info("%s drives to %s, there in %s s", van.rsplit("#", 1)[-1], to, delay)

    def position(self, thing: str) -> tuple[int, int] | None:
        """Where `thing` truly stands: its fix's coordinates if it has one, else its model's, else nowhere."""
        if thing in self.vans:
            column, row, _ = self.vans[thing]
            return (int(round(self.sensors[column]["value"])), int(round(self.sensors[row]["value"])))
        return self.posed.get(thing)

    def _sight(self) -> None:
        """Every contact's sensors set to the vector from the carrying van to what the contact stands for —
        its peer, or the nearest thing no receiver of that van identifies, slots taking the nearest first —
        where that is within the radius, and to a vector landing past the far corner of the cells the world's
        agents know where it is not, or where there is nothing to stand for."""
        beyond = (max(x for x, _ in self.cells) + 1, max(y for _, y in self.cells) + 1) if self.cells else (1, 1)
        identified = {(van, peer) for van, peer, *_ in self.contacts.values() if peer}
        taken: dict[str, set[str]] = {}
        for contact, (van, peer, column, row, radius) in self.contacts.items():
            here = self.position(van)
            if here is None:
                continue
            target = None
            if peer:
                target = self.position(peer)
            else:
                things = [(abs(p[0] - here[0]) + abs(p[1] - here[1]), name, p)
                          for name in [*self.vans, *self.posed]
                          if name != van and (van, name) not in identified and name not in taken.get(van, set())
                          and (p := self.position(name)) is not None]
                things.sort()
                if things:
                    _, name, target = things[0]
                    taken.setdefault(van, set()).add(name)
            if target is not None and (radius is None or abs(target[0] - here[0]) + abs(target[1] - here[1]) <= radius):
                vector = (target[0] - here[0], target[1] - here[1])
            else:
                vector = (beyond[0] - here[0], beyond[1] - here[1])
            self.sensors[column]["value"], self.sensors[row]["value"] = float(vector[0]), float(vector[1])

    def due_in(self, now: datetime) -> float:
        """World seconds until the earliest reading falls due — nought where one is due already, a day
        where nothing here reads — so the process sleeps until then and not for a real second."""
        if not self.sensors:
            return 86400.0
        return max(0.0, (min(s["due"] for s in self.sensors.values()) - now).total_seconds())

    def step(self, now: datetime) -> list[tuple[str, dict]]:
        """Advance the physics to `now` and publish every topic a reading has fallen due on; what was
        published, as (topic, document).

        ONE DOCUMENT PER TOPIC, AS A BOARD PUBLISHES: a topic is a client's, named for it, and the client
        publishes every sensor it hosts in one message at its heartbeat, each sensor's number at the
        pointer the world binds it to (`sensing:readingPointer`) — the terrace board's five values are
        one message, and the agent's sensors each read their own. So every sensor of a topic is read
        when any of them is due, and sensors of one board report at the cadence of its fastest."""
        seconds = max(0.0, (now - self.at).total_seconds())
        for sensor in self.sensors.values():
            rate = self.dries.get(sensor["subject"])
            if rate and sensor["property"] == CLIMATE + "SoilMoisture":
                self._move(sensor, -rate * seconds / 86400.0)
        for heater, until in list(self.heating.items()):
            running = max(0.0, (min(now, until) - self.at).total_seconds())
            for r in self._rows(_HEATS_Q, actuator=heater):
                for sensor in self._of(r["subject"], r["property"]):
                    self._move(sensor, float(r["rate"]) * running / 3600.0)
            if until <= now:
                del self.heating[heater]
        for van, (shows, to) in list(self.moving.items()):
            if shows <= now:
                self.sensors[self.vans[van][0]]["value"] = float(to[0])
                self.sensors[self.vans[van][1]]["value"] = float(to[1])
                del self.moving[van]
        self.at = now
        self._sight()
        published = []
        for topic in sorted({s["topic"] for s in self.sensors.values() if s["due"] <= now}):
            document: dict = {}
            for sensor in self.sensors.values():
                if sensor["topic"] == topic:
                    _put(document, sensor["pointer"], self._read(sensor))
                    sensor["due"] = now + timedelta(seconds=sensor["every"])
            self.client.publish(topic, json.dumps(document).encode())
            published.append((topic, document))
        return published


def _put(document: dict, pointer: str, value: float) -> None:
    """`value` at `pointer` in `document` — a JSON pointer of object members, `/a/b`, which is what a
    board writes and the reverse of the one walk sensing reads by."""
    keys = pointer.lstrip("/").split("/")
    for key in keys[:-1]:
        document = document.setdefault(key, {})
    document[keys[-1]] = value
