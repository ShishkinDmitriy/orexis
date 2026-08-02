"""Executor — the trusted actuator (RPi side).

Consumes a validated capability voucher and publishes a *bounded* valve command to the
pump-ESP32 over MQTT. Decides nothing; enforces single-use (jti) and a hard dose cap
(defence-in-depth even though the voucher already passed the constitution). The pump is a
guarded subscriber that runs the fail-safe watchdog.

See knowledge/domain/executor.md.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Callable

from . import signing
from .clearing import Voucher

# Publish sink: (topic, payload_dict) -> None. Injected so the executor is testable
# without a broker; the default factory below wires a real MQTT publisher.
Publish = Callable[[str, dict], None]


@dataclass(frozen=True)
class Command:
    jti: str
    plant: str
    scope: str
    ml: float
    seconds: float
    round_id: str


class Executor:
    def __init__(
        self,
        publish: Publish,
        ml_per_second: float = 10.0,
        max_dose_ml: float = 1000.0,
        host_key=None,
        clearing_key=None,
    ):
        self.publish = publish
        self.ml_per_second = ml_per_second
        self.max_dose_ml = max_dose_ml  # hard edge cap (litres already cleared, but be safe)
        # v1 in-process: the settlement service holds both keys and co-signs the token.
        self.host_key = host_key
        self.clearing_key = clearing_key
        self._settled: set[str] = set()

    def command_for(self, voucher: Voucher) -> Command:
        ml = min(voucher.amount_l * 1000.0, self.max_dose_ml)
        seconds = round(ml / self.ml_per_second, 2)
        return Command(
            jti=voucher.jti,
            plant=voucher.sub,
            scope=voucher.scope,
            ml=round(ml, 1),
            seconds=seconds,
            round_id=voucher.round_id,
        )

    def settle(self, voucher: Voucher) -> Command:
        """Publish the bounded command for a voucher, co-signed (host + clearing) so the pump
        can verify the actuate boundary. Raises on replay (single-use)."""
        if voucher.jti in self._settled:
            raise ValueError(f"replay: jti {voucher.jti} already settled")
        cmd = self.command_for(voucher)
        payload = asdict(cmd)
        if self.host_key is not None and self.clearing_key is not None:
            data = signing.canonical(payload)  # the command fields (no sig yet)
            payload["match_sig"] = signing.sign(self.host_key, data)  # the seller authorises
            payload["val_sig"] = signing.sign(self.clearing_key, data)  # clearing validates
        self.publish(f"actuators/{cmd.plant}/valve", payload)
        self._settled.add(voucher.jti)
        return cmd

    def settle_all(self, vouchers: list[Voucher]) -> list[Command]:
        return [self.settle(g) for g in vouchers]


def verify_command(payload: dict, host_pub, clearing_pub) -> bool:
    """Pump-side check: the valve opens only on a token signed by BOTH host and clearing."""
    if host_pub is None or clearing_pub is None:
        return False
    match_sig = payload.get("match_sig")
    val_sig = payload.get("val_sig")
    if not match_sig or not val_sig:
        return False
    cmd = {k: v for k, v in payload.items() if k not in ("match_sig", "val_sig")}
    data = signing.canonical(cmd)
    return signing.verify(host_pub, data, match_sig) and signing.verify(clearing_pub, data, val_sig)


def mqtt_publisher(host: str, port: int):
    """A real MQTT publish sink (QoS 1). Returns (publish, client)."""
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host, port)
    client.loop_start()

    def publish(topic: str, payload: dict) -> None:
        client.publish(topic, json.dumps(payload), qos=1)

    return publish, client
