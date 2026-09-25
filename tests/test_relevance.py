"""Which levers could serve a want, read off the actions and closed backward (#488).

The unit half: that the closure keeps a chain alive, that a derivation rule is an edge in it,
and that anything unreadable keeps every action — over-approximation is safe and
under-approximation prunes a needed step. What the sets were on the puzzles went with them to
Agent 0.2.0, where `agent/planning/footprint.py` is what reads them.
"""

import rdflib

from conftest import genesis_store

from orexis_agent_deliberation import relevance as R
from orexis_agent_progression.ontology import PUBLIC

C = "http://example.org/orexis/courier#"
H = "http://example.org/orexis/hanoi#"
X = rdflib.Namespace("http://example.org/x#")


def _short(s):
    return None if s is None else {str(p).rsplit("#", 1)[-1] for p in s}


def test_the_closure_keeps_a_chain_alive():
    """A want reads D. Only `dose` writes D, and `dose` reads a claim C. Only `bid` writes C,
    and reads M. Filtering to levers that touch the goal would keep `dose` alone and delete
    the plan; the closure brings `bid` in on the second round and stops there — `unrelated`,
    which writes nothing anybody reads, never enters."""
    acts = {
        "dose": (frozenset({X.C}), frozenset({X.D})),
        "bid": (frozenset({X.M}), frozenset({X.C})),
        "unrelated": (frozenset({X.M}), frozenset({X.Z})),
    }
    assert R.relevant(frozenset({X.D}), acts) == {"dose", "bid"}


def test_a_derivation_rule_is_an_edge_in_the_closure():
    """A want reads D, which no action writes: a RULE derives D from A, and `feed` writes A.
    The rule joins the closure as an edge — reads A, writes D — with no row of its own, so
    `feed` is relevant. Reasoning is saturation for the search and an edge for relevance."""
    acts = {"feed": (frozenset(), frozenset({X.A})), "other": (frozenset(), frozenset({X.B}))}
    rule = (frozenset({X.A}), frozenset({X.D}))
    assert R.relevant(frozenset({X.D}), acts, rules=(rule,)) == {"feed"}
    assert R.relevant(frozenset({X.D}), acts) == frozenset(), "and without the rule, nothing"


def test_a_narrower_property_reaches_a_want_reading_the_broader_one():
    """The entailment folds `narrow rdfs:subPropertyOf broad` into `broad`, so a want reading
    the broad word is served by an action writing the narrow one."""
    acts = {"narrowly": (frozenset(), frozenset({X.narrow}))}
    assert R.relevant(frozenset({X.broad}), acts, subproperties={X.broad: {X.narrow}}) \
        == {"narrowly"}
    assert R.relevant(frozenset({X.broad}), acts) == frozenset()


def test_anything_unreadable_keeps_every_action():
    """The rule the design rests on. A want that reads ANYTHING filters nothing; an action
    whose effect is ANYTHING is always relevant; a relevant action whose precondition is
    ANYTHING widens the want to everything."""
    acts = {"a": (frozenset(), frozenset({X.p})), "b": (frozenset(), frozenset({X.q}))}
    assert R.relevant(R.ANYTHING, acts) is R.ANYTHING
    acts["c"] = (frozenset(), R.ANYTHING)
    assert "c" in R.relevant(frozenset({X.p}), acts)
    acts["a"] = (R.ANYTHING, frozenset({X.p}))
    assert R.relevant(frozenset({X.p}), acts) is R.ANYTHING

    assert R.reads_of_select("this is not sparql") is R.ANYTHING
    assert R.writes_of_construct("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }") is R.ANYTHING
    assert R.edges_of_update("not an update") == ((R.ANYTHING, R.ANYTHING),)


def test_the_rule_texts_parse_with_their_tokens_stood_in():
    """Every `rules.ru` the tree ships parses once its `$given`, `$derived` and `$into(...)`
    tokens are stood in — so the edges are read rather than guessed. Pinned because a new
    token in a rule would silently turn that rule into an ANYTHING edge, which widens every
    want it touches to everything."""
    edges = R.rule_edges()
    assert edges, "no rule anywhere would mean the loader found nothing"
    unreadable = [e for e in edges if e[0] is R.ANYTHING or e[1] is R.ANYTHING]
    assert not unreadable, f"{len(unreadable)} rule edges read as ANYTHING"


def test_a_pattern_under_not_exists_is_read():
    """A want saying "unmet while this fact is absent" reads that fact's predicate — the
    shape a promise's want takes (#523) — and `traverse` never descended into a filter's
    expression on its own, so such a want read nothing and every action was irrelevant."""
    text = ("SELECT ?unmet WHERE { BIND(1 AS ?unmet) FILTER NOT EXISTS { { "
            "<urn:x#disk> <urn:x#at> <urn:x#cell> . } } }")
    assert {str(p) for p in R.reads_of_select(text)} == {"urn:x#at"}
