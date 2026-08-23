"""The terms this package implements — the Python end of `ontology.ttl`.

The axis here is **what keeping a commitment costs**. Every implementation answers the same
question — *what am I already doing about this, and is it still worth doing?* — and the how
could differ: a ledger with a patience clock keeps commitments by rule; something that weighs a
commitment against what has changed since it was made would keep them by judgement. One ability,
two ways of having it, which is what makes this a capability rather than a bookkeeping module.

Nothing outside this package names these. `agent.provider(INTENTION)` asks for whoever keeps
commitments, exactly as it asks for whoever wants or perceives.
"""

from __future__ import annotations

NS = "http://example.org/orexis/intention#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name

# The mind's STATES live in the kernel now: they are the lingua franca four packages
# already had to name, and `ag:IntentionGraph` holding `intention:Intention` was a split
# brain. What stays here is the HOW — this family, its members, and its own figures.
KERNEL = "http://example.org/orexis#"


def kernel(name: str) -> str:
    """A mind state, by local name. Kernel-owned; see the-mind-is-six-graphs."""
    return KERNEL + name


# The family. Anything that keeps this agent's commitments is one of these — so a caller may
# say "commit to this" without knowing how commitments are kept.
INTENTION = term("IntentionCapability")

# The members.
KEEPING = term("Keeping")  # a ledger with a patience clock: rule-kept commitments

# What an intention is made of. Named here because the module writes and reads them.
INTENTION_CLASS = kernel("Intention")
BY = kernel("by")
PURSUES = kernel("pursues")  # which desire this commitment serves (#the collision)
ADOPTED_AT = kernel("adoptedAt")
RESOLVED_AT = kernel("resolvedAt")
OUTCOME = kernel("outcome")
BECAUSE_OF = kernel("becauseOf")

# The means — what kind of act the commitment is to.
OBSERVE = kernel("Observe")  # look: get a reading where the gap is unmeasured or stale
ACTUATE = kernel("Actuate")  # move it myself: lever and resource both mine — the second rung
ACQUIRE = kernel("Acquire")  # obtain: bid for what would reduce a gap
APPLY = kernel("Apply")      # spend: redeem a held claim against the world — RESERVED, see ontology

# The commitment policy — the belief, not the mechanism.
PATIENCE_S = term("patienceS")

# The expectation — the END, judged apart from the means. See ontology.ttl's own section.
EXPECTS_VALUE_TO = kernel("expectsValueTo")
BASELINE_VALUE = kernel("baselineValue")
BASELINE_AT = kernel("baselineAt")
EXPECTS_DELTA = kernel("expectsDelta")
DEADLINE_AT = kernel("deadlineAt")
END_MET = kernel("endMet")
END_VERIFIED_AT = kernel("endVerifiedAt")
SUSPECT_AFTER = term("suspectAfter")
