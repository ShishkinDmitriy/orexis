"""`start`: the HTTP transport brought up and started — what the runtime calls where this package's
premise holds and it is told to connect (a-package-starts-itself). It polls each sensor it reads."""

from __future__ import annotations

from .driver import Http


def start(runtime):
    """Bring the agent's side of the web up and start it — attached, and polling each of its
    sensors at the frequency the sensor states."""
    Http.connect(runtime.me).start(runtime)
