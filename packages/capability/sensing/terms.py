"""The terms this package implements — the Python end of `ontology.ttl`.

Every capability package names its terms in one small file like this, so nothing central has
to know they exist. **This package owns a namespace**, and `term()` here builds into it —
perceiving is what an agent wired to a sensor does, not what every agent does, so `ag:` was
never the right place for it. `tests/test_layout.py` holds `NS` and the `@prefix` in
`ontology.ttl` together.
"""

from __future__ import annotations

NS = "http://example.org/orexis/sensing#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name

# The family. Anything that perceives is one of these — which is what lets another capability
# ask for "whoever perceives" without knowing which way it does it.
SENSING = term("SensingCapability")

# The axis is who holds the clock, and these are in decreasing order of agent control.
POLLING = term("Polling")  # the agent asks, each time — RESERVED, nothing implements it yet
SUBSCRIBING = term("Subscribing")  # the agent states an interval; the device keeps to it
LISTENING = term("Listening")  # the device announces on its own clock; the agent records

# The other end of the same axis: what a DEVICE is, from which the capability above is derived.
# A module names the mode it serves so it can take only the sensors it is actually for — the
# pairing is stated in rules.ru as well, and the alternative is introspecting a SPARQL update to
# recover it, which is worse. Both are T-Box terms, which the first rule permits in code.
PULL = term("PolledProcedure")           # answers when asked — the unbuilt sensing:Polling would serve it
SCHEDULED = term("ScheduledProcedure")   # keeps an interval it is given -> sensing:Subscribing
PUSH = term("PushProcedure")            # keeps its own clock, takes no orders -> sensing:Listening

#  The horizon this agent publishes per sensor, so a SHAPE can read what only Python could work
#  out (#240). One definition and one direction: `stale_after_s` computes it, `publish_horizon`
#  writes it, and everything else — including the freshness want — reads what was written.
STALE_AFTER_S = term("staleAfterS")
