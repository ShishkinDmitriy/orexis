"""What an agent that simulates its subject must believe.

Only the freshness rule, and how often it looks. It holds no interval to *give* anything —
there is nothing to instruct — so unlike ag:Subscribing these numbers govern the agent's own
loop and nobody else's.

Vocabulary: capabilities/simulated-sensing/ontology.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agora.beliefs import Block

from .terms import SIMULATED_SENSING


@dataclass(frozen=True)
class SimulatedSensingBeliefs:
    """How closely this agent watches its model, and how stale it lets a reading get."""

    fast_sleep_s: int
    slow_sleep_s: int
    max_age_s: int


SIMULATED_SENSING_BLOCK = Block(
    capability=SIMULATED_SENSING,
    cls=SimulatedSensingBeliefs,
    terms={
        "fast_sleep_s": "fastSleepS",
        "slow_sleep_s": "slowSleepS",
        "max_age_s": "maxReadingAgeS",
    },
)
