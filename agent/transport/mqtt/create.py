"""`create`: the MQTT transport brought up from the environment — its part, which the runtime makes
where a role it is loaded for needs it (`agent.runtime.TRANSPORTS`) and it is told to connect, then starts and stops
(a-package-starts-itself)."""

from __future__ import annotations

from .driver import Mqtt


def create(runtime) -> Mqtt:
    """Connect the agent's side of the bus as the environment says: the part the runtime links, starts
    — listening, attached, asking after missing readings — and stops."""
    return Mqtt.connect(runtime.me)
