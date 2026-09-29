"""`start`: the MQTT transport brought up from the environment and started — what the runtime calls
where this package's premise holds and it is told to connect (a-package-starts-itself). Its stop,
answered, closes the client."""

from __future__ import annotations

from .driver import Mqtt


def start(runtime):
    """Connect the agent's side of the bus as the environment says, start it — listening, attached,
    asking after missing readings — and answer how to stop it."""
    member = Mqtt.connect(runtime.me)
    member.start(runtime)
    return member.stop
