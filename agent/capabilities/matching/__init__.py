"""The manifest: what this capability contributes to a build.

One of the two ways of matching. `ag:UniformPrice` — every winner paying one clearing price — is
declared in `ontology.ttl` and deliberately absent here, exactly as `ag:Polling` is for perception
and `ag:Consulting` for review: the vocabulary should be honest that the allocation rule is the
replaceable part, but nothing implements this one yet, and a world that states it derives a
capability whose absence the agent reports at startup. Adding it is a class and one line of
`PROVIDES`; no other package moves, which is the whole point of #66.
"""

from .module import PayAsBidModule
from .terms import MATCHES_BY, MATCHING, PAY_AS_BID, UNIFORM_PRICE

PROVIDES = (PayAsBidModule,)

__all__ = ["PROVIDES", "PayAsBidModule", "MATCHING", "PAY_AS_BID", "UNIFORM_PRICE", "MATCHES_BY"]
