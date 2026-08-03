"""Virtual plants — a software stand-in for {sensor + valve + soil}.

Not an agent: it has no beliefs, no stake and no capabilities. It is the *physical world*,
and it reads only physical facts from the world graph — which subjects exist, how fast each
dries, how much water moves it — plus the topics its devices are reachable on. It never sees
an agent's beliefs, because soil does not care what anyone wants.

At the wire it is indistinguishable from an ESP32: it publishes on the sensor's
`ag:readingTopic` **only when the agent's cadence says to** (or on a `sense` request), takes
cadence from the sensor's `ag:commandTopic`, and waters when a co-signed command arrives on
the valve's `ag:commandTopic`. Ingest is the polling agent's job, not its own.

Note the split: drying is physics and never stops; *sensing* is the agent's initiative. A
plant nobody is watching still dries — which is exactly the risk of sleeping through a
drought, kept real in simulation.

  agora-sim
"""

from __future__ import annotations

import json
import logging
import random
import time

import paho.mqtt.client as mqtt

from . import config, signing, store
from .modules.actuation import verify_command
from .ontology import WORLD_GRAPH
from .store import bindings
from .world import load_bus, load_world

log = logging.getLogger("sim")

DEFAULT_SLEEP_S = 60  # cadence before any agent has commanded one (mirrors the firmware)

# Devices and their subjects — physical wiring, public. Nothing here reads a belief.
_DEVICES_Q = f"""
SELECT ?subjectId ?sensor ?sensorId ?readingTopic ?sensorCmd ?valveCmd ?dryRate ?litresPerFraction
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?subject ag:localId ?subjectId .
  OPTIONAL {{ ?subject ag:dryRatePerTick ?dryRate }}
  OPTIONAL {{ ?subject ag:litresPerFraction ?litresPerFraction }}
  ?sensor a ag:Sensor ; ag:monitors ?subject ; ag:localId ?sensorId ;
          ag:readingTopic ?readingTopic .
  OPTIONAL {{ ?sensor ag:commandTopic ?sensorCmd }}
  OPTIONAL {{ ?valve a ag:Valve ; ag:actuates ?subject ; ag:commandTopic ?valveCmd }}
}} }}"""


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


class SimPlant:
    """A soil model with a sensor board bolted on: it senses only when asked."""

    def __init__(self, subject_id, moisture, dry_rate, ml_to_fraction, min_sleep_s, max_sleep_s):
        self.subject_id = subject_id
        self.moisture = moisture
        self.dry_rate = dry_rate
        self.ml_to_fraction = ml_to_fraction
        self.min_sleep_s, self.max_sleep_s = min_sleep_s, max_sleep_s
        self.sleep_s = float(DEFAULT_SLEEP_S)
        self.next_sense_at = 0.0  # sense once at startup, then on cadence

    def dry(self) -> None:
        self.moisture = _clamp(self.moisture - self.dry_rate)

    def water(self, ml: float) -> None:
        self.moisture = _clamp(self.moisture + ml * self.ml_to_fraction)

    def set_cadence(self, sleep_s: float, now: float) -> None:
        """Accept the agent's cadence, clamped to the constitutional bounds, as a board does."""
        self.sleep_s = min(self.max_sleep_s, max(self.min_sleep_s, float(sleep_s)))
        self.next_sense_at = min(self.next_sense_at, now + self.sleep_s)

    def due_to_sense(self, now: float) -> bool:
        return now >= self.next_sense_at


