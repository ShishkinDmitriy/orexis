"""`create`: the email transport brought up — the agent's mailbox, which the runtime makes where a translator is in
a chat by email (`agent.runtime.TRANSPORTS`) and it is told to connect, then starts: it polls the mailbox."""

from __future__ import annotations

from .driver import Email


def create(runtime) -> Email:
    """Bring the agent's mailbox up from the environment: the part the runtime starts — attached, and polling."""
    return Email.connect(runtime.me)
