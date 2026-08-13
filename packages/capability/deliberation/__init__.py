"""The manifest: what this capability contributes to a build.

One of the two ways of deciding. `deliberation:Consulting` — asking a model what next — is
declared in `ontology.ttl` and deliberately absent here, exactly as `desire:Consulting` and
`review:Consulting` are: the vocabulary should be honest that the judgement is the replaceable
part — here it is the reason the family exists at all — but the seam had to demonstrably carry
Reflex first, and granting a capability no module provides only produces a startup warning.
Adding it is a class and one line of `PROVIDES`; no actor moves.
"""

from .module import ReflexModule
from .terms import CONSULTING, DELIBERATION, REFLEX

PROVIDES = (ReflexModule,)

__all__ = ["PROVIDES", "ReflexModule", "DELIBERATION", "REFLEX", "CONSULTING"]
