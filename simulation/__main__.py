"""`python -m simulation <world>`: play a world's simulated systems on its broker until stopped.

The broker's address and this client's credential arrive as environment, as an agent's do —
`MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD` — and paho is imported here and
nowhere else in the simulator."""

from __future__ import annotations

import argparse
import logging
import os
import queue
import time
from pathlib import Path

from agent import clock

from .simulator import Simulator


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Play a world's simulated systems on its broker.")
    parser.add_argument("world", type=Path, help="the world's directory")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    import paho.mqtt.client as paho

    client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=os.environ["MQTT_USERNAME"])
    client.username_pw_set(os.environ["MQTT_USERNAME"], os.environ.get("MQTT_PASSWORD"))
    inbox: queue.SimpleQueue = queue.SimpleQueue()
    client.on_message = lambda c, u, m: inbox.put((m.topic, m.payload))
    client.connect(os.environ["MQTT_HOST"], int(os.environ.get("MQTT_PORT", "1883")))
    client.loop_start()
    simulator = Simulator(args.world, client)
    simulator.open()
    while True:
        while not inbox.empty():
            simulator.command(*inbox.get_nowait())
        simulator.step(clock.now())
        time.sleep(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
