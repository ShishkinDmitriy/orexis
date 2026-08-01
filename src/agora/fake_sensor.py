"""A stand-in for the ESP32 sensor edge: publishes simulated moisture to MQTT.

Lets the whole gateway slice run on a laptop with no hardware. Each plant dries out
gradually, with occasional "watering/rain" bumps, so you see bands cross LOW/OK/HIGH
and situation events fire. Replace with a real ESP32 publishing the same topic/shape.
"""

from __future__ import annotations

import json
import logging
import random
import time

import paho.mqtt.client as mqtt

from . import config

log = logging.getLogger("fake-sensor")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    cfg = config.load_plants()
    plants = cfg["plants"]

    host = config.env("MQTT_HOST", "localhost")
    port = int(config.env("MQTT_PORT", "1883"))
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host, port)
    client.loop_start()

    # Each plant starts comfortably moist and dries out.
    moisture = {p["id"]: random.uniform(0.45, 0.6) for p in plants}
    log.info("publishing simulated readings to %s:%s (Ctrl-C to stop)", host, port)

    try:
        while True:
            for p in plants:
                pid = p["id"]
                moisture[pid] -= random.uniform(0.005, 0.02)          # evaporation
                if random.random() < 0.05:                            # occasional watering/rain
                    moisture[pid] += random.uniform(0.10, 0.30)
                moisture[pid] = max(0.0, min(1.0, moisture[pid]))

                payload = {"value": round(moisture[pid], 3), "sensor": p.get("sensor", "sensor")}
                client.publish(f"sensors/{pid}/moisture", json.dumps(payload))
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
