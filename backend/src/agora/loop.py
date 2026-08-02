"""Event-driven round runner — the auction condenses out of scarcity.

Subscribes to the gateway's `situations/<plant>` events and runs a round when a plant
crosses `:LOW` (with a cooldown so a plant flapping around the threshold can't spam rounds).
The gateway only emits a situation on a *band change*, so this is already edge-triggered;
the cooldown is the second guard.

  agora-loop

See knowledge/domain/market.md (triggering), knowledge/domain/round.md.
"""

from __future__ import annotations

import json
import logging
import time

import paho.mqtt.client as mqtt

from . import config
from .live import run_live_round

log = logging.getLogger("loop")

SITUATIONS_TOPIC = "situations/+"


def due(last_run_ts: float, now: float, cooldown_s: float) -> bool:
    """Whether enough time has passed since the last round to run another."""
    return (now - last_run_ts) >= cooldown_s


class RoundRunner:
    def __init__(self, cooldown_s: float = 30.0):
        self.cooldown_s = cooldown_s
        self.last_run_ts = 0.0
        self.mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        log.info("connected (%s); subscribing %s", reason_code, SITUATIONS_TOPIC)
        client.subscribe(SITUATIONS_TOPIC)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            band = json.loads(msg.payload).get("band")
        except (ValueError, AttributeError):
            return
        if band != "LOW":
            return  # only scarcity opens a round
        now = time.monotonic()
        if not due(self.last_run_ts, now, self.cooldown_s):
            log.info("LOW on %s but within cooldown — skipping", msg.topic)
            return
        self.last_run_ts = now
        log.info("LOW on %s — running a round", msg.topic)
        try:
            run_live_round()
        except Exception as exc:  # never let one bad round kill the loop
            log.error("round failed: %s", exc)

    def run(self) -> None:
        host = config.env("MQTT_HOST", "localhost")
        port = int(config.env("MQTT_PORT", "1883"))
        log.info("round-runner starting; MQTT %s:%s cooldown=%ss", host, port, self.cooldown_s)
        self.mqtt.connect(host, port)
        try:
            self.mqtt.loop_forever()
        except KeyboardInterrupt:
            log.info("shutting down")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )
    cfg = config.load_plants()
    cooldown = float(cfg.get("round_loop", {}).get("cooldown_seconds", 30))
    RoundRunner(cooldown_s=cooldown).run()


if __name__ == "__main__":
    main()