class Simulator:
    def __init__(self):
        st = store.from_env(config.env)
        world = load_world(st.query)
        self.bus = load_bus(st.query)  # the same bus the agents meet on, from the same world
        self.tick_s = float(config.env("AGORA_SIM_TICK_S", "2"))
        bounds = bindings(st.query("""
SELECT ?min ?max WHERE { GRAPH ?g {
  ag:PerceptionCapability ag:minSleepS ?min ; ag:maxSleepS ?max } } LIMIT 1"""))
        min_sleep = int(bounds[0]["min"]) if bounds else 10
        max_sleep = int(bounds[0]["max"]) if bounds else 900

        wanted = [p.strip() for p in (config.env("AGORA_SIM_PLANTS", "") or "").split(",") if p.strip()]
        self.plants, self.by_sensor_cmd, self.by_valve_cmd = {}, {}, {}
        self.reading_topic, self.sensor_id = {}, {}

        for row in bindings(st.query(_DEVICES_Q)):
            sid = row["subjectId"]
            if wanted and sid not in wanted:
                continue  # a real ESP32 is handling this one
            lpf = float(row["litresPerFraction"]) if row.get("litresPerFraction") else 2.0
            self.plants[sid] = SimPlant(
                sid, random.uniform(0.4, 0.6),
                float(row["dryRate"]) if row.get("dryRate") else 0.01,
                1.0 / (lpf * 1000.0), min_sleep, max_sleep,
            )
            self.reading_topic[sid] = row["readingTopic"]
            self.sensor_id[sid] = row["sensorId"]
            if row.get("sensorCmd"):
                self.by_sensor_cmd[row["sensorCmd"]] = sid
            if row.get("valveCmd"):
                self.by_valve_cmd[row["valveCmd"]] = sid

        self.world_version = world.version
        try:
            self.host_pub = signing.load_public("host")
            self.clearing_pub = signing.load_public("clearing")
        except Exception:
            self.host_pub = self.clearing_pub = None
            log.warning("no signing keys (run agora-keygen) — valve commands will be REJECTED")

        self.mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        for topic in (*self.by_sensor_cmd, *self.by_valve_cmd):
            client.subscribe(topic)  # retained cadence arrives here on subscribe
        log.info("world v%s — simulating %s", self.world_version, ", ".join(self.plants) or "nothing")

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload)
        except (ValueError, TypeError):
            return
        if msg.topic in self.by_sensor_cmd:
            self._on_cmd(self.by_sensor_cmd[msg.topic], payload)
        elif msg.topic in self.by_valve_cmd:
            self._on_valve(self.by_valve_cmd[msg.topic], payload)

    def _on_cmd(self, sid: str, payload: dict) -> None:
        """The agent owns the cadence and may ask for a reading now — the board's contract."""
        plant, now = self.plants[sid], time.monotonic()
        if "sleep_s" in payload:
            try:
                plant.set_cadence(float(payload["sleep_s"]), now)
            except (ValueError, TypeError):
                return
            log.info("%-9s cadence set: sense every %.0fs", sid, plant.sleep_s)
        if payload.get("sense"):
            self._sense(sid, now)

    def _on_valve(self, sid: str, payload: dict) -> None:
        try:
            ml = float(payload["ml"])
        except (ValueError, KeyError, TypeError):
            return
        if not verify_command(payload, self.host_pub, self.clearing_pub):
            log.warning("%-9s REJECTED valve command (bad/missing host+clearing signature)", sid)
            return
        self.plants[sid].water(ml)
        log.info("%-9s watered %.0f ml -> moisture %.3f", sid, ml, self.plants[sid].moisture)

    def _sense(self, sid: str, now: float) -> None:
        plant = self.plants[sid]
        plant.next_sense_at = now + plant.sleep_s
        self.mqtt.publish(self.reading_topic[sid], json.dumps(
            {"value": round(plant.moisture, 3), "sensor": self.sensor_id[sid]}))

    def run(self) -> None:
        self.mqtt.connect(self.bus.host, self.bus.port)
        self.mqtt.loop_start()
        log.info("tick=%ss (Ctrl-C to stop)", self.tick_s)
        try:
            while True:
                now = time.monotonic()
                for sid, plant in self.plants.items():
                    plant.dry()  # physics never sleeps, even when nobody is looking
                    if plant.due_to_sense(now):
                        self._sense(sid, now)
                time.sleep(self.tick_s)
        except KeyboardInterrupt:
            pass
        finally:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    Simulator().run()


if __name__ == "__main__":
    main()
