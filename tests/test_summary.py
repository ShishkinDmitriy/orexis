"""What an agent's readings came to, and what it costs to keep — plus the house it keeps.

The point of a summary is that it is a **belief about history** rather than history: fixed size
however long the agent runs, surviving a restart, and readable without the series store being
up. Each of those is a property something could quietly lose, so each is asserted here.

See knowledge/decisions/a-belief-is-a-pick-within-a-range.md and issue #45.
"""

from __future__ import annotations

import pytest

from agent import genesis
from agent.ontology import SENSED_GRAPH, summaries_graph, term
from agent.store import Store
from agent.summary import RING, Summaries

from conftest import MOISTURE, WORLDS_ROOT, build_agent

FERN = "http://example.org/agora#fern"


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", monkeypatch=monkeypatch)


@pytest.fixture
def summaries():
    return Summaries(Store(), "fern")


# --- what it keeps ---------------------------------------------------------------------------

def test_a_summary_holds_what_the_readings_came_to(summaries):
    for value in (0.2, 0.4, 0.6):
        summaries.record(FERN, MOISTURE, value)
    held = summaries.accumulating()[0]
    assert held.count == 3
    assert (held.minimum, held.maximum) == (0.2, 0.6)
    assert held.mean == pytest.approx(0.4)


def test_an_instrument_that_did_not_move_spreads_exactly_zero(summaries):
    """A variance only APPROACHES zero for a nearly-still world, and IS zero only for an
    instrument that has not moved at all. Those two want opposite responses, so the extremes are
    kept beside the sums to make the distinction exact rather than nearly exact."""
    for _ in range(10):
        summaries.record(FERN, MOISTURE, 0.412)
    assert summaries.accumulating()[0].spread == 0.0


def test_a_barely_moving_instrument_spreads_slightly(summaries):
    for value in (0.500, 0.502) * 5:
        summaries.record(FERN, MOISTURE, value)
    assert 0.0 < summaries.accumulating()[0].spread < 0.01


def test_the_spread_is_unit_free(summaries):
    """One agent's property is a fraction and another's is degrees; a threshold in either unit
    would be nonsense in the other, so the same proportional wobble reads the same either way."""
    other = Summaries(Store(), "fern")
    for value in (0.100, 0.102):
        summaries.record(FERN, MOISTURE, value)
    for value in (100.0, 102.0):
        other.record(FERN, MOISTURE, value)
    assert summaries.accumulating()[0].spread == pytest.approx(
        other.accumulating()[0].spread, rel=1e-6)


# --- what it costs ---------------------------------------------------------------------------

def test_a_summary_of_a_year_is_the_size_of_a_summary_of_an_hour(summaries):
    """The guarantee `agent-metrics.md` makes about a flat triple count. History lives in Influx;
    what the store keeps is running totals, so the belief base does not grow with time."""
    for value in range(50):
        summaries.record(FERN, MOISTURE, value / 100)
    small = len(summaries.store)
    for value in range(5000):
        summaries.record(FERN, MOISTURE, value / 10000)
    assert len(summaries.store) == small


def test_the_ring_is_bounded(summaries):
    for _ in range(RING * 3):
        summaries.record(FERN, MOISTURE, 0.5)
        summaries.roll()
    assert len(summaries.completed()) <= RING


def test_rolling_closes_the_window_and_starts_a_fresh_one(summaries):
    summaries.record(FERN, MOISTURE, 0.5)
    assert summaries.roll() == 1
    assert summaries.accumulating() == []
    assert [w.count for w in summaries.newest()] == [1]

    summaries.record(FERN, MOISTURE, 0.6)
    assert [w.count for w in summaries.accumulating()] == [1]


def test_the_newest_window_is_what_accumulated_since_the_last_arising(summaries):
    for value in (0.1, 0.2, 0.3):
        summaries.record(FERN, MOISTURE, value)
    summaries.roll()
    summaries.record(FERN, MOISTURE, 0.9)
    summaries.roll()
    assert [w.count for w in summaries.newest()] == [1]


# --- what survives ---------------------------------------------------------------------------

def test_an_accumulator_survives_a_restart(tmp_path, monkeypatch):
    """The reason this is in the store and not in memory. An agent that reboots keeps the grounds
    for its own judgement instead of earning them again — and never has to ask the series store
    for them, which attention must never wait on.
    """
    path, world = str(tmp_path / "beliefs"), WORLDS_ROOT / "society"

    store = genesis.open_belief_base(world, "fern", path)
    Summaries(store, "fern").record(FERN, MOISTURE, 0.42)
    Summaries(store, "fern").record(FERN, MOISTURE, 0.44)
    del store

    reborn = genesis.open_belief_base(world, "fern", path)
    held = Summaries(reborn, "fern").accumulating()
    assert [w.count for w in held] == [2]
    assert held[0].maximum == 0.44


def test_a_summary_is_not_part_of_the_sensed_record(fern):
    """Apart on purpose: `:sensed` is the measurement record, and a summary is the agent's own
    derived account of its past. Keeping them in one graph would make 'a review never writes the
    sensed record' untestable."""
    sensor = fern.subscribing().sensors[0]
    fern.reviewer.summaries.record(sensor.subject, sensor.observes, 0.5)
    assert "ObservationSummary" not in fern.store.get_graph(SENSED_GRAPH)
    assert "ObservationSummary" in fern.store.get_graph(summaries_graph("fern"))


def test_the_ingest_path_summarises_every_reading(fern):
    """Kernel, beside the writer it follows — so a summary does not depend on which capability
    happened to obtain the number."""
    sensor = fern.subscribing().sensors[0]
    for value in (0.30, 0.31, 0.32):
        fern.subscribing().ingest(sensor, value)
    assert [w.count for w in fern.reviewer.summaries.accumulating()] == [3]


# --- keeping its own house (issue #45) ---------------------------------------------------------

def test_an_in_memory_store_has_no_ratio_and_is_never_compacted(fern):
    """Every test and every world-building tool holds one, and none has anything to compact."""
    assert fern.reviewer.upkeep.ratio() is None
    assert not fern.reviewer.upkeep.consider()


def test_the_compaction_threshold_is_read_from_the_ontology(fern):
    assert fern.reviewer.upkeep.max_bytes_per_triple > 0


def test_a_belief_base_on_disk_is_compacted_when_it_is_mostly_history(tmp_path, monkeypatch):
    """The ratio that revealed #45 is the ratio that triggers the remedy: flat triples under
    rising bytes is write amplification, and neither number alone shows it."""
    store = genesis.open_belief_base(WORLDS_ROOT / "society", "fern", str(tmp_path / "beliefs"))
    agent = build_agent("fern", st=store, monkeypatch=monkeypatch)
    upkeep = agent.reviewer.upkeep

    assert upkeep.ratio() is not None  # it has a disk, so it has a ratio
    upkeep.max_bytes_per_triple = 0  # any real store is "mostly history" at this threshold
    assert upkeep.consider()
    assert upkeep.compactions == 1
    assert agent.metrics.agent_fields()["belief_compactions"] == 1
