"""Beliefs are read per capability, from the agent's own graph, with no defaults."""

from datetime import datetime, timedelta, timezone

import pytest

from agora.beliefs import BeliefError, Beliefs, Reading

FERN = "http://example.org/agora#fern_agent"
SUCCULENT = "http://example.org/agora#succulent_agent"
SUPPLIER = "http://example.org/agora#supplier"


@pytest.fixture
def fern(query):
    return Beliefs(query, "fern", FERN)


# --- one block per capability ----------------------------------------------

def test_polling_block(fern):
    p = fern.polling()
    assert (p.fast_sleep_s, p.slow_sleep_s, p.max_age_s) == (30, 600, 120)


def test_bidding_block(fern):
    b = fern.bidding()
    assert b.target == 0.55
    assert (b.low, b.high) == (0.35, 0.65)
    assert b.max_value_per_l == 0.80


def test_hosting_block(query):
    h = Beliefs(query, "supplier", SUPPLIER).hosting()
    assert (h.quantity_l, h.reserve_price_per_l) == (2.0, 0.20)
    assert h.bid_window_s == 3


def test_agents_hold_different_opinions(query):
    fern = Beliefs(query, "fern", FERN).bidding()
    succ = Beliefs(query, "succulent", SUCCULENT).bidding()
    # same world, same ontology, different mind — and neither is wrong
    assert succ.target < fern.target
    assert succ.low < fern.low


def test_slower_agent_tolerates_older_data(query):
    fern = Beliefs(query, "fern", FERN).polling()
    succ = Beliefs(query, "succulent", SUCCULENT).polling()
    assert succ.slow_sleep_s > fern.slow_sleep_s
    assert succ.max_age_s > fern.max_age_s


# --- isolation and failure -------------------------------------------------

def test_one_agent_cannot_read_anothers_beliefs(query):
    """The graph IS the boundary: fern's URI against succulent's graph yields nothing."""
    with pytest.raises(BeliefError):
        Beliefs(query, "succulent", FERN).bidding()


def test_a_missing_belief_is_an_error_not_a_default(query):
    """The supplier holds no bidding terms — it must fail, never silently invent a target."""
    with pytest.raises(BeliefError) as exc:
        Beliefs(query, "supplier", SUPPLIER).bidding()
    assert "ag:hasTarget" in str(exc.value)  # it names the term and the graph
    assert "supplier" in str(exc.value)


def test_the_error_names_every_missing_term(query):
    with pytest.raises(BeliefError) as exc:
        Beliefs(query, "supplier", SUPPLIER).polling()
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
