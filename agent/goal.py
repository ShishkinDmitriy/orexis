"""What an agent is trying to bring about, in the one shape a deliberator ranges over.

Here and not in a package because a goal is a MENTAL STATE, and those are the kernel's — the
same reason `ag:Obligation` and `ag:Intention` moved into the agora namespace when the mind
was named (the-mind-is-six-graphs). Two packages need this type and neither may import the
other: `desire` produces goals, `deliberation` consumes them, and the only thing they are
allowed to share is a kernel word.

**Two sources, one currency.** A goal is either a stake — a property of the subject this agent
acts for, wanted inside a region — or a duty, a claim someone else holds against it. They are
deliberately the same type: an agent's whole conduct is wants it pursues through affordances,
and a deliberator that had to ask which kind it was holding would be the second decision path
this design exists to avoid. What differs is only where the urgency came from, and that is
recorded in the graph rather than in a flag anyone branches on. See
knowledge/decisions/an-obligation-is-a-desire-someone-else-sourced.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Goal:
    """One thing wanted, and how badly.

    `urgency` is unit-free in both cases and that is the whole point of the type: a stake's
    comes from the survival envelope (how much room is left before the subject ends), a duty's
    from the redeem window (how much time is left before the claim expires), and the two become
    comparable without either knowing how the other was computed. "My plant is dying" and "I owe
    fern a litre" finally rank against each other.
    """

    uri: str  # the goal's own node: a shape this agent holds, or an obligation
    urgency: float  # 0 = content, 1 = at the edge of what it can bear or of its deadline

    # A stake's two: what is wanted, and what it currently reads. `value` is None when nothing
    # has been observed, which is a gap and not a zero — see gap.rq.
    observed_property: str | None = None
    value: float | None = None

    # A duty's two: the claim it came from and whom it is owed to. A stake has neither, which
    # is what `is_duty` reads — no kind field, because a flag that can disagree with the data
    # beside it is a flag that eventually does.
    claim: str | None = None
    owed_to: str | None = None

    # Whether anything is being asked of this agent YET. A duty nobody has presented stands and
    # may be hot, and still must not be acted on: the holder is waiting for its own watch to be
    # live, and a host that doses early spends the water where nothing is looking. Always true
    # for a stake — a plant does not ask.
    pursuable: bool = True

    #  What state the goal is in, in its own kind's vocabulary: `met`, `unmet` or `unmeasured`
    #  for a stake, `standing` or `demanded` for a duty. Carried rather than inferred from
    #  urgency, and that distinction is not academic — urgency is 0 only exactly at a region's
    #  centre, so "urgency > 0" counts a barrel sitting comfortably inside 1-5 as unmet. It
    #  read that way on the bench for about ten minutes and made a calm society look stuck.
    state: str | None = None

    @property
    def is_met(self) -> bool:
        """Nothing is wanted here right now. False for a duty, which is never *met* — it is
        discharged, and a discharged debt is history rather than a goal."""
        return self.state == "met"

    @property
    def is_duty(self) -> bool:
        return self.claim is not None
