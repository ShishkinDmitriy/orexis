"""The terms this package implements — the Python end of `ontology.ttl`.

The axis here is **how bids become an allocation**. Given a lot and a set of bids there is more
than one defensible answer — pay each winner its own bid, or pay everyone the same clearing
price — and which one is in force changes what a rational bidder should offer. Two ways of
having one ability, which is what makes this a capability rather than a function.

**"Matching" is the word for that ability**, and knowledge/domain/bid-matching.md defines it. Three
were in circulation for one concept — *matching*, *rule* and *format* — and `rule` was the
worst of them, because `rules.ru` already means something else in every capability directory.

Nothing outside this package names these. `agent.provider(BID_MATCHING)` asks for whoever can match,
exactly as hosting already asks for whoever can actuate.
"""

from __future__ import annotations

from agent.ontology import term

# The family. Anything that turns bids into an allocation is one of these — so a host may ask
# for "whoever matches" without knowing which member answered.
BID_MATCHING = term("BidMatchingCapability")

# The members, by what a winner pays. Both implemented; a world says which its host runs.
PAY_AS_BID = term("PayAsBid")          # each winner pays its own bid
UNIFORM_PRICE = term("UniformPrice")   # every winner pays the lowest accepted bid

# What a host states to say how it matches. Read by this package's derivation; the capability
# follows from it and is never declared.
MATCHES_BY = term("matchesBy")
