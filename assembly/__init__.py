"""How a build is put together, and how its parts reach each other.

**Not the mind.** `agent/` is a BDI engine — belief, desire, intention, act, plan — and how a
build is assembled from packages is none of those. This package owns finding packages, the
extension mechanism they contribute through, and the vocabulary that names an extension point.
The kernel keeps the points it OWNS (`ag:desires`, `ag:take`, `ag:size`) and stops owning the
machinery (the-assembly-is-not-the-mind).

The direction, held by `lint-imports`: **assembly <- agent <- onboarding**. Nothing here imports
the kernel, which is what lets the kernel be one of the things assembled.
"""

from .contribute import answer, contributes, contributions_of
from .terms import ACTIONS, DERIVATION, REVIEW, SHAPES, VOCABULARY, WANTS

__all__ = ["answer", "contributes", "contributions_of",
           "ACTIONS", "DERIVATION", "REVIEW", "SHAPES", "VOCABULARY", "WANTS"]
