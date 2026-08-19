"""The terms this package implements — the Python end of `ontology.ttl`.

The axis here is **how the region is arrived at**. Every implementation answers the same
question — *where should this agent try to keep the property it cares about?* — and there is
genuinely more than one way to answer it: work it out from the ranges the world states, or ask
something else where inside them to aim. Two ways of having one ability, which is what makes
this a capability rather than a function.

Nothing outside this package names these. `agent.provider(DESIRE)` asks for whoever wants,
exactly as it asks for whoever perceives.
"""

from __future__ import annotations

NS = "http://example.org/agora/desire#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name

# The mind's STATES live in the kernel now: they are the lingua franca four packages
# already had to name, and `ag:IntentionGraph` holding `intention:Intention` was a split
# brain. What stays here is the HOW — this family, its members, and its own figures.
KERNEL = "http://example.org/agora#"


def kernel(name: str) -> str:
    """A mind state, by local name. Kernel-owned; see the-mind-is-six-graphs."""
    return KERNEL + name


# The family. Anything that can say where a property should be held is one of these — so a
# caller may ask for "whoever holds a desire" without knowing how it reached one.
DESIRE = term("DesireCapability")

# The members, in decreasing order of self-sufficiency — the same axis review's are on.
DEDUCING = term("Deducing")      # intersects the ranges the world states; no latitude at all
CONSULTING = term("Consulting")  # asks something else — RESERVED, nothing implements it yet

# What a deduced desire is made of. Named here because the module reads them back out of the
# graph the rule wrote, and because a region is this package's subject even though every figure
# in one came from somewhere else.
DESIRES = kernel("desires")
DESIRE_CLASS = kernel("Desire")
TOLERATED_MIN = kernel("toleratedMin")
TOLERATED_MAX = kernel("toleratedMax")

# The graph class. A TERM, not an instance: `agent.store` is asked which graphs are of this
# class, so a second source of desire is a vocabulary edit and touches no Python here.
REGION_GRAPH = term("RegionGraph")  # the regions that BIND — a constraint graph, not a desire
