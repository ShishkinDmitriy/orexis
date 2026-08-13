"""A sensor that does not exist, speaking exactly what one would.

This is FIRMWARE, in every sense that matters. It runs on the far side of the wire, it is told
its identity and its topics the way a board is told them in `config.h`, and it knows nothing
about agents, worlds or belief bases. It is in Python and beside two PlatformIO projects because
what a directory under `firmware/` answers is *what runs on the device*, and the language a
device happens to run is not the interesting part.

**The whole claim is that nothing downstream can tell.** So this publishes what the real board
publishes, byte for byte — obeys the same retained `{"sleep_s": N}`, answers the same
`{"sense": true}`, and holds the same constitutional floor and ceiling on its cadence. An agent
wired to one of these derives `ag:Subscribing` and runs the ordinary perception module, because
from where it stands there is nothing else it could be.

That is the point of the exercise. The simulation world used to exercise a parallel
implementation, which meant it could pass while the real path was broken — the weakest possible
form of simulation.

**One board, several values.** A KY-015 reports temperature and humidity down one line, so a
board's message carries a value per property and each sensor takes its own out with a JSON
Pointer. This publishes the same shape: `SIM_VALUES` lists what this device reports and where in
its document each one goes, and a device that reports one thing is simply a list of one. The
claim above went quietly false when the real firmware learned to send three values and this still
sent one; nothing noticed, because no world had asked it for more.

**A temperature is not a fraction.** Each value drifts inside its own range, from its own start,
by its own step — because 0..1 was never a fact about sensing, only about soil moisture. Water
moves the one value whose property the domain's valuation is denominated in; the rest are
untouched by a dose, which is what makes a thermometer on a watered pot behave like a thermometer.

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


def place(doc: dict, pointer: str, value: float) -> None:
    """Put `value` where an RFC 6901 pointer says it goes, making the objects on the way.

    The mirror of what an agent does to read it, and deliberately a separate implementation: a
    board does not import the reader's code, and one that could would stop being a stand-in for
    something that cannot. Unescaping is ordered — `~1` to `/` FIRST, then `~0` to `~` — because
    reversing it decodes a literal `~1` written `~01` as a separator.

    Object keys only. An array index would need a length to grow to, and nothing here reports
    one; refusing is better than half-supporting it, since the failure would otherwise be a
    value quietly landing somewhere nobody reads.
    """
    if not pointer.startswith("/"):
        raise ValueError(f"{pointer!r} is not a JSON Pointer — it must start with '/'")
    tokens = [t.replace("~1", "/").replace("~0", "~") for t in pointer.split("/")[1:]]
    node = doc
    for token in tokens[:-1]:
        node = node.setdefault(token, {})
        if not isinstance(node, dict):
            raise ValueError(f"{pointer!r}: {token!r} is already a value, not an object")
    node[tokens[-1]] = value


class Value:
    """One property this device reports: where it goes in the message, and how it moves.

    Its own range and its own step, because a range was never a fact about sensing. A moisture
    fraction happens to run 0..1 and a temperature in degrees does not, and a board that reported
    both would be describing two different kinds of number down one wire — which is exactly what
    a KY-015 does.
    """

    def __init__(self, spec: dict) -> None:
        self.pointer = str(spec.get("pointer") or "/value")
        self.min = float(spec.get("min", 0.0))
        self.max = float(spec.get("max", 1.0))
        self.initial = float(spec.get("initial", self.min))
        self.drift = float(spec.get("drift", 0.0))
        # Only the value the domain's valuation is denominated in moves when water arrives. A
        # thermometer on a watered pot reads the same before and after, which is the whole
        # difference between modelling a property and modelling a number.
        self.litres_per_fraction = float(spec.get("litres", 0.0) or 0.0)
        self._drift_at_boot = self.drift
        self.value = self.clamp(self.initial)

    def clamp(self, v: float) -> float:
        return max(self.min, min(self.max, v))

    def reset(self) -> None:
        """Back to how it booted — the value AND the trend, because a trend someone set is part
        of the scenario they set up, not a property of the device."""
        self.value, self.drift = self.clamp(self.initial), self._drift_at_boot


class SimulatedSensor:
    """One device: the values it reports, a clock, and a connection."""

    def __init__(self) -> None:
        self.sensor_id = _env("SIM_SENSOR_ID")
        self.reading_topic = _env("SIM_READING_TOPIC")
        self.command_topic = os.environ.get("SIM_COMMAND_TOPIC") or ""
        self.dose_topic = os.environ.get("SIM_DOSE_TOPIC") or ""
        # `scheduled` keeps the interval it is given; `push` keeps its own. The agent's
        # capability follows from this, and neither branch knows that.
        self.mode = _env("SIM_SENSE_MODE", "scheduled").lower()

        # What this device reports, and where each one goes in its message. One entry for a
        # single-property board, several for a part that reports several down one line. Required
        # rather than defaulted: a board that reports nothing is not a board, and guessing a
        # range is how a thermometer ends up clamped to a fraction.
        self.values = [Value(spec) for spec in json.loads(_env("SIM_VALUES"))]
        if not self.values:
            raise SystemExit("SIM_VALUES is empty — a device that reports nothing is not one")
        seen = [v.pointer for v in self.values]
        if len(set(seen)) != len(seen):
            raise SystemExit(f"SIM_VALUES repeats a pointer {sorted(seen)} — two properties "
                             f"would overwrite each other in one message")
        self.tick_s = _float("SIM_TICK_SECONDS", 3)

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
        """One message carrying every property this device reports.

        One message and not one per value, because that is what the hardware does: a board wakes
        once, reads what it is wired to, and spends one radio transmission on the lot. Publishing
        per value would be cheaper to write and would stop exercising the thing that made all of
        this necessary — several sensors taking their own number out of one payload.
        """
        doc: dict = {"sensor": self.sensor_id}
        # The reading says which cadence it was taken under (#135) — scheduled mode only,
        # because a push device keeps its own clock and has no commanded cadence to receipt.
        # The real board reports the same field for the same reason: its RAM is cleared by
        # deep sleep, so the ack is its only testimony about the rhythm actually in force.
        if self.mode == "scheduled":
            doc["sleep_s"] = int(self.sleep_s)
        for v in self.values:
            place(doc, v.pointer, round(v.value, 3))
        self.client.publish(self.reading_topic, json.dumps(doc), qos=1)

    def _at(self, doc: dict) -> Value | None:
        """Which value a control verb is aimed at — `/value` unless it says otherwise.

        The default keeps every scenario that steers a single-property device working unchanged,
        while `"at"` reaches the others. One extra key rather than a second verb per property:
        the control surface should grow with what a device reports, not with what it might.
        """
        pointer = doc.get("at") or "/value"
        for v in self.values:
            if v.pointer == pointer:
                return v
        log.warning("%s: nothing is reported at %s — this device reports %s", self.sensor_id,
                    pointer, ", ".join(v.pointer for v in self.values))
        return None

    def _control(self, doc: dict) -> None:
        """Steer the simulation. NOT physics — this is a hand reaching into the model.

        Watering is deliberately not here: water arriving at soil is something the world does, so
        it comes over the dose topic and exercises the real actuation path. Routing it through
        here would mean the simulation quietly stopped testing whether watering works.

        What belongs here is what has no physical counterpart: putting the value somewhere to see
        what an agent does about it, and putting it back.
        """
        # `value` in, `value` out: the same word the reading payload uses, so nobody has to ask
        # what is being set. NOTE what is NOT renamed — `sleep_s` and `sense` are the REAL device
        # protocol, implemented by a physical board, and the whole claim of this program is that
        # nothing downstream can tell it from one. Tidying those would silently break every
        # flashed board.
        if isinstance(doc.get("value"), (int, float)):
            if (v := self._at(doc)) is not None:
                v.value = v.clamp(float(doc["value"]))
                log.info("%s: %s set to %.3f", self.sensor_id, v.pointer, v.value)
        if isinstance(doc.get("trend_per_tick"), (int, float)):
            # Signed, and it REPLACES the drift rather than adding to it: a positive trend is
            # a pot being rained on, which is a different world, not a wetter one.
            if (v := self._at(doc)) is not None:
                v.drift = -float(doc["trend_per_tick"])
                log.info("%s: %s trend now %+.4f per tick", self.sensor_id, v.pointer, -v.drift)
        if doc.get("reset"):
            # Everything, not just what `at` names: a reset puts the device back, and a board
            # half-reset is a scenario nobody meant to set up.
            for v in self.values:
                v.reset()
            log.info("%s: reset to %s", self.sensor_id,
                     ", ".join(f"{v.pointer}={v.value:.3f}" for v in self.values))
        if doc.get("publish"):
            self._publish()

    # --- the physics ---

    def _receive(self, ml: float) -> None:
        """Water arrived at the subject. How far it moves a reading is a fact about the pot.

        It moves only the values that say how much a litre is worth to them, which in practice is
        the one property the domain's valuation is denominated in. A thermometer sharing the board
        is not cooled by watering the plant, and a simulation in which it was would be teaching an
        agent something false about the world.
        """
        if ml <= 0:
            return
        for v in self.values:
            if v.litres_per_fraction > 0:
                v.value = v.clamp(v.value + (ml / 1000.0) / v.litres_per_fraction)
                log.info("%s: received %.0f ml -> %s=%.3f", self.sensor_id, ml, v.pointer, v.value)

    def _dry(self) -> None:
        for v in self.values:
            v.value = v.clamp(v.value - v.drift)

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
