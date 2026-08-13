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

NS = "http://example.org/agora/intention#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name


# The family. Anything that keeps this agent's commitments is one of these — so a caller may
# say "commit to this" without knowing how commitments are kept.
INTENTION = term("IntentionCapability")

# The members.
KEEPING = term("Keeping")  # a ledger with a patience clock: rule-kept commitments

# What an intention is made of. Named here because the module writes and reads them.
INTENTION_CLASS = term("Intention")
BY = term("by")
ADOPTED_AT = term("adoptedAt")
RESOLVED_AT = term("resolvedAt")
OUTCOME = term("outcome")
BECAUSE_OF = term("becauseOf")

# The means — what kind of act the commitment is to.
OBSERVE = term("Observe")  # look: get a reading where the gap is unmeasured or stale
ACQUIRE = term("Acquire")  # obtain: bid for what would reduce a gap
APPLY = term("Apply")      # spend: redeem a held claim against the world — RESERVED, see ontology

# The commitment policy — the belief, not the mechanism.
PATIENCE_S = term("patienceS")
