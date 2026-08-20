"""The manifest: what this capability contributes to a build.

One of the two ways of arriving at a region. `desire:Consulting` — asking something else where
inside the stated ranges to aim — is declared in `ontology.ttl` and deliberately absent here,
exactly as `review:Consulting` and `sensing:Polling` are: the vocabulary should be honest that
the judgement is the replaceable part, but nothing implements this one yet and granting a
capability no module provides only produces a startup warning. Adding it is a class and one line
of `PROVIDES`; no other package moves.
"""

from .module import (DesireModule, Gap, Region, aims_of, gaps_of, goals_of,
                     regions_of)
from .owing import OwingModule
from .terms import CONSULTING, DEDUCING, DESIRE, OWING

#  Two capabilities, two modules, and an agent may compose either or both: a plant
#  holds stakes and owes nothing, the city owes and holds no stake, the supplier does
#  both. They are separate families, so `agent.provider` is never ambiguous.
PROVIDES = (DesireModule, OwingModule)

__all__ = ["PROVIDES", "DesireModule", "OwingModule", "Gap", "Region", "aims_of",
           "gaps_of",
           "goals_of", "regions_of",
           "DESIRE", "DEDUCING", "CONSULTING", "OWING"]
