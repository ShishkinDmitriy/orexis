"""Beliefs are read per capability, from the agent's own graph, with no defaults.

The reader is kernel; the blocks belong to the capability packages, so a test reaches for
`POLLING_BLOCK` from `capabilities.perception` exactly as the module that runs does.
"""

from datetime import datetime, timedelta, timezone

import pytest

from agora import loader  # noqa: F401  (puts the package trees on sys.path)
from agora.beliefs import BeliefError, Beliefs, Reading
from capabilities.market.beliefs import BIDDING_BLOCK, HOSTING_BLOCK
from capabilities.perception.beliefs import POLLING_BLOCK

FERN = "http://example.org/agora#fern_agent"
SUCCULENT = "http://example.org/agora#succulent_agent"
SUPPLIER = "http://example.org/agora#supplier"


@pytest.fixture
def fern(query):
    return Beliefs(query, "fern", FERN)


# --- one block per capability ----------------------------------------------

def test_polling_block(fern):
    p = fern.read(POLLING_BLOCK)
    assert (p.fast_sleep_s, p.slow_sleep_s, p.max_age_s) == (30, 600, 120)


def test_bidding_block(fern):
    b = fern.read(BIDDING_BLOCK)
    assert b.target == 0.55
    assert (b.low, b.high) == (0.35, 0.65)
    assert b.max_value_per_l == 0.80


def test_hosting_block(query):
    h = Beliefs(query, "supplier", SUPPLIER).read(HOSTING_BLOCK)
    assert (h.quantity_l, h.reserve_price_per_l) == (2.0, 0.20)
    assert h.bid_window_s == 3


def test_agents_hold_different_opinions(query):
    fern = Beliefs(query, "fern", FERN).read(BIDDING_BLOCK)
    succ = Beliefs(query, "succulent", SUCCULENT).read(BIDDING_BLOCK)
    # same world, same ontology, different mind — and neither is wrong
    assert succ.target < fern.target
    assert succ.low < fern.low


def test_slower_agent_tolerates_older_data(query):
    fern = Beliefs(query, "fern", FERN).read(POLLING_BLOCK)
    succ = Beliefs(query, "succulent", SUCCULENT).read(POLLING_BLOCK)
    assert succ.slow_sleep_s > fern.slow_sleep_s
    assert succ.max_age_s > fern.max_age_s


# --- what a stake makes of a reading ---------------------------------------
# The band belongs to the agent that holds a target, never to the sensor: the same number is
# trouble for a fern and comfort for a succulent.

def test_it_judges_a_reading_against_its_own_limits(fern):
    b = fern.read(BIDDING_BLOCK)
    assert b.band(0.20) == "LOW"
    assert b.band(0.50) == "OK"
    assert b.band(0.80) == "HIGH"


def test_the_same_reading_is_trouble_for_one_and_not_the_other(query):
    fern = Beliefs(query, "fern", FERN).read(BIDDING_BLOCK)
    succ = Beliefs(query, "succulent", SUCCULENT).read(BIDDING_BLOCK)
    assert fern.band(0.30) == "LOW"
    assert succ.band(0.30) != "LOW"


def test_urgency_runs_from_its_ceiling_to_its_floor(fern):
    b = fern.read(BIDDING_BLOCK)
    assert b.urgency(b.high) == 0.0
    assert b.urgency(b.low) == 1.0
    assert b.urgency(0.0) == 1.0  # below the floor is not MORE than trouble
    assert 0.0 < b.urgency((b.low + b.high) / 2) < 1.0


# --- isolation and failure -------------------------------------------------

def test_one_agent_cannot_read_anothers_beliefs(query):
    """The graph IS the boundary: fern's URI against succulent's graph yields nothing."""
    with pytest.raises(BeliefError):
        Beliefs(query, "succulent", FERN).read(BIDDING_BLOCK)


def test_a_missing_belief_is_an_error_not_a_default(query):
    """The supplier holds no bidding terms — it must fail, never silently invent a target."""
    with pytest.raises(BeliefError) as exc:
        Beliefs(query, "supplier", SUPPLIER).read(BIDDING_BLOCK)
    assert "ag:hasTarget" in str(exc.value)  # it names the term and the graph
    assert "supplier" in str(exc.value)


def test_the_error_names_every_missing_term(query):
    with pytest.raises(BeliefError) as exc:
        Beliefs(query, "supplier", SUPPLIER).read(POLLING_BLOCK)
    for term in ("ag:fastSleepS", "ag:slowSleepS", "ag:maxReadingAgeS"):
        assert term in str(exc.value)


# --- readings and the freshness rule ---------------------------------------

def _reading(age_s):
    ts = None if age_s is None else datetime.now(timezone.utc) - timedelta(seconds=age_s)
    return Reading(value=0.18, result_time=ts)


def test_reads_its_subject(query_with_readings):
    b = Beliefs(query_with_readings({"fern": 0.18}), "fern", FERN)
    reading = b.current_reading("http://example.org/agora#fern")
    assert reading.value == 0.18 and reading.is_fresh(120)


def test_no_reading_yet_is_none(fern):
    assert fern.current_reading("http://example.org/agora#fern") is None


def test_stale_reading_is_not_fresh():
    assert not _reading(3600).is_fresh(120)


def test_untimed_reading_is_never_fresh():
    assert not _reading(None).is_fresh(120)
