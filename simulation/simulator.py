"""The simulator plays a world's simulated systems from the world's own words.

It is NOT a pretend board. A board is told its topics and knows nothing else; the simulator is the
environment the agents act in — the bed drying, the pump pouring, the heater warming — so it reads
the world as an agent boots it (`agent.runtime.world_of`) and takes every fact from there — the
world graph and the society graph, both public, and never the deployment graph, since the broker's
address reaches it as environment, as an agent's does:

- which systems to play: every one marked `sim:simulatedBy`, and a sensor's starting reading and
  bounds from its `sim:Model` (the world graph);
- where each speaks: the topic a sensor publishes on and the topic an actuator listens to, by the
  patterns of the MQTT4SSN filters that match them (the society graph); how often a sensor
  reports, from its `ssn-system:Frequency`;
- the physics: a subject's soil dries `climate:driesPerDay`; a dose of `dose_ml` on a valve that
  `actuation:actuates` a subject raises the property it `actuation:actuatesProperty` by the litres
  over the subject's `climate:litresPerFraction`; a heating of `heat_s` on a heater that
  `climate:warms` a subject raises the property it `climate:warmsProperty` at `climate:degreesPerHour`
  for as long as it runs.

A reading is published as `{"value": n}` on the sensor's topic, the document sensing's default
pointer reads. Time is the one timeline, `clock.now()`; `step` is called with the present and
advances everything from the last step.

THE NUMBER PUBLISHED IS THE INSTRUMENT'S, NOT THE MODEL'S (#879). The physics moves only what a
drift or a running heater moves, so a model nothing touches — the air of a greenhouse nobody heats,
a probe clamped at its bound — reads the same to the fourth place at every cadence, and sensing,
whose stuck detector is premised on a live instrument's count moving by at least one within a few
readings, said such a sensor stuck an hour into its world. So each published number is the model's
reading with the instrument's noise: a draw within the model's `sim:jitter` either way (`JITTER`
where it states none, one count of the `PLACES` the simulator publishes to), rounded as a board
would round, and never the number this sensor published last — the premise the detector states,
held to rather than left to a draw that could repeat. The draw is seeded, so a test and a run are
reproducible, and the noise is the instrument's alone: the model's reading is untouched by it, and
the model's bounds bound the reading, not the number.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta

from agent import clock
from agent.runtime import world_of
from agent.store import graphs_of, rows

log = logging.getLogger("simulation")

PUBLIC = "http://example.org/orexis#PublicGraph"
SIM = "http://example.org/orexis/sim#"
CLIMATE = "http://example.org/orexis/climate#"
ACTUATION = "http://example.org/orexis/actuation#"
MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"
_SECONDS = {"SEC": 1, "MIN": 60, "HR": 3600, "HUR": 3600, "DAY": 86400}

#  WHAT A BOARD WOULD PUBLISH: the decimal places a number is rounded to, and how far the published
#  number strays from the model's reading either way where the model states no `sim:jitter` — one
#  count of those places, the least a live instrument moves by.
PLACES = 4
JITTER = 10.0 ** -PLACES

_SENSORS_Q = f"""
SELECT ?sensor ?subject ?property ?start ?lo ?hi ?jitter ?pattern ?every ?unit WHERE {{
  ?sensor a sosa:Sensor ; <{SIM}simulatedBy> ?model ; sosa:isHostedBy ?subject ; sosa:observes ?property ;
          <{MQTT4SSN}observesTopic> ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern .
  FILTER(!CONTAINS(?pattern, "+") && !CONTAINS(?pattern, "#"))
  OPTIONAL {{ ?model <{SIM}initialValue> ?start }}
  OPTIONAL {{ ?model <{SIM}minValue> ?lo }} OPTIONAL {{ ?model <{SIM}maxValue> ?hi }}
  OPTIONAL {{ ?model <{SIM}jitter> ?jitter }}
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
                "jitter": float(r["jitter"]) if r.get("jitter") is not None else JITTER, "last": None}
        self.listening = {r["pattern"]: r["actuator"] for r in self._rows(_ACTUATORS_Q)
                          if "+" not in r["pattern"] and "#" not in r["pattern"]}
        self.dries = {r["subject"]: float(r["rate"]) for r in self._rows(_DRIES_Q)}
        self.heating: dict[str, datetime] = {}

    def _rows(self, text: str, **values) -> list[dict]:
        return rows(self.store, text, graphs_of(self.store, PUBLIC), **values)

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
        """A command on an actuator's topic: a dose pours at once, a heating runs for its seconds."""
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

    def due_in(self, now: datetime) -> float:
        """World seconds until the earliest reading falls due — nought where one is due already, a day
        where nothing here reads — so the process sleeps until then and not for a real second."""
        if not self.sensors:
            return 86400.0
        return max(0.0, (min(s["due"] for s in self.sensors.values()) - now).total_seconds())

    def step(self, now: datetime) -> list[tuple[str, float]]:
        """Advance the physics to `now` and publish every reading fallen due; what was published."""
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
        self.at = now
        published = []
        for sensor in self.sensors.values():
            if sensor["due"] <= now:
                value = self._read(sensor)
                self.client.publish(sensor["topic"], json.dumps({"value": value}).encode())
                sensor["due"] = now + timedelta(seconds=sensor["every"])
                published.append((sensor["topic"], value))
        return published
