"""Executor — the trusted actuator (RPi side).

Consumes a validated capability grant and publishes a *bounded* valve command to the
pump-ESP32 over MQTT. Decides nothing; enforces single-use (jti) and a hard dose cap
(defence-in-depth even though the grant already passed the constitution). The pump is a
guarded subscriber that runs the fail-safe watchdog.

See knowledge/domain/executor.md.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Callable

from .clearing import Grant

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
    def __init__(self, publish: Publish, ml_per_second: float = 10.0, max_dose_ml: float = 1000.0):
        self.publish = publish
        self.ml_per_second = ml_per_second
        self.max_dose_ml = max_dose_ml  # hard edge cap (litres already cleared, but be safe)
        self._settled: set[str] = set()

    def command_for(self, grant: Grant) -> Command:
        ml = min(grant.amount_l * 1000.0, self.max_dose_ml)
        seconds = round(ml / self.ml_per_second, 2)
        return Command(
            jti=grant.jti,
            plant=grant.sub,
            scope=grant.scope,
            ml=round(ml, 1),
            seconds=seconds,
            round_id=grant.round_id,
        )

    def settle(self, grant: Grant) -> Command:
        """Publish the bounded command for a grant. Raises on replay (single-use)."""
        if grant.jti in self._settled:
            raise ValueError(f"replay: jti {grant.jti} already settled")
        cmd = self.command_for(grant)
        self.publish(f"actuators/{cmd.plant}/valve", asdict(cmd))
        self._settled.add(grant.jti)
        return cmd

    def settle_all(self, grants: list[Grant]) -> list[Command]:
        return [self.settle(g) for g in grants]


def mqtt_publisher(host: str, port: int):
    """A real MQTT publish sink (QoS 1). Returns (publish, client)."""
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host, port)
    client.loop_start()

    def publish(topic: str, payload: dict) -> None:
        client.publish(topic, json.dumps(payload), qos=1)

    return publish, client
