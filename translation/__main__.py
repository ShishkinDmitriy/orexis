"""`python -m translation <world>`: stand between a world's people and its agents until stopped.

The broker's address and this client's credential arrive as environment, as the simulator's do —
`MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD` — and paho is imported here and nowhere
else in the translator. The model is `MODEL_API_KEY`, `MODEL_NAME` and `MODEL_URL` (`model.py`), the
mailbox `MAIL_*` (`carrier.py`) asked every `MAIL_POLL_S` real seconds, the Telegram bot `TELEGRAM_BOT_TOKEN`
asked every `TELEGRAM_POLL_S`, at `TELEGRAM_URL`. The
bus is the other carrier and needs nothing of its own: every message the translator is subscribed to
goes through `Translator.receive`, prose on a chat's topic and statements on a person's inbox alike."""

from __future__ import annotations

import argparse
import logging
import os
import queue
import time
from pathlib import Path

from .carrier import Email, Telegram
from .model import Model
from .translator import Translator


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Translate between a world's people and its agents.")
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
    mail = Email.from_environ()
    translator = Translator(args.world, client, Model.from_environ(), mail, Telegram.from_environ())
    translator.open()
    carriers = [(mail, float(os.environ.get("MAIL_POLL_S", "30")), [0.0], "the mailbox"),
                (translator.telegram, float(os.environ.get("TELEGRAM_POLL_S", "3")), [0.0], "the bot")]
    while True:
        while not inbox.empty():
            translator.receive(*inbox.get_nowait())
        for carrier, every, polled, name in carriers:
            if carrier is not None and time.monotonic() - polled[0] >= every:
                polled[0] = time.monotonic()
                try:
                    for address, prose in carrier.poll():
                        translator.hear(address, prose)
                except Exception as exc:                                # noqa: BLE001 — a carrier fails
                    logging.getLogger("carrier").warning("%s would not answer: %s", name, exc)
        time.sleep(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
