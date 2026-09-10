"""Deliberation reads no clock (#598), and this is what keeps it that way.

A rule, a measure or a shape that asks `NOW()` is asking the REAL now — the wall clock of
whatever process happens to evaluate it — and inside a search that is never the instant its
act would be taken at. So the answer is about a world nobody is in: a round that closed
between the pass and the act was open in every world the search imagined.

Every such question turns out to be asking for a FACT. Is the round open. Is the venue
cooling. Is this reading still evidence. A fact is written by whoever owns the clock — a
host declaring its close, a timer landing on the loop, time's own sense at the belief-revision
seam — and read as a triple, which asks no clock in a simulated world or a real one.

The two that are left are sensing's, and they are named here rather than tolerated silently:
the freshness measure and the want derived from it both compute a reading's age. This test is
a RATCHET — it fails on a new one anywhere, and it fails when a named one is fixed and not
struck off, so the list cannot rot into permission.
"""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#  What deliberation evaluates: the rules an action declares, the measures a want scores by,
#  the shapes a world is judged against, the derivations that write wants, and the reviews.
EVALUATED = ("packages/*/actions.ttl", "packages/*/measures.ttl", "packages/*/shapes.ttl",
             "packages/*/desires.ru", "packages/*/rules.ru", "packages/*/review.rq",
             "agent/shapes.ttl", "agent/ontology.ttl")

#  The clock reads still standing, each with the issue that takes it out. A file here must
#  carry EXACTLY this many, so fixing one without striking it off fails as loudly as adding one.
LEFT = {
    "packages/orexis-capability-sensing/measures.ttl": 1,   # #598: a reading's age, per candidate world
    "packages/orexis-capability-sensing/desires.ru": 1,     # #598: the same, built into the derived want
}


def _code(path: pathlib.Path) -> str:
    """The file without its comment lines — a comment may say NOW() and often should, since
    that is how a fixed one is explained."""
    return "\n".join(line for line in path.read_text().splitlines()
                     if not line.strip().startswith("#"))


def _files():
    seen = []
    for pattern in EVALUATED:
        seen.extend(sorted(ROOT.glob(pattern)))
    return seen


def test_the_files_deliberation_evaluates_are_found():
    """A glob that stops matching takes a case off the guard without failing anything, which
    has happened twice in this repo (`tests/test_store.py` says so)."""
    found = {p.name for p in _files()}
    assert {"actions.ttl", "measures.ttl", "shapes.ttl", "desires.ru"} <= found, found
    assert len(_files()) >= 12, [p.name for p in _files()]


@pytest.mark.parametrize("path", _files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_rule_deliberation_evaluates_asks_the_wall_clock(path):
    rel = str(path.relative_to(ROOT))
    assert _code(path).count("NOW()") == LEFT.get(rel, 0), (
        f"{rel}: a clock read where a fact belongs, or a fixed one still listed in LEFT. "
        "A rule asking NOW() inside a search asks the real now, never the instant its act "
        "would be taken at — see #598, and the round that stopped asking in #599.")
