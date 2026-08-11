"""What a perceiving agent must believe. Declared here, next to the code that reads it.

The asymmetry between the blocks is the capability split made concrete: every perceiver
decides how stale a reading may be, because that is about belief; only one that can say WHEN
is asked for an interval, because only it could apply one. Nothing central lists these — the
block travels with the module that reads it.

A future `perception:Polling` module would read the same two figures, since they are an interval
either way — the difference is only whose timer runs it.

Vocabulary: capabilities/perception/ontology.ttl. Rules: capabilities/perception/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.beliefs import Block


from .terms import LISTENING, SUBSCRIBING, term


@dataclass(frozen=True)
class SubscribingBeliefs:
    """perception:Subscribing — how closely this agent watches, and how stale it lets a reading get.

    The two intervals are the agent's policy; the device merely keeps to whichever is in
    force. They are how long the device may REST, not the period between readings: the
    observed gap is this plus whatever waking costs, which on a sleeping board is seconds.
    """

    fast_sleep_s: int
    slow_sleep_s: int
    # Not an absolute age. This agent CHOOSES the interval, so staleness means "did not report
    # within the interval I asked for, plus this much slack" — a board's wake time and a late
    # wifi association. An absolute limit would contradict the agent's own instruction: it
    # cannot both decide that 600s between looks is acceptable and refuse a 120s-old number.
    grace_s: int


@dataclass(frozen=True)
class ListeningBeliefs:
    """perception:Listening — only the freshness rule, and here it IS an absolute.

    The device keeps its own clock and takes no orders, so there is no interval for the agent to
    be relative to. All it can state is how long it will wait before deciding the thing has gone
    quiet. That asymmetry with perception:Subscribing is the point: the two capabilities differ in who
    holds the clock, and the freshness rule differs the same way."""

    max_age_s: int


SUBSCRIBING_BLOCK = Block(
    capability=SUBSCRIBING,
    cls=SubscribingBeliefs,
    terms={
        "fast_sleep_s": term("fastSleepS"),
        "slow_sleep_s": term("slowSleepS"),
        "grace_s": term("readingGraceS"),
    },
)

LISTENING_BLOCK = Block(
    capability=LISTENING,
    cls=ListeningBeliefs,
    terms={"max_age_s": term("maxReadingAgeS")},
)
