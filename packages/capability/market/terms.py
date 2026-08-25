"""The terms this package implements — the Python end of `ontology.ttl`.

Three capabilities, not one, because a directory is a **package** and not a capability. A
bidder answers offers with a private number; a host runs the round; a matching family turns the
bids that arrive into an allocation with prices. An agent may hold any of them, and the third is
a family with interchangeable members where the first two are single abilities.

Also the terms this package *refers to*. A capability that needs something from another names
that other's family term and asks the agent for a provider; it never imports the other's Python.
The term is the interface, exactly as the constitution says — which is why matching living in
this directory changes nothing about how `hosting.py` reaches it.

**This package owns a namespace**, and `term()` here builds into it. `ag:` is what every agent
has — `ag:Agent`, `ag:Capability`, `ag:hasCapability`, `ag:localId` — and those are reached
through `agent.ontology` because they are the kernel's, not this package's to move. See
knowledge/decisions/a-package-owns-its-namespace.md.
"""

from __future__ import annotations

from agent import ontology

# Where this package's terms live. `ontology.ttl` declares the same namespace and is the
# authority — `agent.loader` reads it from there, which is how `market:` reaches a query. This
# constant is so Python can name a term without parsing Turtle, and the two are held together by
# `tests/test_layout.py`.
NS = "http://example.org/orexis/market#"


def term(name: str) -> str:
    """One of this package's own terms. The kernel's are reached through `agent.ontology`."""
    return NS + name


# --- the three capabilities this package provides ---
BIDDING = term("Bidding")  # plumbed into a market: it answers offers with a private number
HOSTING = term("Hosting")  # owns the venue: it runs rounds

# The matching family, and its two members. A host asks for the FAMILY and is answered by
# whichever member its world put in force — which is the whole point of it being one.
BID_MATCHING = term("BidMatchingCapability")
PAY_AS_BID = term("PayAsBid")          # each winner pays its own bid
UNIFORM_PRICE = term("UniformPrice")   # every winner pays the lowest accepted bid

# What a host states to say how it matches. Read by this package's derivation; the capability
# follows from it and is never declared.
MATCHES_BY = term("matchesBy")

# A round as a FACT (a-round-is-a-fact-and-offering-is-an-action) — held by host and bidder
# alike, each in its own graph. See rounds.py for the one writer both sides use.
ROUND = term("Round")
HAS_ROUND = term("hasRound")
ROUND_ID = term("roundId")
LOT_L = term("lotL")
RESERVE_PER_L = term("reservePerL")
CLOSES_AT = term("closesAt")
MAY_CONVENE_AT = term("mayConveneAt")

# A call: the want a participant's LOW sources on a host (knowledge/domain/call.md).
CALL = term("Call")
CALLED_ON = term("calledOn")
CALLED_BY = term("calledBy")
CALLED_AT = term("calledAt")

# --- what this package asks OF others, by family. Their namespaces, not this one's ---
#
# Declared as literals rather than imported: capability packages never import each other's
# Python, so the namespace IRI is the interface. Building these with the KERNEL's `term()` is
# the mistake to avoid — it compiles silently, names a term nobody declares, and
# `agent.provider` then finds nobody. `test_round.py::test_winning_opens_the_valve` caught
# exactly that when actuation took a namespace of its own.
ACTUATION_NS = "http://example.org/orexis/actuation#"

SENSING = ontology.SENSING + "SensingCapability"  # whoever can look, however it looks
ACTUATION = ACTUATION_NS + "Actuation"  # whoever can touch the hardware, if this agent can at all
# The mind's STATES are kernel words; the FAMILIES that arrive at them are not.
KERNEL = "http://example.org/orexis#"
#  Whoever keeps the debts. Its OWN family, because owing is granted by holding a lever
#  others may demand and not by having a stake — a host with no interest of its own still
#  owes what its market allocated (#233).
# The three means a bidder's acts amount to. MEANS, not capabilities: they name what an act IS
# when the keeper records it, and they are the kernel's individuals referenced by IRI — as is
# the keeper itself now, reached as `agent.keeper` rather than asked for by family.
ACQUIRING = term("Acquiring")     # buying — the action, and the kind of act it is
SERVING = term("Serving")         # the host pouring a presented claim
PRESENTING = term("Presenting")   # the buyer holding, then presenting, a won claim (#132)
OFFERING = term("Offering")       # the host opening a round
