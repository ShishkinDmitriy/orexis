"""A sensor that does not exist, speaking exactly what one would.

This is FIRMWARE, in every sense that matters. It runs on the far side of the wire, it is told
its identity and its topics the way a board is told them in `config.h`, and it knows nothing
about agents, worlds or belief bases. It is in Python and beside two PlatformIO projects because
what a directory under `firmware/` answers is *what runs on the device*, and the language a
device happens to run is not the interesting part.

**The whole claim is that nothing downstream can tell.** So this publishes what the real board
publishes, byte for byte — `{"value": 0.183, "sensor": "..."}` — obeys the same retained
`{"sleep_s": N}`, answers the same `{"sense": true}`, and holds the same constitutional floor and
ceiling on its cadence. An agent wired to one of these derives `ag:Subscribing` and runs the
ordinary perception module, because from where it stands there is nothing else it could be.

That is the point of the exercise. The simulation world used to exercise a parallel
implementation, which meant it could pass while the real path was broken — the weakest possible
form of simulation.

**Sense mode is honoured rather than assumed.** `scheduled` obeys the cadence command like a
sleeping board; `push` publishes on its own clock and ignores commands, so its agent derives
`ag:Listening` and never tries to instruct it. Same code, same wire, different device character.

**Why it watches a valve.** A real plant gets wet because water physically arrives. Nothing
physical happens here, so the model has to learn about the dose somehow — and it does it by
reading the same public command the valve reads. No private channel between simulators: the
water is observed on the wire, which is as close to "the water arrived" as a message can be.

Configured entirely by environment, because that is what a board gets. It does not read the
world graph — it could not, if it were an ESP32, and letting it would quietly make this a
different kind of thing.
"""

from __future__ import annotations

import json
import logging
import os
import random
import signal
import threading
import time

import paho.mqtt.client as mqtt

log = logging.getLogger("simulator")


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise SystemExit(f"{name} is required — a simulated device is configured exactly as a "
                         f"board is, and this is part of its config.h")
    return value


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else default


