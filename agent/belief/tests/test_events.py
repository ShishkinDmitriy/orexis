"""What the deliberator says happened, as events: a revision pass said with what it spent, and the
revisions the catalogue describes counted apart from the unsettled — over Hanoi's mover, whose state
is revised at its start."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox

from agent import clock
from agent.belief.events import Revised, RevisionsHeld
from agent.belief.ontology import REVISION_GRAPH, SETTLED
from agent.runtime import Runtime, boot
from agent.store import catalogue_of, graphs_of

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

HANOI = Path(__file__).resolve().parents[3] / "world" / "hanoi"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
STATE = "http://example.org/orexis#StateGraph"


def _revised_again(monkeypatch, before=None) -> list:
    monkeypatch.setattr(clock, "now", lambda: NOW)
    runtime = Runtime(boot(HANOI, "hanoi"), "hanoi")
    deliberator = runtime.parts["belief"].deliberator
    heard = []
    deliberator.revised.connect(heard.append)
    deliberator.revisions_held.connect(heard.append)
    if before:
        before(runtime.beliefs)
    deliberator.changed(graphs_of(runtime.beliefs, STATE)[0])
    deliberator.deliberate(NOW)
    return heard


def test_a_revision_pass_is_said_with_what_it_spent(monkeypatch):
    """The state revised again: one source handed and revised, executions spent, none cut short."""
    revised, held = _revised_again(monkeypatch)
    assert isinstance(revised, Revised) and isinstance(held, RevisionsHeld)
    assert (revised.sources, revised.cut, len(revised.graphs)) == (1, 0, 1)
    assert revised.duration_s > 0 and held.unsettled == 0


def test_the_revisions_are_counted_off_the_catalogue_and_the_unsettled_apart(monkeypatch):
    """Two revision graphs described besides, one of them cut short by its budget: two more, and one
    unsettled."""
    def two(beliefs):
        cat = ox.NamedNode(catalogue_of(beliefs))
        for graph, settled in (("urn:revision:one", True), ("urn:revision:two", False)):
            beliefs.add(ox.Quad(ox.NamedNode(graph), ox.NamedNode(RDF_TYPE), ox.NamedNode(REVISION_GRAPH), cat))
            beliefs.add(ox.Quad(ox.NamedNode(graph), ox.NamedNode(SETTLED), ox.Literal(settled), cat))
    plain = _revised_again(monkeypatch)[1]
    held = _revised_again(monkeypatch, two)[1]
    assert (held.revisions, held.unsettled) == (plain.revisions + 2, plain.unsettled + 1)
