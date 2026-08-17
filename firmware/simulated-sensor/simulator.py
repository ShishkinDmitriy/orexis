"""A sensor that does not exist, speaking exactly what one would.

This is FIRMWARE, in every sense that matters. It runs on the far side of the wire, it is told
its identity and its topics the way a board is told them in `config.h`, and it knows nothing
about agents, worlds or belief bases. It is in Python and beside two PlatformIO projects because
what a directory under `firmware/` answers is *what runs on the device*, and the language a
device happens to run is not the interesting part.

**The whole claim is that nothing downstream can tell.** So this publishes what the real board
publishes, byte for byte — obeys the same retained `{"sleep_s": N}`, answers the same
`{"sense": true}`, and holds the same constitutional floor and ceiling on its cadence. An agent
wired to one of these derives `ag:Subscribing` and runs the ordinary sensing module, because
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

**A temperature is not a fraction.** Each value lives inside its own range, from its own start,
at its own rates — because 0..1 was never a fact about sensing, only about soil moisture. Water
moves the one value whose property the domain's valuation is denominated in; the rest are
untouched by a dose, which is what makes a thermometer on a watered pot behave like a thermometer.

**The physics run on the clock, at the world's pace.** Drying is stated per simulated day and
integrated over real time times `SIM_TIMESCALE` (ag:timeScale), so a pot loses what the day
costs it however often anyone looks — the per-reading drift this replaces made a closely-watched
pot dry faster, which is backwards. A daily sine (`swing`) gives a room its afternoons. And the
instrument is imperfect on purpose: Gaussian grain on every reading and the occasional outright
spike, applied at report time and never fed back — an agent reared on a world that never
glitches would trust its first real probe too much.

**Rain is somebody else's container.** The meddler (see `firmware/simulated-meddler/`) waters
pots on its own schedule over `SIM_RAIN_TOPIC`; the soil here takes its millilitres exactly as
it takes a valve's, because soil cannot tell a bought litre from a kind stranger's — and that
indistinguishability is precisely what the society's sampling has to cope with (#151).

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
import math
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

    Its own range and its own rates, because a range was never a fact about sensing. A moisture
    fraction happens to run 0..1 and a temperature in degrees does not, and a board that reported
    both would be describing two different kinds of number down one wire — which is exactly what
    a KY-015 does.

    **The physics run on the clock, not on the readings.** `loses` is units per SIMULATED DAY,
    integrated over real elapsed time times the world's timescale — the old per-tick drift made
    a closely-watched pot dry faster than an ignored one, which is backwards, and became
    unmissable once the agents started varying how closely they watch. `swing` is the amplitude
    of a daily sine around the value, for properties with a diurnal cycle: a room's temperature
    has one, soil moisture does not.
    """

    def __init__(self, spec: dict, timescale: float = 1.0) -> None:
        self.pointer = str(spec.get("pointer") or "/value")
        self.min = float(spec.get("min", 0.0))
        self.max = float(spec.get("max", 1.0))
        self.initial = float(spec.get("initial", self.min))
        self.loses_per_day = float(spec.get("loses", 0.0))
        self.daily_swing = float(spec.get("swing", 0.0))
        # Only the value the domain's valuation is denominated in moves when water arrives. A
        # thermometer on a watered pot reads the same before and after, which is the whole
        # difference between modelling a property and modelling a number.
        self.litres_per_fraction = float(spec.get("litres", 0.0) or 0.0)
        self.timescale = timescale
        # `trend_per_s` steering: an operator-set drift, in units per real second, REPLACING
        # the modelled drying while set — a positive trend is rain, which is a different world
        # rather than a wetter one.
        self.forced_drift_per_s: float | None = None
        self.value = self.clamp(self.initial)

    def clamp(self, v: float) -> float:
        return max(self.min, min(self.max, v))

    def advance(self, dt_real_s: float) -> None:
        """Age this value by real elapsed seconds: the day's drying, at the world's pace."""
        if self.forced_drift_per_s is not None:
            self.value = self.clamp(self.value + self.forced_drift_per_s * dt_real_s)
            return
        sim_days = dt_real_s * self.timescale / 86400.0
        self.value = self.clamp(self.value - self.loses_per_day * sim_days)

    def read(self, sim_time_s: float) -> float:
        """What the world holds at this instant: the base plus where the day's cycle sits.

        The swing is applied at read time rather than integrated, because a cycle is a position
        in the day and not an accumulation — integrate it and a value read only at noon would
        ratchet upward forever.
        """
        if not self.daily_swing:
            return self.value
        phase = (sim_time_s % 86400.0) / 86400.0
        return self.clamp(self.value + self.daily_swing * math.sin(2 * math.pi * phase))

    def reset(self) -> None:
        """Back to how it booted — the value AND any forced trend, because a trend someone set
        is part of the scenario they set up, not a property of the device."""
        self.value, self.forced_drift_per_s = self.clamp(self.initial), None


