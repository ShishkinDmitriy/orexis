"""The manifest: what this capability package contributes to a build.

Three capabilities from one directory, because a directory is a **package** and not a
capability. Bidding and hosting are the two sides of one venue, separate because they are
separate decisions: a bidder answers with a private number, a host runs the round. Matching is a
third and a different shape — a family with two interchangeable members, where the other two
have one way each.

**Matching sharing the package does not weaken the seam it was split out to prove.** What keeps
the protocol independent of the matching is `PROVIDES` and the term: `hosting.py` asks
`agent.provider(BID_MATCHING)` and never learns which member answered. Uniform price landed
without touching a line of `hosting.py`, and it would have done so from here too. A directory
boundary is how a family is DELETED, not how it is isolated — and the cost of folding is exactly
that: removing matching is now an edit rather than a deletion. See
knowledge/decisions/a-package-owns-its-namespace.md.
"""

from .bidding import BiddingModule, value_bid
from .hosting import HostingModule
from .matching import PayAsBidModule, UniformPriceModule
from .terms import BID_MATCHING, BIDDING, HOSTING, MATCHES_BY, PAY_AS_BID, UNIFORM_PRICE

PROVIDES = (BiddingModule, HostingModule, PayAsBidModule, UniformPriceModule)

__all__ = ["PROVIDES", "BiddingModule", "HostingModule", "PayAsBidModule", "UniformPriceModule",
           "value_bid", "BIDDING", "HOSTING",
           "BID_MATCHING", "PAY_AS_BID", "UNIFORM_PRICE", "MATCHES_BY"]
