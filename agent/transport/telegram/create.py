"""`create`: the Telegram transport brought up — the agent's bot, which the runtime makes where a translator speaks
through one (`agent.runtime.TRANSPORTS`) and it is told to connect, then starts: it polls the bot."""

from __future__ import annotations

from .driver import Telegram


def create(runtime) -> Telegram:
    """Bring the agent's bot up from the environment: the part the runtime starts — attached, and polling."""
    return Telegram.connect(runtime.me)
