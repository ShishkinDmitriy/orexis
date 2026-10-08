"""`create`: the HTTP transport brought up — its part, which the runtime makes where an observer's
sensor is a thing with a form (`agent.runtime.TRANSPORTS`) and it is told to connect, then starts: it polls each sensor it reads
(a-package-starts-itself)."""

from __future__ import annotations

from .driver import Http


def create(runtime) -> Http:
    """Bring the agent's side of the web up: the part the runtime starts — attached, and polling each of
    its sensors at the frequency the sensor states."""
    return Http.connect(runtime.me)
