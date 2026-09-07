"""A predicted number is an interval (#556): how the signature states one, what it covers,
and what the cone does with a present that lands inside it.

The record is knowledge/decisions/a-predicted-number-is-an-interval.md. The rule-side half —
that the effect declares the ends — is in tests/test_effects.py; the keeper's half in
tests/test_expectation.py.
"""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from conftest import build_agent, genesis_store
from orexis_agent_deliberation import signature
from orexis_agent_deliberation.planner import Planner

SOSA = "http://www.w3.org/ns/sosa/"
XSD = "http://www.w3.org/2001/XMLSchema#"
AT_LEAST = "http://example.org/orexis/sensing#atLeast"
AT_MOST = "http://example.org/orexis/sensing#atMost"
KEYS = signature.Keys(
    {SOSA + "Observation": (frozenset({SOSA + "hasFeatureOfInterest", SOSA + "observedProperty"}),
                            frozenset({SOSA + "hasSimpleResult"}))},
    ends={SOSA + "hasSimpleResult": (AT_LEAST, AT_MOST)})


def _observation(value: str, low: str | None = None, high: str | None = None):
    node = ox.BlankNode()
    dec = ox.NamedNode(XSD + "decimal")
    out = [ox.Triple(node, ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                     ox.NamedNode(SOSA + "Observation")),
           ox.Triple(node, ox.NamedNode(SOSA + "hasFeatureOfInterest"), ox.NamedNode("urn:zz")),
           ox.Triple(node, ox.NamedNode(SOSA + "observedProperty"), ox.NamedNode("urn:moisture")),
           ox.Triple(node, ox.NamedNode(SOSA + "hasSimpleResult"), ox.Literal(value, datatype=dec))]
    if low is not None:
        out.append(ox.Triple(node, ox.NamedNode(AT_LEAST), ox.Literal(low, datatype=dec)))
    if high is not None:
        out.append(ox.Triple(node, ox.NamedNode(AT_MOST), ox.Literal(high, datatype=dec)))
    return out


def test_a_node_stating_both_ends_is_one_fact_whose_value_is_the_pair():
    """The two end predicates the vocabulary declares for a carried value fold into it: one
    fact, its value `("interval", low, high)`, and the ends count as nothing of their own —
    so a narrower interval at the same midpoint is a new world. One end alone, or none, is
    the number; a plain dict of keys, stating no ends, reads the ends as facts of their own."""
    (fact,) = signature.facts(_observation("0.5", "0.45", "0.55"), KEYS)
    assert fact[3] == SOSA + "hasSimpleResult" and fact[4] == ("interval", 0.45, 0.55)
    (point,) = signature.facts(_observation("0.5"), KEYS)
    assert point[4] == 0.5
    (lone,) = signature.facts(_observation("0.5", low="0.45"), KEYS)
    assert lone[4] == 0.5, "one end alone states a point"
    narrower = signature.facts(_observation("0.5", "0.48", "0.52"), KEYS)
    assert narrower != signature.facts(_observation("0.5", "0.45", "0.55"), KEYS)
    assert len(signature.facts(_observation("0.5", "0.45", "0.55"), dict(KEYS))) == 1, \
        "with no ends declared, an end predicate is not carried and does not count"


def test_an_interval_is_placed_in_a_cell_by_its_midpoint():
    cells = {"urn:moisture": (0.3, 0.45)}
    (fact,) = signature.facts(_observation("0.5", "0.40", "0.60"), KEYS, cells)
    assert fact[4] == ("cell", 0.45, None)
    (again,) = signature.to_cells(signature.facts(_observation("0.5", "0.40", "0.60"), KEYS), cells)
    assert again[4] == ("cell", 0.45, None)
    assert signature.point(("interval", 0.4, 0.6)) == pytest.approx(0.5)
    assert signature.point(0.5) == 0.5


def test_a_predicted_interval_covers_the_present_inside_it():
    """The exact test with the width read as the prediction meant it: a present reading inside
    the predicted interval is what the world predicted; outside it is not; a predicted fact
    missing or a present fact unpredicted is not either. Plain facts are equal or nothing."""
    head = ("keyed", SOSA + "Observation", (("k", "urn:zz"),), SOSA + "hasSimpleResult")
    inside = frozenset({head + (("interval", 0.4, 0.6),)})
    assert signature.covers(inside, frozenset({head + (0.55,)}))
    assert signature.covers(inside, frozenset({head + (0.4,)})), "the ends are inclusive"
    assert not signature.covers(inside, frozenset({head + (0.7,)}))
    assert not signature.covers(inside | {("a", "b", "c")}, frozenset({head + (0.5,)})), "a predicted fact missing"
    assert not signature.covers(inside, frozenset({head + (0.5,), ("a", "b", "c")})), "a present fact unpredicted"
    assert not signature.covers(inside, frozenset({head + (("interval", 0.45, 0.55),)})), \
        "a narrower interval is not a present inside it: the present is observed, a point"
    assert signature.covers(frozenset({("a", "b", "c")}), frozenset({("a", "b", "c")}))
    assert not signature.covers(frozenset({head + (0.5,)}), frozenset({head + (0.55,)})), "a point predicts one number"


def test_inside_the_interval_the_subtree_stands_and_outside_it_falls(monkeypatch):
    """A dry gardener plans a dose that predicts an interval. A present INSIDE it is the
    world the dose predicted, exactly — the worlds beneath were computed from that width —
    so the cone re-roots there with its subtree whole. A present in the same CELL but outside
    the interval is the same world by every rule's reckoning and not what the step promised:
    the node becomes the root, re-scored from the present, and what was imagined beneath it
    is dropped (#573, #556)."""
    from conftest import write_reading
    from orexis_agent_deliberation.partition import cell_of
    from test_planning import MOISTURE, STORED
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): 0.10, ("water_butt", STORED): 3.0}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)

    def want():
        return next(g for g in agent.pursuing()
                    if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)

    planner = Planner(agent, agent.me)
    seen = []
    original = planner._reroot

    def spy(node, present, subtree=True, desire=None):
        seen.append(subtree)
        return original(node, present, subtree=subtree, desire=desire)
    monkeypatch.setattr(planner, "_reroot", spy)

    plan = planner.plan(want())
    assert plan.steps, "a dry gardener doses"
    stated = next(f[4] for f in plan.steps[0].predicts[0] if f[0] == "keyed")
    low, high = signature.ends(stated)
    mid = signature.point(stated)
    assert low < mid < high
    cells = planner.partition(want())[MOISTURE]
    outside = high + 0.01
    assert cell_of(outside, cells) == cell_of(mid, cells), "outside the interval, in the cell"
    write_reading(agent, outside, MOISTURE)
    planner.plan(want())
    assert seen == [False], "in the cell and outside the interval: the node alone, re-scored"

    planner.reset()
    write_reading(agent, 0.10, MOISTURE)
    plan = planner.plan(want())
    stated = next(f[4] for f in plan.steps[0].predicts[0] if f[0] == "keyed")
    low, high = signature.ends(stated)
    inside = high - 0.01
    assert low <= inside <= high and inside != signature.point(stated)
    write_reading(agent, inside, MOISTURE)
    planner.plan(want())
    assert seen == [False, True], "inside the interval: exact, the subtree stands"
