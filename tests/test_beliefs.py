"""Beliefs are read per capability, from the agent's own graph, with no defaults.

The reader is kernel; the blocks belong to the capability packages, so a test reaches for
`SUBSCRIBING_PICKS` from `capabilities.sensing` exactly as the module that runs does.
"""

from datetime import datetime, timedelta, timezone

import pytest

from assembly import loader  # noqa: F401  (puts the package trees on sys.path)
from orexis_agent_progression import ontology
from orexis_agent_deliberation.beliefs import BeliefError, Beliefs
from orexis_capability_sensing.readings import Reading, current_reading
from orexis_capability_sensing.regions import aims_of, regions_of
from orexis_capability_market.beliefs import BIDDING_PICKS, HOSTING_PICKS
from orexis_capability_sensing.beliefs import SUBSCRIBING_PICKS

from conftest import MOISTURE, TEMPERATURE, desires_build, genesis_store


def regions(agent_id, agent_uri):
    """What one agent wants, read the way its own module reads it: from the desire modality,
    which derives them — deduced, not believed, and since #312 not in the belief base at all."""
    return regions_of(desires_build(genesis_store(), agent_id).query_union, agent_uri)

FERN = "http://example.org/orexis/world/simulation#fern_agent"
FERN_URI = "http://example.org/orexis/world/simulation#fern"  # the plant, not the agent that acts for it
SUCCULENT = "http://example.org/orexis/world/simulation#succulent_agent"
SUPPLIER = "http://example.org/orexis/world/simulation#supplier"
CITY = "http://example.org/orexis/world/simulation#city"


@pytest.fixture
def fern():
    return Beliefs(genesis_store(), "fern")


# --- one block per capability ----------------------------------------------

def test_subscribing_block(fern):
    p = fern.read(SUBSCRIBING_PICKS)
    assert (p.fast_sleep_s, p.slow_sleep_s, p.grace_s) == (30, 600, 45)


def test_bidding_block(fern):
    """A wallet and a value curve — no band, no target, and no conversion.

    The band edges left first: they were the plant's own limits restated privately. The target
    followed, as `sensing:aims` — the point an agent steers for is a fact about its ends, not
    about a market, and the bidder now asks whoever provides the desire family for it at bid
    time. The conversion left last (#198): WHICH term turns a deficit into litres is a fact
    about the bidder's venue — litres-per-fraction for a fern, litres-per-stored-litre for the
    dealer — and a block's terms are fixed at import, so the module discovers the term through
    the venue tie and reads its own belief in it by IRI. What is left is what only a BID needs
    whatever the venue prices.
    """
    b = fern.read(BIDDING_PICKS)
    assert b.max_value_per_l == 0.80
    for gone in ("target", "low", "high", "litres_per_fraction"):
        assert not hasattr(b, gone), gone


def test_hosting_block(query):
    h = Beliefs(genesis_store(), "supplier").read(HOSTING_PICKS)
    assert (h.quantity_l, h.reserve_price_per_l) == (2.0, 0.20)
    assert h.bid_window_s == 3


def test_agents_hold_different_opinions(query):
    # same world, same ontology, different mind — and neither is wrong. The differing opinion
    # is the AIM now, read the way the desire module reads it: privately, from each agent's own
    # graph, which is why the id travels with the URI.
    fern_aims = aims_of(query, "fern", FERN)
    succ_aims = aims_of(query, "succulent", SUCCULENT)
    assert succ_aims[MOISTURE] < fern_aims[MOISTURE]


def test_slower_agent_tolerates_older_data(query):
    fern = Beliefs(genesis_store(), "fern").read(SUBSCRIBING_PICKS)
    succ = Beliefs(genesis_store(), "succulent").read(SUBSCRIBING_PICKS)
    assert succ.slow_sleep_s > fern.slow_sleep_s
    assert succ.grace_s >= fern.grace_s


# --- what a stake makes of a reading ---------------------------------------
# The verdict belongs to the agent that holds a stake, never to the sensor: the same number is
# trouble for a fern and comfort for a succulent. It is no longer a BELIEF, though, which is why
# these read from the world through the desire capability rather than from a beliefs file — the
# region is deduced from what each plant states it needs, and neither agent could have picked it.

def test_the_same_reading_is_trouble_for_one_and_not_the_other(query):
    fern = regions("fern", FERN)[MOISTURE]
    succ = regions("succulent", SUCCULENT)[MOISTURE]
    assert fern.band(0.30) == "LOW"
    assert succ.band(0.30) != "LOW"
    assert succ.low < fern.low        # a succulent sits drier, and its plant says so publicly