class SimulatedSensor:
    """One device: the values it reports, a clock, and a connection."""

    def __init__(self) -> None:
        self.sensor_id = _env("SIM_SENSOR_ID")
        self.reading_topic = _env("SIM_READING_TOPIC")
        self.command_topic = os.environ.get("SIM_COMMAND_TOPIC") or ""
        # One or several: a pot takes water on its valve's channel; a SOURCE loses it on
        # every valve that draws from it (the barrel learns to run dry). Comma-joined env.
        self.dose_topics = {t for t in (os.environ.get("SIM_DOSE_TOPIC") or "").split(",") if t}
        # Water from OUTSIDE the society — the meddler's channel (ag:rainTopic). Arrives at the
        # soil exactly as a dose does, which is the point: the pot cannot tell a bought litre
        # from a kind stranger's, and neither can the agent except by not having decided it.
        self.rain_topic = os.environ.get("SIM_RAIN_TOPIC") or ""
        # `scheduled` keeps the interval it is given; `push` keeps its own. The agent's
        # capability follows from this, and neither branch knows that.
        self.mode = _env("SIM_SENSE_MODE", "scheduled").lower()

        # The world's clock (ag:timeScale): simulated seconds per real second. Physics integrate
        # real elapsed time times this, so one bench hour can hold one simulated day.
        self.timescale = _float("SIM_TIMESCALE", 1.0)

        # What this device reports, and where each one goes in its message. One entry for a
        # single-property board, several for a part that reports several down one line. Required
        # rather than defaulted: a board that reports nothing is not a board, and guessing a
        # range is how a thermometer ends up clamped to a fraction.
        self.values = [Value(spec, self.timescale) for spec in json.loads(_env("SIM_VALUES"))]
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
        # How long a scheduled device waits to be RELEASED after publishing (#152), before
        # giving up on the agent for this wake — the stand-in for RELEASE_WAIT_MS.
        self.release_wait_s = _float("SIM_RELEASE_WAIT_S", 5)
        self._released = threading.Event()

        # Announce-on-crossing (#151): the agent commands a band PER WATCHED CHANNEL beside
        # the cadence — {"watch": {"/value": [0.45, 0.65], "/temperature": [18, 24]}} — and
        # this device checks every banded value between heartbeats the way a real board's ULP
        # would, waking early the moment ANY of them leaves its band. Empty until commanded; a
        # world whose channels state no AlarmProcedure never sends one, so this stays
        # dormant exactly as unflashed firmware would. A stand-in may watch every channel it
        # has, where real silicon watches only what its ULP can reach — the honest asymmetry
        # the vocabulary states per sensor.
        self.alarm: dict[str, tuple[float, float]] = {}
        self.alarm_period_s = _float("SIM_ALARM_PERIOD_S", 1.0)
        # The constitutional debounce (#180): N consecutive breaching looks before a wake,
        # mirroring the boards' ULP counter so the bench rehearses what the silicon does.
        # Injected by the compose generator from sensing:alarmPersistenceLooks.
        self.alarm_persist = int(_float("SIM_ALARM_PERSIST_LOOKS", 2))
        self._breach_looks = 0
        # A PUSH sentinel's band is baked at "flash" — SIM_ALARM is its config.h, since a
        # device that takes no orders can still keep a promise the world wrote. A scheduled
        # device ignores this and is commanded instead.
        if self.mode == "push" and os.environ.get("SIM_ALARM"):
            self.alarm = {str(ptr): (float(band[0]), float(band[1]),
                                     float(band[2]) if len(band) > 2 else None)
                          for ptr, band in json.loads(os.environ["SIM_ALARM"]).items()}

        # Measurement error — a property of this firmware's fidelity, like LED_BRIGHTNESS on
        # the real board: not generated from the world, env-overridable, stated as fractions of
        # each value's span so one pair of knobs is honest about a fraction and a temperature
        # alike. Gaussian grain on every reading, and the occasional outright lie: a capacitive
        # probe with a marginal wire does both, and an agent trained on a world that never
        # glitches would trust its first real board too much.
        self.noise_span = _float("SIM_NOISE_SPAN", 0.004)
        self.spike_chance = _float("SIM_SPIKE_CHANCE", 0.01)
        self.spike_span = _float("SIM_SPIKE_SPAN", 0.25)
        self.rng = random.Random()
        self._advanced_at = time.monotonic()

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
        for topic in sorted(self.dose_topics):
            client.subscribe(topic)
        if self.rain_topic:
            client.subscribe(self.rain_topic)
        log.info("%s up — publishing %s every %ss (%s)", self.sensor_id, self.reading_topic,
                 self.sleep_s, self.mode)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            doc = json.loads(msg.payload)
        except (ValueError, TypeError):
            log.warning("%s: unreadable payload on %s", self.sensor_id, msg.topic)
            return

        if msg.topic and (msg.topic in self.dose_topics or msg.topic == self.rain_topic):
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
        if isinstance(doc.get("alarm"), dict):
            # [low, high] or [low, high, delta] — the optional third element is the DEVIATION
            # limit: how far the value may drift from the last REPORT before that alone is
            # worth waking for, band or no band.
            self.alarm = {str(pointer): (float(band[0]), float(band[1]),
                                         float(band[2]) if len(band) > 2 else None)
                          for pointer, band in doc["alarm"].items()
                          if isinstance(band, (list, tuple)) and len(band) >= 2}
        if isinstance(doc.get("sleep_s"), (int, float)):
            asked = float(doc["sleep_s"])
            self.sleep_s = max(self.min_sleep_s, min(self.max_sleep_s, asked))
            # An answer carrying a cadence is the release (#152) — a sense nudge is not, exactly
            # as on the board: a nudge republishes, and the answer to THAT reading releases.
            self._released.set()
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
        if getattr(self, "_woke_by_alarm", False):
            doc["wake"] = "alarm"   # this reading exists because the value moved
            self._woke_by_alarm = False
        # What the world holds is one thing; what the instrument says is another. The grain and
        # the occasional spike are applied at REPORT time and never fed back into the value —
        # measurement error is about the reading, and physics that inherited it would drift.
        sim_time = time.time() * self.timescale
        for v in self.values:
            true = v.read(sim_time)
            v.last_reported = true   # what the deviation limit measures drift FROM
            span = v.max - v.min
            reported = true + self.rng.gauss(0.0, self.noise_span * span)
            if self.rng.random() < self.spike_chance:
                reported += self.rng.choice((-1.0, 1.0)) * self.spike_span * span
                log.info("%s: glitch on %s — reporting %.3f while the world holds %.3f",
                         self.sensor_id, v.pointer, v.clamp(reported), true)
            place(doc, v.pointer, round(v.clamp(reported), 3))
        self.client.publish(self.reading_topic, json.dumps(doc), qos=1)

    def _at(self, doc: dict) -> Value | None:
        """Which value a control verb is aimed at — `/value` unless it says otherwise.

        The default keeps every scenario that steers a single-property device working unchanged,
        while `"at"` reaches the others. One extra key rather than a second verb per property:
        the control surface should grow with what a device reports, not with what it might.
        """
        # Defaulting to the sole value's own pointer keeps a single-property device steerable
        # without naming it — and "/value" stays the fallback for the multi-value case, since
        # guessing among several would aim the operator's hand at random.
        pointer = doc.get("at") or (self.values[0].pointer if len(self.values) == 1
                                    else "/value")
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
        if isinstance(doc.get("trend_per_s"), (int, float)):
            # Signed, in units per REAL second, and it REPLACES the modelled drying rather than
            # adding to it: a positive trend is a pot being rained on, which is a different
            # world, not a wetter one. Per second because the tick left the physics — this verb
            # was trend_per_tick when the tick paced them.
            if (v := self._at(doc)) is not None:
                v.forced_drift_per_s = float(doc["trend_per_s"])
                log.info("%s: %s trend now %+.5f per second", self.sensor_id, v.pointer,
                         v.forced_drift_per_s)
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
            # The SIGN of the conversion is which side of the wire this value is on: a pot's
            # litresPerFraction is positive (water raises the valued property), a source's
            # stated dose effect is negative (the litre that fills a pot lowers the barrel
            # it left). Zero stays "water means nothing to this value".
            if v.litres_per_fraction:
                v.value = v.clamp(v.value + (ml / 1000.0) / v.litres_per_fraction)
                log.info("%s: received %.0f ml -> %s=%.3f", self.sensor_id, ml, v.pointer, v.value)

    def _advance(self) -> None:
        """Move the physics by however much real time has passed, at the world's pace.

        Called once per wake, BEFORE publishing — so the drying that happened while the board
        slept is in the soil by the time the soil is read, exactly as it would be for hardware.
        The old `_dry` moved one step per call, which made the physics an artifact of attention:
        a closely-watched pot dried faster than an ignored one.
        """
        now = time.monotonic()
        dt = now - self._advanced_at
        self._advanced_at = now
        for v in self.values:
            v.advance(dt)

    def _alarmed(self) -> bool:
        """Whether ANY watched value has left its band OR jolted since its last report.

        Two limits per channel, exactly as a process alarm has always had them: HI/LO (the
        band) and DEVIATION (more than delta from the last reported value — the stranger
        watering a comfortable pot, the leak still in-range). The TRUE values, not the
        reported ones: a real ULP compares the ADC, and the grain and the spikes are
        properties of the REPORT (#163) — a board that woke for its own measurement noise
        would be a boy crying wolf at his own echo.
        """
        if not self.alarm:
            return False
        sim_time = time.time() * self.timescale
        for value in self.values:
            band = self.alarm.get(value.pointer)
            if band is None:
                continue
            now = value.read(sim_time)
            if now < band[0] or now > band[1]:
                return True
            last = getattr(value, "last_reported", None)
            if band[2] is not None and last is not None and abs(now - last) > band[2]:
                return True
        return False

    def _news(self) -> bool:
        """One look's breach, held to the persistence figure (#180) — the ULP counter's twin.

        A breaching look increments, an in-window look resets, and only the Nth consecutive
        breach is news. A stand-in has no ADC to glitch, so for IT this is pure latency — but
        the bench exists to rehearse what the boards do, and a board that waits two looks must
        be rehearsed waiting two looks, or the simulation would promise a faster messenger
        than any real pot has."""
        if self._alarmed():
            self._breach_looks += 1
        else:
            self._breach_looks = 0
        if self._breach_looks >= self.alarm_persist:
            self._breach_looks = 0
            return True
        return False

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
            self._advance()
            if self.mode == "push":
                # A push device keeps its own tick and waits for nobody — but a SENTINEL
                # watches its baked band between ticks, and a crossing ends the wait early
                # exactly as it ends a scheduled sleep.
                self._publish()
                slept = 0.0
                while slept < self.tick_s and not self._stop.is_set():
                    step = min(self.alarm_period_s, self.tick_s - slept)
                    self._stop.wait(step)
                    slept += step
                    self._advance()
                    if self._news():
                        self._woke_by_alarm = True
                        log.info("%s: crossed the baked band — the sentinel speaks",
                                 self.sensor_id)
                        break
                continue
            # A scheduled device publishes and then WAITS TO BE RELEASED (#152): the agent
            # answers every reading, the answer carries the cadence, and the sleep below runs
            # on what the release said rather than on what was known before the publish. The
            # timeout is the dead-agent case, exactly as on the board. The flag is lowered
            # first because the release must answer THIS reading — a leftover from the last
            # wake is memory, not permission.
            self._released.clear()
            self._publish()
            if not self._released.wait(self.release_wait_s):
                log.warning("%s: no release after %ss — the agent is not answering",
                            self.sensor_id, self.release_wait_s)
            # The heartbeat sleep — WATCHED (#151), where a band is commanded: physics advance
            # each watch-period and a crossing ends the sleep early, exactly as a ULP would end
            # a deep sleep. The next publish then says WHY it happened.
            slept = 0.0
            while slept < self.sleep_s and not self._stop.is_set():
                step = min(self.alarm_period_s, self.sleep_s - slept)
                self._stop.wait(step)
                slept += step
                self._advance()
                if self._news():
                    self._woke_by_alarm = True
                    log.info("%s: crossed the commanded band — waking off-cadence, "
                             "the world changed and this board is its messenger",
                             self.sensor_id)
                    break


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    SimulatedSensor().run()


if __name__ == "__main__":
    main()
