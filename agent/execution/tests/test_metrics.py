"""Execution's metrics: the intentions and the acts counted in the intentions store, and a derived
want's desire read off the store its plan came from. The landing's lateness on a real run is the
greenhouse's to hold."""

from __future__ import annotations

import pyoxigraph as ox

from agent.execution.metrics import derived_from, gauges


def test_an_empty_intentions_store_counts_nought_of_everything_and_leaves_no_field_out():
    """A SUM over no rows is nought, and every column is there — a field left out is a panel's line
    that stops rather than one at nought."""
    sampled = {g.name: f for g, f in gauges(ox.Store())}
    assert sampled == {"intentions": {"standing": 0, "done": 0, "failed": 0, "superseded": 0, "abandoned": 0},
                       "acts": {"taken": 0, "notTaken": 0}}


def test_a_want_derived_from_nothing_names_no_desire():
    store = ox.Store()
    assert derived_from(store, "urn:a:want") is None
    store.add(ox.Quad(ox.NamedNode("urn:a:want"), ox.NamedNode("http://www.w3.org/ns/prov#wasDerivedFrom"),
                      ox.NamedNode("urn:the#comfort"), ox.NamedNode("urn:g")))
    assert derived_from(store, "urn:a:want") == "comfort"
