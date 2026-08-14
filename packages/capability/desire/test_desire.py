"""What a region means, tested where it lives.

Arithmetic only — no world, no store, no fixtures. This package carries these because a region's
behaviour is the package's own claim: how a reading is banded, and how urgency scales by the
envelope. The tests that need a ratified world (that fern deduces two regions, that a bidder's
target answers to one) are the integration suite's, in `tests/`, because they are about the world
and not about this file. See knowledge/decisions/a-package-may-test-itself.md.
"""

from __future__ import annotations

from .module import Region

# A Zamioculcas, in the figures its own package states: the region it grows in, and a survival
# envelope that is NOT symmetric around it. That asymmetry is the reason the envelope is carried
# at all, so it is what these are written against rather than a tidy symmetric example.
ZZ = Region("moisture", low=0.10, high=0.30, floor=0.02, ceiling=0.45)

# The same shape with nothing stated outside it — a world that gives an operating range and no
# survival range, which is legal and must degrade rather than fail.
BARE = Region("moisture", low=0.10, high=0.30)


def test_a_band_is_the_region_and_nothing_else():
    assert ZZ.band(0.05) == "LOW"
    assert ZZ.band(0.10) == "OK"    # the edge is inside: a region includes its bounds
    assert ZZ.band(0.20) == "OK"
    assert ZZ.band(0.30) == "OK"
    assert ZZ.band(0.31) == "HIGH"


def test_urgency_is_nothing_at_the_point_and_everything_at_the_envelope():
    assert ZZ.urgency(ZZ.centre) == 0.0
    assert ZZ.urgency(0.02) == 1.0   # exactly the survival floor
    assert ZZ.urgency(0.45) == 1.0   # exactly the survival ceiling
    assert ZZ.urgency(0.0) == 1.0    # past it is not MORE than trouble
    assert ZZ.urgency(1.0) == 1.0


def test_it_rises_inside_the_region_rather_than_waiting_for_the_edge():
    """The band says whether I am in trouble; urgency says how close I am getting.

    A step function would tell sensing to relax completely anywhere inside the region and
    then panic on the way out. An agent at the very edge of comfortable is already worth
    watching more closely than one sitting in the middle, and the whole point of handing
    sensing a number rather than a verdict is that it can act on the difference.
    """
    assert 0.0 < ZZ.urgency(0.15) < ZZ.urgency(0.11) < ZZ.urgency(0.05)
    assert ZZ.band(0.15) == ZZ.band(0.11) == "OK"


def test_the_two_sides_are_scaled_by_their_own_room():
    """The asymmetry is the fact worth having in machine-readable form.

    This ZZ has 0.18 of room below its centre and 0.25 above, so the same distance out reads as
    sharper on the dry side. Nothing in this file knows what a rhizome is: the ordering comes
    out of the two ranges the species package states, and a plant whose ranges say the opposite
    gets the opposite answer with no edit here.
    """
    out = 0.14  # symmetric about the centre: 0.06 and 0.34
    assert ZZ.urgency(ZZ.centre - out) > ZZ.urgency(ZZ.centre + out)


def test_with_no_envelope_the_region_is_its_own_scale():
    """A world that states no survival range gets a cruder answer, honestly reached."""
    assert BARE.urgency(BARE.centre) == 0.0
    assert BARE.urgency(BARE.low) == 1.0
    assert BARE.urgency(BARE.high) == 1.0
    assert 0.0 < BARE.urgency(0.15) < 1.0
    # and it is uniformly sharper than the same region with room around it, which is right:
    # not knowing how much slack there is should not be read as knowing there is a lot.
    assert BARE.urgency(0.12) > ZZ.urgency(0.12)


def test_a_region_with_no_width_is_all_or_nothing():
    """The reading a bandless bidder used to get, preserved: pinned is pinned."""
    pinned = Region("moisture", low=0.4, high=0.4)
    assert pinned.urgency(0.4) == 0.0
    assert pinned.urgency(0.41) == 1.0
    assert pinned.band(0.41) == "HIGH"
