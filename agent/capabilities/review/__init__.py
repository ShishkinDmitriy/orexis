"""The manifest: what this capability contributes to a build.

One of the two ways of reviewing. `review:Consulting` — asking a model instead of working it out — is
declared in `ontology.ttl` and deliberately absent here, exactly as `perception:Polling` is for
perception: the vocabulary should be honest that the judgement is the replaceable part, but
nothing implements this one yet and granting a capability no module provides only produces a
startup warning. Adding it is a class and one line of `PROVIDES`; no other package moves.
"""

from .module import ReviewModule
from .terms import CONSULTING, RECKONING, REVIEW

PROVIDES = (ReviewModule,)

__all__ = ["PROVIDES", "ReviewModule", "REVIEW", "RECKONING", "CONSULTING"]
