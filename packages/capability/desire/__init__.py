"""The manifest: what this capability contributes to a build.

One of the two ways of arriving at a region. `desire:Consulting` — asking something else where
inside the stated ranges to aim — is declared in `ontology.ttl` and deliberately absent here,
exactly as `review:Consulting` and `perception:Polling` are: the vocabulary should be honest that
the judgement is the replaceable part, but nothing implements this one yet and granting a
capability no module provides only produces a startup warning. Adding it is a class and one line
of `PROVIDES`; no other package moves.
"""

from .module import DesireModule, Gap, Region, aims_of, gaps_of, regions_of
from .terms import CONSULTING, DEDUCING, DESIRE

PROVIDES = (DesireModule,)

__all__ = ["PROVIDES", "DesireModule", "Gap", "Region", "aims_of", "gaps_of", "regions_of",
           "DESIRE", "DEDUCING", "CONSULTING"]
