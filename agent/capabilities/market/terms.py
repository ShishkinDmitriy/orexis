"""The terms this package implements — the Python end of `ontology.ttl`.

Three capabilities, not one, because a directory is a **package** and not a capability. A
bidder answers offers with a private number; a host runs the round; a matching family turns the
bids that arrive into an allocation with prices. An agent may hold any of them, and the third is
a family with interchangeable members where the first two are single abilities.

Also the terms this package *refers to*. A capability that needs something from another names
that other's family term and asks the agent for a provider; it never imports the other's Python.
The term is the interface, exactly as the constitution says — which is why matching living in
this directory changes nothing about how `hosting.py` reaches it.
"""

from __future__ import annotations

from agent.ontology import term

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

# --- what this package asks OF others, by family ---
PERCEPTION = term("PerceptionCapability")  # whoever can look, however it looks
ACTUATION = term("Actuation")  # whoever can touch the hardware, if this agent can at all
