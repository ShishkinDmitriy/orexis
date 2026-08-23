"""The terms this package implements — the Python end of `ontology.ttl`.

The axis here is **who reaches the decision**. Every implementation answers the same question —
*given where I stand against what I want, and what I am already doing, what next?* — and the how
could differ more than anywhere else in this project: a reflex answers from the gap's sign, and
a model could answer from everything the agent knows. One ability, two ways of having it, and
the second is the reason the first was extracted.

Nothing outside this package names these. `agent.provider(DELIBERATION)` asks for whoever
decides, exactly as it asks for whoever wants, keeps or perceives.
"""

from __future__ import annotations

NS = "http://example.org/orexis/deliberation#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name


# The family. Anything that turns a gap and the standing commitments into the next move is one
# of these — so a bidder may ask "should I?" without knowing how the answer is reached.
DELIBERATION = term("DeliberationCapability")

# The members, in decreasing order of self-sufficiency — the axis review's and desire's share.
REFLEX = term("Reflex")          # answers from the gap's sign; deterministic, free
PLANNING = term("Planning")      # bounded depth-2 over menu rows — the dealer's member
CONSULTING = term("Consulting")  # asks a model — RESERVED, nothing implements it yet
