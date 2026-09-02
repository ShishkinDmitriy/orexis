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

from pathlib import Path

from assembly import contributes, ACTIONS, DERIVATION, REVIEW, SHAPES, VOCABULARY
from .terms import BID_MATCHING, BIDDING, HOSTING, MATCHES_BY, PAY_AS_BID, UNIFORM_PRICE

@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — what its terms mean."""
    return [package / "ontology.ttl"]

@contributes(SHAPES)
def shapes(package: Path) -> list[Path]:
    """what must be true of a thing that has it."""
    return [package / "shapes.ttl"]

@contributes(DERIVATION)
def derivation(package: Path) -> list[Path]:
    """the premise that grants it."""
    return [package / "rules.ru"]

@contributes(ACTIONS)
def actions(package: Path) -> list[Path]:
    """the ways of acting it brings."""
    return [package / "actions.ttl"]

def provides() -> tuple:
    """The classes this package contributes. Imported HERE and not at the top, so an
    agent granted none of them never pays for the import (#216) — and a missing optional
    extra costs only the agents that were granted the capability needing it."""
    from .bidding import BiddingModule
    from .hosting import HostingModule
    from .matching import PayAsBidModule, UniformPriceModule

    return (BiddingModule, HostingModule, PayAsBidModule, UniformPriceModule)

__all__ = ["value_bid", "BIDDING", "HOSTING", "BID_MATCHING", "PAY_AS_BID", "UNIFORM_PRICE", "MATCHES_BY"]


@contributes(REVIEW)
def review(package: Path) -> list[Path]:
    """the second thought — a bidder's conversion and tolerance, from the lots it saw land (#518)."""
    return [package / "review.rq"]
