"""The gateway: a thin, stake-free RPi process — the measurement witness.

ESP32 --raw reading--> MQTT --> gateway
   -> InfluxDB   (the series / record: every reading)
   -> Fuseki     (:attested current MEASUREMENT: the signed number agents cite)
   -> readings/<plant>  (a neutral "new reading" event; the agent decides if it's LOW)

It attests the *measurement*, not a judgment — "is 0.18 LOW?" is the agent's call
(desire-relative). Agents never write either store. See knowledge/domain/gateway.md and
knowledge/decisions/agent-centric-epistemics.md.
"""

from __future__ import annotations

import json
import logging

import paho.mqtt.client as mqtt

from . import config
from .attestor import Attestor
from .influx_writer import InfluxWriter

log = logging.getLogger("gateway")

SENSOR_TOPIC = "sensors/+/moisture"  # sensors/<plant_id>/moisture


class Gateway:
    def __init__(self) -> None:
        cfg = config.load_plants()
        self.plants = {p["id"]: p for p in cfg["plants"]}
        self.world_version = int(cfg.get("world_version", 1))

        self.influx = InfluxWriter(
            config.env("INFLUX_URL", "http://localhost:8086"),
            config.env("INFLUX_TOKEN", "dev-token-change-me"),
            config.env("INFLUX_ORG", "agora"),
            config.env("INFLUX_BUCKET", "sensors"),
        )
        self.attestor = Attestor(
            config.env("FUSEKI_URL", "http://localhost:3030/ds"),
            "admin",
            config.env("FUSEKI_PASSWORD", "admin"),
        )

        self.mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_message = self._on_message

    # --- MQTT callbacks ---------------------------------------------------

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        log.info("connected to MQTT (%s); subscribing %s", reason_code, SENSOR_TOPIC)
        client.subscribe(SENSOR_TOPIC)

    def _on_message(self, client, userdata, msg) -> None:
        parts = msg.topic.split("/")
        if len(parts) != 3:
            return
        plant_id = parts[1]
        plant = self.plants.get(plant_id)
        if plant is None:
            log.warning("reading for unknown plant %r; ignoring", plant_id)
            return

        try:
            payload = json.loads(msg.payload)
            value = float(payload["value"])
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("bad payload on %s: %s", msg.topic, exc)
            return

        sensor = payload.get("sensor", plant.get("sensor", "sensor"))

        # 1. series (the record) — every reading.
        self.influx.write_reading(plant_id, sensor, value)

        # 2. attest the MEASUREMENT (not a judgment) — overwrite current-state in :attested.
        try:
            self.attestor.attest(plant["uri"], plant_id, value, sensor, self.world_version)
        except Exception as exc:  # keep the loop alive even if Fuseki hiccups
            log.error("attest failed for %s: %s", plant_id, exc)

        # 3. announce the new reading (a neutral fact, no band). The agent decides LOW.
        client.publish(
            f"readings/{plant_id}",
            json.dumps({"plant": plant_id, "uri": plant["uri"], "value": value,
                        "world_version": self.world_version}),
        )
        log.debug("%-9s attested %.3f", plant_id, value)

    # --- lifecycle --------------------------------------------------------

    def run(self) -> None:
        host = config.env("MQTT_HOST", "localhost")
        port = int(config.env("MQTT_PORT", "1883"))
        log.info("gateway starting; MQTT %s:%s", host, port)
        self.mqtt.connect(host, port)
        try:
            self.mqtt.loop_forever()
        except KeyboardInterrupt:
            log.info("shutting down")
        finally:
            self.influx.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    Gateway().run()


if __name__ == "__main__":
    main()
