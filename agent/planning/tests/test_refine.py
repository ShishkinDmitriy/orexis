"""`refine`: a step whose predicted fact a rule concludes is kept one level down, as a want whose
met-test is the rule run backwards over the world the step lands in.

The case is the tower's shape at its smallest: a disk is on the peg standing on its cell, a rule
says so, and a step moving the disk to peg B is a want below that the disk stand on B's cell —
while the disk that was not moved stays where the level above left it.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pyoxigraph as ox

from agent.planning.refine import refine
from agent.store import close_catalogue, graphs_of, put_graph, rows

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
ME = "http://example.org/test#mover"
STEP = "http://example.org/test#step"
T = "http://example.org/test#"
WANT = "http://example.org/orexis/planning#WantGraph"

_CASE = """
@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

GRAPH :catalogue {
  :catalogue a orexis:CatalogueGraph , orexis:Graph .
  :rules a sh:RulesGraph , orexis:PublicGraph , orexis:Graph .
  :state a orexis:StateGraph , orexis:Graph .
}
GRAPH :rules {
  :stands a sh:SPARQLRule ; sh:construct \"\"\"PREFIX : <http://example.org/test#>
    CONSTRUCT { ?disk :on ?peg } WHERE { ?disk :at ?cell . ?peg a :Peg ; :at ?cell }\"\"\" .
  :twice a sh:SPARQLRule ; sh:construct \"\"\"PREFIX : <http://example.org/test#>
    CONSTRUCT { ?disk :near ?peg . ?peg :near ?disk } WHERE { ?disk :at ?cell . ?peg :at ?cell }\"\"\" .
}
GRAPH :state {
  :pegA a :Peg ; :at :c1 .  :pegB a :Peg ; :at :c2 .
  :d :at :c1 ; :on :pegA .  :e :at :c1 ; :on :pegA .
}
"""


def _store() -> ox.Store:
    st = ox.Store()
    put_graph(st, T + "state", _CASE, dataset=True)
    close_catalogue(st)
    return st


def _iri(x):
    return ["iri", x]


def _met(store, want: str, state: str) -> bool:
    """The minted met-test, run as the search runs it: a violation row is the want unmet."""
    (row,) = rows(store, "SELECT ?q WHERE { ?s sh:select ?q }", graphs_of(store, WANT))
    return not rows(store, row["q"].replace("SELECT $this", "SELECT *"), [state])


def test_a_step_whose_fact_a_rule_concludes_is_a_want_below():
    store = _store()
    want = refine(store, ME, STEP, [[_iri(T + "d"), T + "on", _iri(T + "pegB")]], NOW,
                  retracts=[[_iri(T + "d"), T + "on", _iri(T + "pegA")]])
    assert want == STEP + ".below"
    (row,) = rows(store, "SELECT ?step WHERE { ?step execution:keptBy ?w }", graphs_of(store, WANT))
    assert row["step"] == STEP
    assert not _met(store, want, T + "state"), "the disk still stands on A's cell"


def test_the_want_below_is_the_world_the_step_lands_in_not_its_diff():
    """The moved disk on B's cell AND the one the step left alone still on A's: carrying `e`
    away as well reaches the diff and breaks the frame the level above stands on."""
    store = _store()
    want = refine(store, ME, STEP, [[_iri(T + "d"), T + "on", _iri(T + "pegB")]], NOW,
                  retracts=[[_iri(T + "d"), T + "on", _iri(T + "pegA")]])
    moved = T + "moved"
    put_graph(store, moved, """@prefix : <http://example.org/test#> .
        :pegA a :Peg ; :at :c1 . :pegB a :Peg ; :at :c2 . :d :at :c2 . :e :at :c1 .""")
    assert _met(store, want, moved)
    both = T + "both"
    put_graph(store, both, """@prefix : <http://example.org/test#> .
        :pegA a :Peg ; :at :c1 . :pegB a :Peg ; :at :c2 . :d :at :c2 . :e :at :c2 .""")
    assert not _met(store, want, both)


def test_a_step_no_rule_concludes_is_taken_as_it_would_be():
    store = _store()
    assert refine(store, ME, STEP, [[_iri(T + "d"), T + "painted", _iri(T + "red")]], NOW) is None
    assert not graphs_of(store, WANT), "nothing minted"


def test_a_rule_of_two_head_triples_is_not_run_backwards():
    store = _store()
    assert refine(store, ME, STEP, [[_iri(T + "d"), T + "near", _iri(T + "pegB")]], NOW) is None