class SimulatedSensor:
    """One device: a value that drifts, a clock, and a connection."""

    def __init__(self) -> None:
        self.sensor_id = _env("SIM_SENSOR_ID")
        self.reading_topic = _env("SIM_READING_TOPIC")
        self.command_topic = os.environ.get("SIM_COMMAND_TOPIC") or ""
        self.dose_topic = os.environ.get("SIM_DOSE_TOPIC") or ""
        # `scheduled` keeps the interval it is given; `push` keeps its own. The agent's
        # capability follows from this, and neither branch knows that.
        self.mode = _env("SIM_SENSE_MODE", "scheduled").lower()

        # The range this device can report. A moisture fraction happens to be 0..1, but nothing
        # about a simulated sensor is: a thermometer reports neither. Stated rather than assumed,
        # so the same simulator stands in for the temperature sensor when it arrives.
        self.min_value = _float("SIM_MIN_VALUE", 0.0)
        self.max_value = _float("SIM_MAX_VALUE", 1.0)
        self.initial = _float("SIM_INITIAL_VALUE", 0.45)
        self.value = self.initial
        self.dry_rate = _float("SIM_DRY_RATE", 0.02)
        self.tick_s = _float("SIM_TICK_SECONDS", 3)
        # How much of the observed property a litre moves. The world states this about the
        # subject; the simulator is told it, exactly as calibration is flashed into a board.
        self.litres_per_fraction = _float("SIM_LITRES_PER_FRACTION", 0.0)

        self.min_sleep_s = _float("SIM_MIN_SLEEP_S", 10)
        self.max_sleep_s = _float("SIM_MAX_SLEEP_S", 900)
        # Until an agent says otherwise — the same fallback a board carries.
        self.sleep_s = _float("SIM_DEFAULT_SLEEP_S", 60)

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"agora-sim-{self.sensor_id}-{random.randint(0, 1 << 24):06x}")
        self.client.username_pw_set(_env("MQTT_USERNAME"), _env("MQTT_PASSWORD"))
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._stop = threading.Event()

    # --- the wire ---

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code != 0:
            log.error("%s: refused by the broker (%s) — wrong credential, or the ACL does not "
                      "grant this principal", self.sensor_id, reason_code)
            return
        # A retained cadence is delivered on subscribe, which is the whole mechanism that lets a
        # sleeping board be instructed by an agent it is never awake at the same time as.
        # Subscribed in BOTH modes. A real push board would not listen at all, and the honest
        # part of that — refusing orders about its own clock — is kept below. What it cannot
        # refuse is being repositioned by whoever is running the simulation.
        if self.command_topic:
            client.subscribe(self.command_topic)
        if self.dose_topic:
            client.subscribe(self.dose_topic)
        log.info("%s up — publishing %s every %ss (%s)", self.sensor_id, self.reading_topic,
                 self.sleep_s, self.mode)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            doc = json.loads(msg.payload)
        except (ValueError, TypeError):
            log.warning("%s: unreadable payload on %s", self.sensor_id, msg.topic)
            return

        if msg.topic == self.dose_topic:
            self._receive(float(doc.get("ml") or 0.0))
            return

        # The command topic IS the device's control surface — a real board reads named keys off
        # it and ignores the rest, so the operator's verbs ride the same channel and no second
        # topic, term, shape or grant has to exist. A board handed {"set": 0.9} discards it.
        self._control(doc)

        # push devices take no orders ABOUT THEIR CLOCK, and saying so is the difference between
        # the two modes. They still answer the puppet strings above: a stand-in that could not be
        # steered would be untestable, and steering is not something the device does.
        if self.mode == "push":
            return
        if isinstance(doc.get("sleep_s"), (int, float)):
            asked = float(doc["sleep_s"])
            self.sleep_s = max(self.min_sleep_s, min(self.max_sleep_s, asked))
            log.info("%s: cadence now %ss", self.sensor_id, self.sleep_s)
        if doc.get("sense"):
            self._publish()

    def _publish(self) -> None:
        payload = json.dumps({"value": round(self.value, 3), "sensor": self.sensor_id})
        self.client.publish(self.reading_topic, payload, qos=1)

    def _control(self, doc: dict) -> None:
        """Steer the simulation. NOT physics — this is a hand reaching into the model.

        Watering is deliberately not here: water arriving at soil is something the world does, so
        it comes over the dose topic and exercises the real actuation path. Routing it through
        here would mean the simulation quietly stopped testing whether watering works.

        What belongs here is what has no physical counterpart: putting the value somewhere to see
        what an agent does about it, and putting it back.
        """
        if isinstance(doc.get("set"), (int, float)):
            self.value = self._clamp(float(doc["set"]))
            log.info("%s: set to %.3f", self.sensor_id, self.value)
        if isinstance(doc.get("trend"), (int, float)):
            # Signed, and it REPLACES the dry rate rather than adding to it: a positive trend is
            # a pot being rained on, which is a different world, not a wetter one.
            self.dry_rate = -float(doc["trend"])
            log.info("%s: trend now %+.4f per tick", self.sensor_id, -self.dry_rate)
        if doc.get("reset"):
            self.value, self.dry_rate = self.initial, _float("SIM_DRY_RATE", 0.02)
            log.info("%s: reset to %.3f", self.sensor_id, self.value)
        if doc.get("publish"):
            self._publish()

    # --- the physics ---

    def _clamp(self, v: float) -> float:
        return max(self.min_value, min(self.max_value, v))

    def _receive(self, ml: float) -> None:
        """Water arrived at the subject. How far it moves the reading is a fact about the pot."""
        if ml > 0 and self.litres_per_fraction > 0:
            self.value = self._clamp(self.value + (ml / 1000.0) / self.litres_per_fraction)
            log.info("%s: received %.0f ml -> %.3f", self.sensor_id, ml, self.value)

    def _dry(self) -> None:
        self.value = self._clamp(self.value - self.dry_rate)

    # --- the loop ---

    def run(self) -> None:
        # Blocked before any thread starts, so this thread is the one that wakes and the paho
        # loop inherits the mask. An unhandled signal is DISCARDED for a container's PID 1 —
        # the same rule that once made agents take ten seconds and a SIGKILL to stop.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        self.client.connect(_env("MQTT_HOST"), int(_env("MQTT_PORT")))
        self.client.loop_start()

        waiter = threading.Thread(target=self._loop, daemon=True)
        waiter.start()
        signal.sigwait({signal.SIGINT, signal.SIGTERM})

        log.info("%s shutting down", self.sensor_id)
        self._stop.set()
        self.client.loop_stop()
        self.client.disconnect()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._dry()
            self._publish()
            # A scheduled device sleeps for what it was told; a push one keeps its own tick.
            # Neither can be instructed to breach the constitutional bounds.
            self._stop.wait(self.sleep_s if self.mode != "push" else self.tick_s)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    SimulatedSensor().run()


if __name__ == "__main__":
    main()