def test_a_region_is_the_two_ranges_its_plant_states(query):
    """Nothing in a beliefs file could have produced these numbers: world.ttl says fern grows in
    0.45-0.65 and survives 0.20-0.85, and the region is that pair intersected with every other
    range that applies — which today is none, so it is that pair exactly."""
    moisture = regions("fern", FERN)[MOISTURE]
    assert (moisture.low, moisture.high) == (0.45, 0.65)
    assert (moisture.floor, moisture.ceiling) == (0.20, 0.85)


def test_an_agent_wants_one_thing_per_property_its_plant_states(query):
    """`market:aboutProperty` occurring once used to mean an agent could want exactly one thing.
    Fern's plant states two ranges, so fern holds two regions, in two different units."""
    assert set(regions("fern", FERN)) == {MOISTURE, TEMPERATURE}
    assert set(regions("succulent", SUCCULENT)) == {MOISTURE}


# --- isolation and failure -------------------------------------------------

def test_one_agent_cannot_read_anothers_beliefs():
    """The graph IS the boundary — and since identity became discovered, the mismatched
    reader this test used to build (fern's URI against succulent's graph) cannot even be
    constructed: an id yields its OWN uri and its OWN graph, so the misread is
    unrepresentable rather than merely empty. What remains checkable is that discovery
    binds the pair correctly."""
    b = Beliefs(genesis_store(), "succulent")
    assert b.agent_uri == SUCCULENT
    assert b.graph.endswith("/succulent")


def test_a_missing_belief_is_an_error_not_a_default(query):
    """The city holds no bidding terms — it must fail, never silently invent a valuation.

    This used the SUPPLIER until arc 4 made it the dealer: it holds a wallet and a value
    curve now, because it genuinely bids upstream. The city inherits the role of the agent
    with no buy side — it acts for nothing and wants nothing, so a code path that read its
    bidding block would be a bug this refusal catches.
    """
    with pytest.raises(BeliefError) as exc:
        Beliefs(genesis_store(), "city").read(BIDDING_PICKS)
    # The FULL IRI, not `water:maxValuePerL`. Belief terms come from whichever package
    # declares them and packages own their namespaces, so a prefix here would be a
    # guess — and a wrong one for anything market: owns.
    #
    # A literal, not a kernel constant: `ontology.WATER` left with #148 — the kernel names no
    # domain — so the test names the domain the way the one deliberately-coupled block does.
    assert "http://example.org/orexis/water#maxValuePerL" in str(exc.value)
    assert "city" in str(exc.value)


def test_the_error_names_every_missing_term(query):
    # readingGraceS left this list when the barrel learned to run dry: the supplier states it
    # now (the shapes demand it of every perceiver), so the genuinely missing pair is what a
    # complete error must name — the test's point is EVERY, not WHICH.
    with pytest.raises(BeliefError) as exc:
        Beliefs(genesis_store(), "supplier").read(SUBSCRIBING_PICKS)
    for term in ("http://example.org/orexis/sensing#fastSleepS", "http://example.org/orexis/sensing#slowSleepS"):
        assert term in str(exc.value)


# --- readings and the freshness rule ---------------------------------------

def _reading(age_s):
    ts = None if age_s is None else datetime.now(timezone.utc) - timedelta(seconds=age_s)
    return Reading(value=0.18, result_time=ts)


def test_reads_its_subject(query_with_readings):
    b = Beliefs(genesis_store({"fern": 0.18}), "fern")
    reading = current_reading(b.query, "http://example.org/orexis/world/simulation#fern", MOISTURE)
    assert reading.value == 0.18 and reading.is_fresh(120)


def test_no_reading_yet_is_none(fern):
    assert current_reading(fern.query, "http://example.org/orexis/world/simulation#fern", MOISTURE) is None


def test_two_properties_of_one_subject_both_survive(query_with_readings):
    """The defect, stated as a test: a pot with a probe and a thermometer.

    Keyed by subject alone, these two took turns destroying each other's record — and the loss
    was the smaller half, because a lookup returned whichever wrote last. Asking for moisture
    could hand back 21.0, a plausible number in the wrong unit that a market would act on.
    """
    b = Beliefs(genesis_store({("fern", MOISTURE): 0.18,
                                             ("fern", TEMPERATURE): 21.0}), "fern")
    assert current_reading(b.query, FERN_URI, MOISTURE).value == 0.18
    assert current_reading(b.query, FERN_URI, TEMPERATURE).value == 21.0


def test_a_property_nothing_has_read_is_none_not_the_other_one(query_with_readings):
    """The substitution, guarded from the other side. Silence must not be answered with a
    number that happens to be about the same pot."""
    b = Beliefs(genesis_store({("fern", TEMPERATURE): 21.0}), "fern")
    assert current_reading(b.query, FERN_URI, MOISTURE) is None


def test_stale_reading_is_not_fresh():
    assert not _reading(3600).is_fresh(120)


def test_untimed_reading_is_never_fresh():
    assert not _reading(None).is_fresh(120)
