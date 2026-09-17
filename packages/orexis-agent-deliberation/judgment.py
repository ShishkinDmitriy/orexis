"""How badly one desire is wanted right now — a JUDGMENT, made every pass and never stored.

**This is not a desire.** A desire is DECLARED: a node a package's `desires.ru` writes into the
agent's roots graph at genesis, carrying its binding, its label and its met-test, and read back
by whoever asks. That is data, and `Desire` beside this file is its shape. What is here is what a
capability ANSWERS when the choir asks what it is pursuing: the desire's uri, how urgent it is on
a unit-free scale, what it currently reads, when it runs out. Nothing writes one down and nothing
loads one — every instance in the tree is built fresh inside the pass that ranks it.

The split was found rather than designed, by asking who constructs one: the ledger from a claim's
redeem window, hosting at a flat 1.0 per call, sensing's `ObservedJudgment` from the survival
envelope, and the kernel for the wants no module speaks for. Four sites, four ways of judging,
none of them reading a stored row. The word "desire" was doing both jobs and a repository could
not hand back either one without meaning the other. See
knowledge/decisions/a-desire-is-declared-and-a-judgment-is-made.md.

**Two sources, one currency.** A judgment is made either about a stake — a property of the
subject this agent acts for, wanted inside a region — or about an obligation, a claim someone
else holds against it. They are deliberately the same type: an agent's whole conduct is wants it
pursues through affordances, and a deliberator that had to ask which kind it was holding would be
the second decision path this design exists to avoid. What differs is only where the urgency came
from, and that is recorded in the graph rather than in a flag anyone branches on. See
knowledge/decisions/an-obligation-is-a-desire-someone-else-sourced.md.

Here and not in a package because judging what one wants is a MENTAL act, and those are the
kernel's — the same reason the obligation's premises and `progression:Intention` moved into the
orexis namespace when the mind was named (the-mind-is-six-graphs). Two packages need this type
and neither may import the other: a capability makes the judgments, deliberation consumes them,
and the only thing they are allowed to share is a kernel word.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Judgment:
    """One thing wanted, and how badly.

    `urgency` is unit-free in both cases and that is the whole point of the type: a stake's
    comes from the survival envelope (how much room is left before the subject ends), an obligation's
    from the redeem window (how much time is left before the claim expires), and the two become
    comparable without either knowing how the other was computed. "My plant is dying" and "I owe
    fern a litre" finally rank against each other.
    """

    uri: str  # the desire's own node: a shape this agent holds, or an obligation
    urgency: float  # 0 = content, 1 = at the edge of what it can bear or of its deadline

    # What it currently reads, where whoever contributed the want has a number for it — a
    # stake's reading, filled by sensing. None when nothing has been observed, which is a gap
    # and not a zero. WHAT the want is about is not on this type: a want is its node, and a
    # package that needs the property of one it holds walks to it in its own words
    # (the-stake-is-sensings-want; sensing's `ObservedDesire` carries `observed_property`).
    value: float | None = None

    # A obligation's two: the claim it came from and whom it is owed to. A stake has neither, which
    # is what `is_obligation` reads — no kind field, because a flag that can disagree with the data
    # beside it is a flag that eventually does.
    claim: str | None = None
    owed_to: str | None = None

    #  When the want stops being satisfiable — `orexis:expiresAt`, carried onto the Judgment so
    #  the planner can hold a candidate plan's landing time to the room left. #472: the
    #  obligation's binding is `orexis:Within`, and this is the deadline that binding reads —
    #  a legacy record from before the word behaves identically, because the deadline is the
    #  fact and the binding restates it. None for a stake, and None for a debt whose market
    #  stated no window: such a debt has no landing to miss.
    expires: datetime | None = None

    # An EPISTEMIC want's one: the instrument whose reading is wanted current. Present exactly
    # where the want is about knowing rather than about a number, which is what `is_epistemic`
    # reads — the same discipline as `is_obligation` above, and for the same reason: it is not a flag
    # saying what kind this is, it is the premise, and a want derived from an instrument is a
    # want about that instrument by construction.
    #
    # It is here because two wants can now be about ONE property — fern holds a region in its
    # moisture AND wants its probe to have spoken recently — and everything that used to ask
    # "the want about this property" had exactly one answer and now has two. Whose the
    # instrument IS stays out of the kernel: this is an IRI handed over, and the capability
    # that derived the want is the one that knows what to do with it.
    instrument: str | None = None

    # Whether anything is being asked of this agent YET. A obligation nobody has presented stands and
    # may be hot, and still must not be acted on: the holder is waiting for its own watch to be
    # live, and a host that doses early spends the water where nothing is looking. Always true
    # for a stake — a plant does not ask.
    pursuable: bool = True

    #  What state the desire is in, in its own kind's vocabulary: `met`, `unmet` or `unmeasured`
    #  for a stake, `met`, `stale` or `unmeasured` for an epistemic want — where it is read off
    #  the MEASURE, so a want scored maximal can never report as met, which it did while the
    #  label came from a staleness test that declines to judge at all without a published
    #  horizon — and `standing` or `demanded` for an obligation. Carried rather than inferred from
    #  urgency, and that distinction is not academic — urgency is 0 only exactly at the point
    #  being steered for, so "urgency > 0" counts a barrel sitting comfortably inside 1-5 as
    #  unmet. It read that way on the bench for about ten minutes and made a calm society look
    #  stuck. The split is now structural: the met-SHAPE governs the state and the MEASURE
    #  governs the urgency, and they are different questions on the desire's own node.
    state: str | None = None

    #  THE ROOT THIS WANT IS DERIVED UNDER (#618), or None for a root and for anything not
    #  derived from a want. An `orexis:Desire` is never pursued itself: the row the
    #  container presents in its place carries the root's own measure and names the root
    #  here, so a mark or a lookup by either name meets the same want.
    derived_from: str | None = None

    #  THE INSTANT AN `orexis:At` WANT HOLDS AT (#619), or None. A want derived under a root
    #  from a predicted crossing: judged as the world will be THEN, late past it, and its
    #  room is the stretch to it — which the container computes into `urgency` when it
    #  presents the want, since a time room is the kernel's arithmetic as a debt's is.
    holds_at: datetime | None = None

    #  WHEN THE READING THIS ROW JUDGES WAS TAKEN, or None where nothing was read — filled by
    #  whoever holds the reading (sensing). A pass for a want met at an instant drifts the
    #  reading's AGE at its root (#619, #625): the present is the world as it was OBSERVED, a
    #  drift that counted from the pass's clock would leave those seconds undrifted, and this
    #  engine cannot turn the stretch between two instants into a number (AGENTS, the traps).
    read_at: datetime | None = None

    #  NO measure field, deliberately, and one briefly existed: a desire does not carry how
    #  its badness is scored, because that is a capability's answer and not the mind's
    #  structure (a-desire-states-its-own-measure). Whoever needs the number asks the choir —
    #  `Agent.desire_urgency(desire, query, sensed)` — of whichever world is being judged,
    #  and sensing answers for observation-backed wants from its own declaration. A obligation's
    #  fraction-of-window stays kernel Python behind a pinned engine limit (this store binds
    #  nothing for duration division — tests/test_desires.py), with the market's own
    #  declaration as its recorded future home.

    @property
    def is_met(self) -> bool:
        """Nothing is wanted here right now. False for an obligation, which is never *met* — it is
        discharged, and a discharged debt is history rather than a desire."""
        return self.state == "met"

    @property
    def is_obligation(self) -> bool:
        return self.claim is not None

    @property
    def is_epistemic(self) -> bool:
        """Is this a want about my KNOWLEDGE of something rather than about the thing?

        The two are repaired by different means — no lever moves a number you cannot see —
        and, since a property may carry one of each, whoever asks "what should I do about
        this property" has to say which of the two it means. An actuator means the number.
        """
        return self.instrument is not None
