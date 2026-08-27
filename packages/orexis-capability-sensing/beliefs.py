"""What a perceiving agent must believe. Declared here, next to the code that reads it.

The asymmetry between the blocks is the capability split made concrete: every perceiver
decides how stale a reading may be, because that is about belief; only one that can say WHEN
is asked for an interval, because only it could apply one. Nothing central lists these — the
block travels with the module that reads it.

A future `sensing:Polling` module would read the same two figures, since they are an interval
either way — the difference is only whose timer runs it.

Vocabulary: capabilities/sensing/ontology.ttl. Rules: capabilities/sensing/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.beliefs import Picks


from .terms import LISTENING, SUBSCRIBING, term


@dataclass(frozen=True)
class SubscribingBeliefs:
    """sensing:Subscribing — how closely this agent watches, and how stale it lets a reading get.

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
    """sensing:Listening — only the freshness rule, and here it IS an absolute.

    The device keeps its own clock and takes no orders, so there is no interval for the agent to
    be relative to. All it can state is how long it will wait before deciding the thing has gone
    quiet. That asymmetry with sensing:Subscribing is the point: the two capabilities differ in who
    holds the clock, and the freshness rule differs the same way."""

    max_age_s: int


@dataclass(frozen=True)
class AlarmBeliefs:
    """sensing:alarmDeltaFraction — what this agent counts as a jolt.

    A block of its own rather than a fourth field above, because its ABSENCE is meaningful
    where a missing cadence is an authoring error: an agent that states no pick commands
    band-only alarms, and `read_optional` is how a decision said by omission is read. The
    family's figure in ontology.ttl is deliberately NOT a fallback here — a pick must be the
    agent's own to be revisable, since a revision rewrites the agent's graph and nothing else.
    """

    delta_fraction: float


SUBSCRIBING_PICKS = Picks(
    capability=SUBSCRIBING,
    cls=SubscribingBeliefs,
    terms={
        "fast_sleep_s": term("fastSleepS"),
        "slow_sleep_s": term("slowSleepS"),
        "grace_s": term("readingGraceS"),
    },
)

ALARM_PICKS = Picks(
    capability=SUBSCRIBING,
    cls=AlarmBeliefs,
    terms={"delta_fraction": term("alarmDeltaFraction")},
)

LISTENING_PICKS = Picks(
    capability=LISTENING,
    cls=ListeningBeliefs,
    terms={"max_age_s": term("maxReadingAgeS")},
)
