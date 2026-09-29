"""Revision's metrics: the revisions counted off the belief base's catalogue, and each revision pass
tallied as the deliberator makes it — over Hanoi's mover, whose state is revised at its start."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock, metrics
from agent.belief.metrics import gauges
from agent.belief.ontology import REVISION_GRAPH, SETTLED
from agent.runtime import Runtime, boot
from agent.series import METRICS, Sink, install
from agent.store import catalogue_of, graphs_of

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

HANOI = Path(__file__).resolve().parents[3] / "world" / "hanoi"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATE = "http://example.org/orexis#StateGraph"


@pytest.fixture
def written():
    out = []
    install(METRICS, Sink(METRICS, "m", lambda bucket, record: out.extend(record)))
    yield out
    install(METRICS, None)
    metrics.reset()


def test_the_revisions_are_counted_off_the_catalogue_and_the_unsettled_apart():
    """Two revision graphs described, one of them cut short by its budget: two, and one unsettled —
    and an unsettled count bound where none is, never a column left out."""
    beliefs = boot(HANOI, "hanoi")
    revisions = lambda: next(f for g, f in gauges(beliefs) if g.name == "revisions")
    before = revisions()
    cat = ox.NamedNode(catalogue_of(beliefs))
    for graph, settled in (("urn:revision:one", True), ("urn:revision:two", False)):
        beliefs.add(ox.Quad(ox.NamedNode(graph), ox.NamedNode(RDF_TYPE), ox.NamedNode(REVISION_GRAPH), cat))
        beliefs.add(ox.Quad(ox.NamedNode(graph), ox.NamedNode(SETTLED), ox.Literal(settled), cat))
    assert revisions() == {"revisions": before["revisions"] + 2, "unsettled": before.get("unsettled", 0) + 1}


def test_a_revision_pass_is_tallied_with_what_it_spent(monkeypatch, written):
    """The state revised again: one source handed, executions spent, none cut short."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    runtime = Runtime(boot(HANOI, "hanoi"), "hanoi")
    metrics.flush()                                  # the window the start of the runtime tallied
    runtime.started["belief"].changed(graphs_of(runtime.beliefs, STATE)[0])
    runtime.started["belief"].deliberate(NOW)
    (point,) = metrics.flush()
    assert point["measurement"] == "revise" and point["fields"]["count"] == 1
    assert point["fields"]["sources_sum"] == 1.0 and point["fields"]["cut_max"] == 0.0
    assert point["fields"]["duration_s_max"] > 0
