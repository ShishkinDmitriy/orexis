"""`revise`, one case per file, held to a PATCH of the store it leaves.

A case in `revise/` is a store with a graph of readings, public knowledge beside it, and a graph
of rules as a package would ship them, a sh:RuleSet in a sh:RulesGraph. The test revises the readings and `<case>.diff` is what
that concluded: the readings' revision graph, its row, and nothing in the readings.
"""

from __future__ import annotations

from pathlib import Path

import statistics
import time

import pytest

from agent.belief.ontology import SETTLED
from agent.belief.revise import revise
from agent.ontology import KNOWN
from agent.store import graphs_of, rows, update

CASES_DIR = Path(__file__).parent / "revise"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)
SENSED = "http://example.org/test#sensed"

_CONCLUDED_Q = "SELECT ?s ?p ?o WHERE { GRAPH $g { ?s ?p ?o } }"


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_revise_concludes_what_the_patch_says(case, request, snapshots):
    store = snapshots.stand_in(case)
    revise(store, SENSED, read=graphs_of(store, *KNOWN))
    snapshots.held_to_diff(case, request, "revise", snapshots.snapshot_of(store))


def test_a_rewritten_source_replaces_its_conclusions(snapshots):
    """What replaces a conclusion is its source rewritten: a reading moved inside its range
    concludes nothing, and the graph that said Below is gone with its row."""
    store = snapshots.stand_in(CASES_DIR / "a_reading_below_its_range_is_concluded_below.trig")
    read = graphs_of(store, *KNOWN)
    concluded = SENSED + "/revisions"
    assert revise(store, SENSED, read=read) > 0
    assert rows(store, _CONCLUDED_Q, (), g=concluded)
    update(store, f"DELETE {{ GRAPH <{SENSED}> {{ ?o <http://example.org/test#reads> ?v }} }} "
                  f"INSERT {{ GRAPH <{SENSED}> {{ ?o <http://example.org/test#reads> 0.2 }} }} "
                  f"WHERE {{ GRAPH <{SENSED}> {{ ?o <http://example.org/test#reads> ?v }} }}")
    assert revise(store, SENSED, read=read) > 0
    assert not rows(store, _CONCLUDED_Q, (), g=concluded)
    assert graphs_of(store, "http://example.org/orexis/belief#RevisionGraph") == []


def test_a_rule_that_never_settles_spends_the_budget_and_is_said(snapshots, caplog):
    """A rule minting new content every iteration is a package's bug: the call spends its
    budget of rule executions and stops, the row says the rules did not settle, the log names
    the source, and what was concluded stands."""
    store = snapshots.stand_in(CASES_DIR / "a_reading_below_its_range_is_concluded_below.trig")
    update(store, """
INSERT DATA { GRAPH <http://example.org/test#rules> {
  <http://example.org/test#restless> a <http://www.w3.org/ns/shacl#RuleSet> ;
    <http://www.w3.org/ns/shacl#hasRule> [ a <http://www.w3.org/ns/shacl#SPARQLRule> ;
      <http://www.w3.org/ns/shacl#construct> "PREFIX : <http://example.org/test#> CONSTRUCT { ?s :token ?u } WHERE { ?s a :Pot BIND(STRUUID() AS ?u) }" ] } }""")
    with caplog.at_level("WARNING", logger="revise"):
        spent = revise(store, SENSED, read=graphs_of(store, *KNOWN), budget=12)
    assert spent == 12
    tokens = [r for r in rows(store, _CONCLUDED_Q, (), g=SENSED + "/revisions") if r["p"].endswith("token")]
    assert 0 < len(tokens) <= 12
    assert any("did not settle" in m for m in caplog.messages)
    assert rows(store, "SELECT ?v WHERE { GRAPH ?c { $g $settled ?v } }", (), g=SENSED + "/revisions", settled=SETTLED)[0]["v"] == "false"


def test_a_cut_is_continued_from_what_is_held(snapshots):
    """The chain needs two iterations; a budget of one execution cuts the first call after
    the rule that runs first, and the next call continues from the held revision and settles
    with both — the same revisions the unbudgeted call leaves."""
    whole = snapshots.stand_in(CASES_DIR / "a_chain_settles_in_a_later_round.trig")
    revise(whole, SENSED, read=graphs_of(whole, *KNOWN))
    expected = {(r["s"], r["p"], r["o"]) for r in rows(whole, _CONCLUDED_Q, (), g=SENSED + "/revisions")}
    store = snapshots.stand_in(CASES_DIR / "a_chain_settles_in_a_later_round.trig")
    read = graphs_of(store, *KNOWN)
    first = revise(store, SENSED, read=read, budget=2)
    assert first == 2
    assert rows(store, "SELECT ?v WHERE { GRAPH ?c { $g $settled ?v } }", (), g=SENSED + "/revisions", settled=SETTLED)[0]["v"] == "false"
    revise(store, SENSED, read=read, budget=64)
    assert rows(store, "SELECT ?v WHERE { GRAPH ?c { $g $settled ?v } }", (), g=SENSED + "/revisions", settled=SETTLED)[0]["v"] == "true"
    assert {(r["s"], r["p"], r["o"]) for r in rows(store, _CONCLUDED_Q, (), g=SENSED + "/revisions")} == expected


def test_what_revising_costs(snapshots):
    """The price of one revision over one reading, printed (`pytest -s`): revised again and
    again on the same store. No figure is asserted — the Pi drifts — and the number is what the
    adoption by planning, a revision per fork, is priced against."""
    store = snapshots.stand_in(CASES_DIR / "a_reading_below_its_range_is_concluded_below.trig")
    read = graphs_of(store, *KNOWN)
    took = []
    for _ in range(20):
        began = time.perf_counter()
        revise(store, SENSED, read=read)
        took.append((time.perf_counter() - began) * 1000)
    print(f"\nrevise: median {statistics.median(took):.2f} ms, min {min(took):.2f} ms over {len(took)} runs")
    assert took


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 6, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)
