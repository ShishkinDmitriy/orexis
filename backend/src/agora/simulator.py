"""Virtual plants — a closed-loop software stand-in for {sensor + pump + soil}.

Lets the whole society run and be watched with no hardware, and mix with real plants. Each
virtual plant dries over time, publishes its moisture to the sensor topic (the gateway
attests it, exactly like an ESP32), and subscribes to its valve topic so that *winning water
actually raises its moisture*. The agents, gateway, auction, clearing, and executor are all
unchanged — they can't tell a virtual plant from a real one. That is the edge-independence
the architecture was built for.

Closes the loop: dry → the agent judges itself LOW → round → wins water → valve → wetter →
cedes → dries again. Watering is driven by the market, not by chance.

  agora-sim   (the plant edge — no gateway; needs executor.actuate: true for the closed loop)
"""

from __future__ import annotations

import json
import logging
import random
import time

import paho.mqtt.client as mqtt

from . import config, signing
from .executor import verify_command
from .influx_writer import InfluxWriter
from .sensed_writer import SensedWriter

log = logging.getLogger("sim")


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


class SimPlant:
    """A soil model: dries each tick, gains moisture when watered."""

    def __init__(self, plant_id: str, moisture: float, dry_rate: float, ml_to_fraction: float):
        self.plant_id = plant_id
        self.moisture = moisture
        self.dry_rate = dry_rate  # fraction lost per tick
        self.ml_to_fraction = ml_to_fraction  # moisture gained per ml watered

    def dry(self) -> None:
        self.moisture = _clamp(self.moisture - self.dry_rate)

    def water(self, ml: float) -> None:
        self.moisture = _clamp(self.moisture + ml * self.ml_to_fraction)


class Simulator:
    def __init__(self):
        cfg = config.load_plants()
        sim = cfg.get("simulator", {})
        self.tick_s = float(sim.get("tick_seconds", 2))
        dry_rate = float(sim.get("dry_rate", 0.01))
        # match the agents' demand model so the loop converges sensibly
        lpf = cfg["value_model"]["litres_per_fraction"]
        ml_to_fraction = 1.0 / (lpf * 1000.0)

        ids = sim.get("plants") or [p["id"] for p in cfg["plants"]]
        self.uris = {p["id"]: p["uri"] for p in cfg["plants"]}
        self.sensors = {p["id"]: p.get("sensor", p["id"]) for p in cfg["plants"]}
        self.plants = {
            pid: SimPlant(pid, random.uniform(0.4, 0.6), dry_rate, ml_to_fraction) for pid in ids
        }
        self.world_version = int(cfg.get("world_version", 1))

        # No gateway: each plant writes its OWN sensed data (self-asserted). See
        # knowledge/decisions/trusted-agent-mode.md.
        self.influx = InfluxWriter(
            config.env("INFLUX_URL", "http://localhost:8086"),
            config.env("INFLUX_TOKEN", "dev-token-change-me"),
            config.env("INFLUX_ORG", "agora"),
            config.env("INFLUX_BUCKET", "sensors"),
        )
        self.sensed = SensedWriter(
            config.env("FUSEKI_URL", "http://localhost:3030/ds"),
            "admin",
            config.env("FUSEKI_PASSWORD", "admin"),
        )

        # the pump verifies the co-signed token (host + clearing) before opening a valve
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
        client.subscribe("actuators/+/valve")  # receive water from the executor
        log.info("simulating virtual plants: %s", ", ".join(self.plants))

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload)
            plant = payload["plant"]
            ml = float(payload["ml"])
        except (ValueError, KeyError, TypeError):
            return
        p = self.plants.get(plant)
        if p is None:
            return
        if not verify_command(payload, self.host_pub, self.clearing_pub):
            log.warning("%-9s REJECTED valve command (bad/missing host+clearing signature)", plant)
            return
        p.water(ml)
        log.info("%-9s watered %.0f ml -> moisture %.3f", plant, ml, p.moisture)

    def run(self) -> None:
        host = config.env("MQTT_HOST", "localhost")
        port = int(config.env("MQTT_PORT", "1883"))
        self.mqtt.connect(host, port)
        self.mqtt.loop_start()
        log.info("tick=%ss (Ctrl-C to stop)", self.tick_s)
        try:
            while True:
                for pid, p in self.plants.items():
                    p.dry()
                    sensor = self.sensors.get(pid, pid)
                    # the plant asserts its OWN reading: history (Influx) + current-state (:sensed)
                    self.influx.write_reading(pid, sensor, p.moisture)
                    try:
                        self.sensed.write(self.uris[pid], pid, round(p.moisture, 3), sensor, self.world_version)
                    except Exception as exc:
                        log.error("sensed write failed for %s: %s", pid, exc)
                    # announce a new reading so the round-runner can react
                    self.mqtt.publish(
                        f"readings/{pid}",
                        json.dumps({"plant": pid, "uri": self.uris[pid], "value": round(p.moisture, 3)}),
                    )
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
