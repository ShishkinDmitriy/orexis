"""What a perceiving agent must believe. Declared here, next to the code that reads it.

The asymmetry between the blocks is the capability split made concrete: every perceiver
decides how stale a reading may be, because that is about belief; only one that can say WHEN
is asked for an interval, because only it could apply one. Nothing central lists these — the
block travels with the module that reads it.

A future `ag:Polling` module would read the same two figures, since they are an interval
either way — the difference is only whose timer runs it.

Vocabulary: capabilities/perception/ontology.ttl. Rules: capabilities/perception/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agora.beliefs import Block

from .terms import LISTENING, SUBSCRIBING


@dataclass(frozen=True)
class SubscribingBeliefs:
    """ag:Subscribing — how closely this agent watches, and how stale it lets a reading get.

    The two intervals are the agent's policy; the device merely keeps to whichever is in
    force. They are how long the device may REST, not the period between readings: the
    observed gap is this plus whatever waking costs, which on a sleeping board is seconds.
    """

    fast_sleep_s: int
    slow_sleep_s: int
    max_age_s: int


@dataclass(frozen=True)
class ListeningBeliefs:
    """ag:Listening — only the freshness rule. There is no interval to hold: the hardware
    keeps its own clock, so requiring one would be requiring a fiction."""

    max_age_s: int


SUBSCRIBING_BLOCK = Block(
    capability=SUBSCRIBING,
    cls=SubscribingBeliefs,
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
