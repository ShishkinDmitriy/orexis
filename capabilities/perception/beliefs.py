"""What a perceiving agent must believe. Declared here, next to the code that reads it.

The asymmetry between the two blocks is the capability split made concrete: both agents
decide how stale a reading may be, because that is about belief; only the one that drives its
hardware is asked for a cadence, because only it could apply one. Nothing central lists these
— the block travels with the module that reads it.

Vocabulary: capabilities/perception/ontology.ttl. Rules: capabilities/perception/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agora.beliefs import Block

from .terms import LISTENING, POLLING


@dataclass(frozen=True)
class PollingBeliefs:
    """ag:Polling — how closely this agent watches, and how stale it lets a reading get."""

    fast_sleep_s: int
    slow_sleep_s: int
    max_age_s: int


@dataclass(frozen=True)
class ListeningBeliefs:
    """ag:Listening — only the freshness rule. There is no cadence to hold: the hardware
    pushes on its own clock, so requiring a cadence would be requiring a fiction."""

    max_age_s: int


POLLING_BLOCK = Block(
    capability=POLLING,
    cls=PollingBeliefs,
    terms={
        "fast_sleep_s": "fastSleepS",
        "slow_sleep_s": "slowSleepS",
        "max_age_s": "maxReadingAgeS",
    },
)

LISTENING_BLOCK = Block(
    capability=LISTENING,
    cls=ListeningBeliefs,
    terms={"max_age_s": "maxReadingAgeS"},
)
