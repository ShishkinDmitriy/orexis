"""A valve that does not exist, refusing exactly what a real one would refuse.

This is FIRMWARE, like `firmware/simulated-sensor/simulator.py` and for the same reason: it runs
on the far side of the wire, it is told its identity and its topics the way a board is told them
in `config.h`, and it knows nothing about agents, worlds, markets or belief bases. It sees a
command arrive and decides whether to open.

**The signature check is the whole point.** The old `capabilities/simulated-actuation` said so
plainly and then skipped it — "no signature, because there is nothing to convince" — which was
honest about what it did and wrong about what that cost. A market exists to make actuation safe:
the host authorises a match, clearing validates it, and a device opens only for a token carrying
both. A simulation that skipped that tested everything except the part anyone would worry about.
So this verifies, and a command missing either signature moves no water.

**It holds public keys only.** `host.pub` and `clearing.pub`, mounted read-only, exactly as a
board would carry them. There is no private key here and no way for this process to author a
command — if there were, the check would be theatre.

**Reporting is not optional.** Water reaching soil is physics, and physics has no wire. Between
containers the only way the simulated sensor can learn that water actually flowed is this
process saying so on `ag:statusTopic` — which is why it publishes there after dispensing and
stays silent when it refuses. `firmware/pump-valve` has always published a status "so the
executor knows water actually flowed"; this does the same thing for the same reason.

The verification below duplicates `orexis.signing.verify_command` rather than importing it: this
image holds `cryptography` and `paho` and not the orexis package, which is the point of it being
its own image. `backend/tests/test_simulated_valve.py` holds the two implementations to the same
answers, so the copy cannot drift in silence.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import random
import signal
import threading
import time

import paho.mqtt.client as mqtt
from cryptography.hazmat.primitives import serialization

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
log = logging.getLogger("valve")


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise SystemExit(f"{name} is required — this stand-in is told what it is, like a board")
    return value


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else default


def canonical(payload: dict) -> bytes:
    """Byte-for-byte what orexis.signing.canonical produces. Held to it by a test."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def verify(pub, data: bytes, sig_b64: str) -> bool:
    try:
        pub.verify(base64.b64decode(sig_b64), data)
        return True
    except Exception:
        return False


def verify_command(payload: dict, host_pub, clearing_pub) -> bool:
    """Open only for a token signed by BOTH the host and clearing.

    Deliberately the same shape as the kernel's: signature fields excluded from the canonical
    bytes, both signatures required, and any failure is a refusal rather than an exception.
    """
    if host_pub is None or clearing_pub is None:
        return False
    match_sig, val_sig = payload.get("match_sig"), payload.get("val_sig")
    if not match_sig or not val_sig:
        return False
    cmd = {k: v for k, v in payload.items() if k not in ("match_sig", "val_sig")}
    data = canonical(cmd)
    return verify(host_pub, data, match_sig) and verify(clearing_pub, data, val_sig)


class SimulatedValve:
    """One valve: two public keys, a limit, and a connection."""

    def __init__(self) -> None:
        self.valve_id = _env("VALVE_ID")
        self.command_topic = _env("VALVE_COMMAND_TOPIC")
        self.status_topic = _env("VALVE_STATUS_TOPIC")
        # Its own calibration, exactly as the real device's: the dose the market cleared is
        # capped by what THIS valve will pass, whatever anyone else believed.
        self.ml_per_second = _float("VALVE_ML_PER_SECOND", 10.0)
        self.max_dose_ml = _float("VALVE_MAX_DOSE_ML", 1000.0)

        self.host_pub = self._load("VALVE_HOST_PUB")
        self.clearing_pub = self._load("VALVE_CLEARING_PUB")
        if self.host_pub is None or self.clearing_pub is None:
            log.warning("%s: missing a public key — every command will be refused, which is the "
                        "safe direction but probably not what you meant", self.valve_id)

        # Single-use, by jti, as the real path enforces it. A replayed claim opens nothing.
        self.spent: set[str] = set()

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"orexis-valve-{self.valve_id}-{random.randint(0, 1 << 24):06x}")
        self.client.username_pw_set(_env("MQTT_USERNAME"), _env("MQTT_PASSWORD"))
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._stop = threading.Event()

    @staticmethod
    def _load(var: str):
        path = os.environ.get(var, "")
        if not path or not os.path.exists(path):
            return None
        with open(path, "rb") as fh:
            return serialization.load_pem_public_key(fh.read())

    # --- the wire ---

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code != 0:
            log.error("%s: refused by the broker (%s) — wrong credential, or the ACL does not "
                      "grant this principal", self.valve_id, reason_code)
            return
        client.subscribe(self.command_topic, qos=1)
        log.info("%s up — listening on %s, reporting on %s (max %.0f ml)",
                 self.valve_id, self.command_topic, self.status_topic, self.max_dose_ml)

    def _refuse(self, why: str, payload: dict) -> None:
        """Say nothing on the status topic. Silence is the report: no water flowed.

        Logged rather than published on purpose — a refusal that announced itself on the status
        topic would still be a message a simulated sensor might learn to water on, and the one
        thing this must not do is move water it declined to move.
        """
        log.warning("%s: REFUSED (%s) jti=%s", self.valve_id, why, payload.get("jti"))

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload)
        except (ValueError, TypeError):
            log.warning("%s: unreadable payload on %s", self.valve_id, msg.topic)
            return

        if not verify_command(payload, self.host_pub, self.clearing_pub):
            self._refuse("signature", payload)
            return

        jti = payload.get("jti")
        if jti in self.spent:
            self._refuse("replay", payload)
            return

        asked = float(payload.get("ml") or 0.0)
        if asked <= 0:
            self._refuse("nothing to dispense", payload)
            return
        # The device's own ceiling, applied after the signature and regardless of what cleared.
        # A real valve does this too: two independent limits, because the interesting failures
        # are the ones where one of them is wrong.
        ml = min(asked, self.max_dose_ml)
        if ml < asked:
            log.warning("%s: capping %.0f ml at its own limit of %.0f",
                        self.valve_id, asked, self.max_dose_ml)

        seconds = ml / self.ml_per_second
        time.sleep(min(seconds, 2.0))  # the pour, abbreviated; nothing downstream times it
        self.spent.add(jti)

        report = {"valve": self.valve_id, "jti": jti, "plant": payload.get("plant"),
                  "ml": round(ml, 1), "seconds": round(seconds, 2), "ok": True}
        self.client.publish(self.status_topic, json.dumps(report), qos=1)
        log.info("%s: dispensed %.0f ml over %.1fs -> %s", self.valve_id, ml, seconds,
                 self.status_topic)

    # --- the loop ---

    def run(self) -> None:
        # Blocked before any thread starts, so this thread is the one that wakes and the paho
        # loop inherits the mask. An unhandled signal is DISCARDED for a container's PID 1 — the
        # rule that once made agents take ten seconds and a SIGKILL to stop.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        self.client.connect(_env("MQTT_HOST"), int(_env("MQTT_PORT")))
        self.client.loop_start()
        try:
            signal.sigwait({signal.SIGINT, signal.SIGTERM})
        finally:
            log.info("%s shutting down", self.valve_id)
            self.client.loop_stop()
            self.client.disconnect()


if __name__ == "__main__":
    SimulatedValve().run()
