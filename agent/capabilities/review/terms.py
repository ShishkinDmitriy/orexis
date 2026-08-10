"""The terms this package implements — the Python end of `ontology.ttl`.

The axis here is **who does the judging**. A review is arithmetic over evidence followed by a
choice, and the choice is the part that can be made differently: an agent can work it out from
rules the packages ship, or it can ask something else. Two ways of having one ability, which is
what makes this a capability rather than a function.

Nothing outside this package names these. `agent.provider(REVIEW)` asks for whoever reviews,
exactly as it asks for whoever perceives.
"""

from __future__ import annotations

from agent.ontology import term

# The family. Anything that reconsiders its own settings is one of these — so a caller may ask
# for "whoever reviews" without knowing which way it does it.
REVIEW = term("ReviewCapability")

# The axis is who reaches the judgement, and these are in decreasing order of self-sufficiency.
RECKONING = term("Reckoning")    # works it out itself, from rules the packages ship
CONSULTING = term("Consulting")  # asks something else — RESERVED, nothing implements it yet

# What a commitment is made of. Named here because the granting rule reads them, and because a
# range is this package's subject even though the world is where one is stated.
COMMITS = term("commits")
ON_TERM = term("onTerm")
