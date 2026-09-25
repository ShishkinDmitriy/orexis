"""The simulator plays a world's simulated systems from the world's own words.

It is NOT a pretend board. A board is told its topics and knows nothing else; the simulator is the
environment the agents act in — the bed drying, the pump pouring, the heater warming — so it reads
the world as an agent boots it (`agent.runtime.world_of`) and takes every fact from there:

- which systems to play: every one marked `sim:simulatedBy`, and a sensor's starting reading and
  bounds from its `sim:Model`;
- where each speaks: the topic a sensor publishes on and the topic an actuator listens to, by the
  patterns of the MQTT4SSN filters that match them; how often a sensor reports, from its
  `ssn-system:Frequency`;
- the physics: a subject's soil dries `climate:driesPerDay`; a dose of `dose_ml` on a valve that
  `actuation:actuates` a subject raises the property it `actuation:actuatesProperty` by the litres
  over the subject's `climate:litresPerFraction`; a heating of `heat_s` on a heater that
  `climate:warms` a subject raises the property it `climate:warmsProperty` at `climate:degreesPerHour`
  for as long as it runs.

A reading is published as `{"value": n}` on the sensor's topic, the document sensing's default
pointer reads. Time is the one timeline, `clock.now()`; `step` is called with the present and
advances everything from the last step.
"""

from __future__ import annotations

import json
import logging
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

_SENSORS_Q = f"""
SELECT ?sensor ?subject ?property ?start ?lo ?hi ?pattern ?every ?unit WHERE {{
  ?sensor a sosa:Sensor ; <{SIM}simulatedBy> ?model ; sosa:isHostedBy ?subject ; sosa:observes ?property ;
          <{MQTT4SSN}observesTopic> ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern .
  FILTER(!CONTAINS(?pattern, "+") && !CONTAINS(?pattern, "#"))
  OPTIONAL {{ ?model <{SIM}initialValue> ?start }}
  OPTIONAL {{ ?model <{SIM}minValue> ?lo }} OPTIONAL {{ ?model <{SIM}maxValue> ?hi }}
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

    def __init__(self, world, client, now: datetime | None = None):
        self.store = world_of(world)
        self.client = client
        self.at = now or clock.now()
        self.sensors: dict[str, dict] = {}
        for r in self._rows(_SENSORS_Q):
            every = float(r["every"]) * _SECONDS.get((r.get("unit") or "").rsplit("/", 1)[-1], 1) if r.get("every") else 60.0
            self.sensors[r["sensor"]] = {
                "subject": r["subject"], "property": r["property"], "topic": r["pattern"],
                "value": float(r.get("start") or 0.0), "every": every, "due": self.at,
                "lo": float(r["lo"]) if r.get("lo") is not None else None,
                "hi": float(r["hi"]) if r.get("hi") is not None else None}
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
                value = round(sensor["value"], 4)
                self.client.publish(sensor["topic"], json.dumps({"value": value}).encode())
                sensor["due"] = now + timedelta(seconds=sensor["every"])
                published.append((sensor["topic"], value))
        return published
