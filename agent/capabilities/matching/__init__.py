"""The manifest: what this capability contributes to a build.

Both ways of matching, now. `ag:UniformPrice` was declared here with no implementation when the
format became a capability, under a note claiming that adding it would be *"a class and one line
of PROVIDES; no other package moves"*. That turned out to be exactly true — this file and
`module.py` are the whole of it, and `hosting.py` was not touched, because it asks
`agent.provider(MATCHING)` for whoever matches and never learns which rule answered.

Which is the point of a family. The market package still does not know that either rule is
implemented in Python at all.
"""

from .module import PayAsBidModule, UniformPriceModule
from .terms import MATCHES_BY, MATCHING, PAY_AS_BID, UNIFORM_PRICE

PROVIDES = (PayAsBidModule, UniformPriceModule)

__all__ = ["PROVIDES", "PayAsBidModule", "UniformPriceModule",
           "MATCHING", "PAY_AS_BID", "UNIFORM_PRICE", "MATCHES_BY"]
