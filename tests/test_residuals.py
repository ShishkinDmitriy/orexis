"""Review is the belief revision function (#518): every answered step leaves a residual —
the reading it predicted against the reading the world showed — and a package's rule re-picks
the CONVERSION when residuals lean one way and the TOLERANCE when they scatter. Nothing is
mocked: fern's real ledger, the real evidence graph, the SPARQL the market package ships."""
from __future__ import annotations

import pytest

from orexis_capability_market.terms import ACQUIRING, TOLERANCE, TENDERING
from orexis_agent_progression.store import bindings
from orexis_capability_review.graphs import evidence_graph
from conftest import (MOISTURE, build_agent, genesis_store, predicted_reading, reading_of,
                      stake_of, write_reading)

CONVERSION = "http://example.org/orexis/water#litresPerFraction"
BASELINE, PREDICTED = 0.30, 0.55            # 0.5 L through 2.0 L-per-fraction from 0.30


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", genesis_store({"fern": BASELINE}), monkeypatch)


def answered(agent, observed: float, predicted: float = PREDICTED) -> str:
    """One lot bought and answered: the step predicts `predicted`, the world shows `observed`.
    Inside the band the verdict is met on the reading; outside it the deadline passes."""
    keeper, want = agent.keeper, stake_of(agent).uri
    write_reading(agent, BASELINE, MOISTURE)
    uri = keeper.adopt(TENDERING, want, "a lot on its way")
    #  The band a rule would declare at the default tolerance: half the movement either way.
    band = 0.5 * abs(predicted - BASELINE)
    assert keeper.expect(uri, "show me", baseline=reading_of(agent, MOISTURE),
                         predicts=predicted_reading(agent.me.acts_for, MOISTURE, predicted,
                                                    low=predicted - band, high=predicted + band))
    write_reading(agent, observed, MOISTURE)
    if keeper.open_expectations(want):
        keeper.lapse(uri)
    return uri


def step_of(agent, uri):
    return bindings(agent.intentions.query_union(f"""
SELECT ?p ?o WHERE {{ <{uri}> progression:by ?s . ?s progression:predictedValue ?p ; progression:observedValue ?o }}"""))


def test_a_verdict_records_what_was_predicted_and_what_the_world_showed(fern):
    uri = answered(fern, 0.60)                                   # inside the band: met
    rows = step_of(fern, uri)
    assert len(rows) == 1
    assert float(rows[0]["p"]) == pytest.approx(PREDICTED) and float(rows[0]["o"]) == pytest.approx(0.60)
    uri = answered(fern, 0.36)                                   # short of it: unmet, still a residual
    rows = step_of(fern, uri)
    assert float(rows[0]["o"]) == pytest.approx(0.36), "a shortfall at the deadline is evidence too"


def test_residuals_are_published_as_evidence_off_the_ledger(fern):
    for observed in (0.60, 0.40):
        answered(fern, observed)
    review = fern.reviewing()
    review.publish_evidence(review.ranges())
    rows = bindings(fern.beliefs.query(f"""
SELECT ?o ?b WHERE {{ GRAPH <{evidence_graph(fern.id)}> {{
  ?r a review:Residual ; review:ofAction <{TENDERING}> ; review:predicted ?p ;
     review:observed ?o ; review:baseline ?b }} }} ORDER BY ?o"""))
    assert [float(r["o"]) for r in rows] == [pytest.approx(0.40), pytest.approx(0.60)]
    assert all(float(r["b"]) == pytest.approx(BASELINE) for r in rows)


def test_residuals_leaning_one_way_re_pick_the_conversion(fern):
    """Three lots, each moving the property 0.10 where 0.25 was promised: the conversion is
    wrong by 2.5, and the rule proposes 2.0 x 2.5 = 5.0 — inside the water bounds."""
    review = fern.reviewing()
    assert review.current(CONVERSION) == pytest.approx(2.0)
    for _ in range(3):
        answered(fern, 0.40)
    review.review()
    assert review.current(CONVERSION) == pytest.approx(5.0)
    assert review.revisions >= 1


def test_residuals_scattering_widen_the_tolerance_and_leave_the_conversion(fern):
    """Two short and two long, averaging exactly the promise: no lean, so the conversion
    stands; the widest miss is 0.6 of the movement against a tolerance of 0.5, so the
    tolerance is re-picked to 0.75."""
    review = fern.reviewing()
    for observed in (0.40, 0.70, 0.40, 0.70):
        answered(fern, observed)
    review.review()
    assert review.current(CONVERSION) == pytest.approx(2.0)
    assert review.current(TOLERANCE) == pytest.approx(0.75)


def test_residuals_landing_tight_narrow_the_tolerance(fern):
    """Every lot within 0.04 of the movement: a tolerance of 0.5 admits five times the
    error the model makes, and it narrows to the widest miss with slack — 0.05, the floor."""
    review = fern.reviewing()
    for observed in (0.56, 0.54, 0.55):
        answered(fern, observed)
    review.review()
    assert review.current(TOLERANCE) == pytest.approx(0.05)


def test_too_few_residuals_say_nothing(fern):
    review = fern.reviewing()
    answered(fern, 0.40)
    answered(fern, 0.40)
    review.review()
    assert review.current(CONVERSION) == pytest.approx(2.0) and review.current(TOLERANCE) == pytest.approx(0.5)
