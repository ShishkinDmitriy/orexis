"""Someone who waters the plants now and then, and never asks the society first.

This is the third-party impulse of #151 made into a resident: a human with a watering can, rain
through an open window — water that arrives at the soil without any agent bidding, any claim
issued, or any valve moving. The society's only defence against a signal that changes without
its doing is how it samples, and a world where that never happens is a world that flatters its
sampling policy.

**Its own container and its own credential, deliberately.** The first draft hid this inside the
simulated sensor, which was wrong twice: a pot does not water itself, and a stand-in that
secretly did could never be told from one whose physics were broken. The meddler is a separate
process on the far side of the wire, granted WRITE on each pot's `sim:rainTopic` and nothing
else — it cannot hear a reading, see an offer, or impersonate a valve, because the ACL never
lets rain near the society's channels. The valve's status topic stays the valve's testimony.

**The soil cannot tell.** A pour is `{"ml": N}`, the same shape a dose report carries, because
millilitres are millilitres to dirt. The simulated sensor takes rain and doses through the same
`_receive`, and whichever agent watches that pot simply sees moisture rise unexplained — which
is the entire point.

Timing is exponential per pot, with a mean of `MEDDLER_MEAN_DAYS` SIMULATED days converted
through the world's `MEDDLER_TIMESCALE` — under a pace of 24 (a world whose day is an hour) and a mean of 2, each pot is
visited about every other bench-hour. Pours are 150-500 ml, the size of a passing kindness
rather than a proper watering.

Configured entirely by environment, like every stand-in: it is told its topics, never the world.
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

log = logging.getLogger("meddler")


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise SystemExit(f"{name} is required — a meddler is configured exactly as a "
                         f"device is, told its topics and nothing else")
    return value


class Meddler:
    """One wanderer, several pots, no schedule anyone could learn."""

    def __init__(self) -> None:
        self.topics = [str(t) for t in json.loads(_env("MEDDLER_TOPICS"))]
        if not self.topics:
            raise SystemExit("MEDDLER_TOPICS is empty — a meddler with nothing to water is "
                             "not one")
        self.mean_days = float(_env("MEDDLER_MEAN_DAYS"))
        self.timescale = float(_env("MEDDLER_TIMESCALE", "1"))
        if self.mean_days <= 0 or self.timescale <= 0:
            raise SystemExit("MEDDLER_MEAN_DAYS and MEDDLER_TIMESCALE must be positive — a "
                             "world that wants no meddling states no `sim:strayDoseMeanDays`")
        self.rng = random.Random()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"orexis-meddler-{self.rng.randint(0, 1 << 24):06x}")
        self.client.username_pw_set(_env("MQTT_USERNAME"), _env("MQTT_PASSWORD"))
        self._stop = threading.Event()
        # One independent clock per pot: kindness is not coordinated.
        self._due = {topic: self._interval_s() for topic in self.topics}

    def _interval_s(self) -> float:
        """Real seconds until the next visit to one pot: exponential around the stated mean.

        Exponential rather than uniform because a passer-by has no memory — the chance of
        being watered in the next minute never depends on how long it has been, which is
        exactly the property that makes the arrival unlearnable by cadence alone.
        """
        mean_real_s = self.mean_days * 86400.0 / self.timescale
        return self.rng.expovariate(1.0 / mean_real_s)

    def pour(self, topic: str) -> None:
        ml = round(self.rng.uniform(150, 500))
        # qos 1 and never retained: rain that arrived is an event, and rain the broker
        # replayed onto a restarting sensor would be a flood nobody poured.
        self.client.publish(topic, json.dumps({"ml": ml}), qos=1)
        log.info("watered %s with %d ml — nobody asked", topic, ml)

    def _loop(self) -> None:
        last = time.monotonic()
        while not self._stop.is_set():
            self._stop.wait(min(30.0, min(self._due.values())))
            now = time.monotonic()
            elapsed, last = now - last, now
            for topic in self.topics:
                self._due[topic] -= elapsed
                if self._due[topic] <= 0:
                    self.pour(topic)
                    self._due[topic] = self._interval_s()

    def run(self) -> None:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        self.client.connect(_env("MQTT_HOST"), int(_env("MQTT_PORT")))
        self.client.loop_start()
        log.info("wandering among %d pot(s), one visit per ~%.1f simulated day(s) each",
                 len(self.topics), self.mean_days)
        waiter = threading.Thread(target=self._loop, daemon=True)
        waiter.start()
        signal.sigwait({signal.SIGINT, signal.SIGTERM})
        log.info("meddler leaving")
        self._stop.set()
        self.client.loop_stop()
        self.client.disconnect()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    Meddler().run()


if __name__ == "__main__":
    main()
