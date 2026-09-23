"""What is still to be weighed — the read the Planner asks before every round of weighing, and
the one the derivation's and the weighing's cases ask too, so no harness spells a rule of its
own about what a pass weighs next.

THREE KINDS OF PAIR, and every one is `(for, about)` as `weigh` takes them:

- every DESIRE in every ground it is not weighed in — what the derivation reads its wants off;
- every WANT in the PRESENT ground it is not weighed in — the root of the want's search, and
  only the present: a want weighed in a later ground would be a later ground on its
  frontier, spent nought, and the search would open the future instead of the present;
- for every want, every CANDIDATE leaving a world the want has weighed that it has weighed
  neither the candidate nor the world it reached — which is what an iteration weighs after
  admitting and taking, and what a pass cut by the budget takes up.

A candidate's row says which world it leaves (`from`) and, where it was taken, which it
reached (`child`), so the Planner can take the ones not yet taken and hold an iteration to
the world it is opening. THE FILTERS STAND AT THE TOP OF THE WHERE: inside the catalogue's
group they could not see the variable the union bound, NOT EXISTS matched any weighing, and a
store holding one had nothing left to weigh — the trap AGENTS.md records for BIND and UNION.
And the catalogue is bound ONCE, before the union, so each filter joins on it rather than
finding it again; and the graphs a desire or a want lives in are asked BY CLASS, because
`GRAPH ?d` unbound scans every named graph there is — every possible world included — for a
pattern only a desire or want graph can match.
"""

from __future__ import annotations

from orexis.agent.store import Raw, catalogue_of, remember, rows

#  THE CATALOGUE IS BOUND, NOT FOUND, IN THE HOT READS: `GRAPH ?cat { ?cat a
#  orexis:CatalogueGraph . … }` makes the engine evaluate the group per named graph, and with
#  a store of sixteen possible worlds each such read cost 0.5 to 1.0 ms where a read over one
#  bound graph costs 0.1 to 0.2 — measured on the two-disk bench. The name is asked of the
#  store once per pass (`catalogue_of`, remembered) and spliced as `$cat`: a reader asking
#  the store for the catalogue's name is what the rule allows; spelling it is what it refuses.

_IN_GROUNDS_Q = """
SELECT ?for ?about WHERE {
  { GRAPH $cat { ?d a orexis:DesireGraph } GRAPH ?d { ?holder orexis:holds ?for . ?for a orexis:Desire $narrow }
    GRAPH $cat { ?about a planning:GroundGraph } }
  UNION
  { GRAPH $cat { ?d a orexis:WantGraph } GRAPH ?d { ?holder orexis:holds ?for . ?for a orexis:Want $narrow }
    { SELECT ?about WHERE {
        GRAPH ?c1 { ?c1 a orexis:CatalogueGraph . ?about a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }
      ORDER BY ?start LIMIT 1 } }
  FILTER NOT EXISTS { GRAPH $cat { ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?about } } }
ORDER BY ?for ?about"""

#  THE BOUND VARIABLE FIRST IN A `NOT EXISTS`. The engine evaluates one per row, from its first
#  pattern: `?x a planning:Weighing ; … ; planning:weighs ?about` scanned every weighing per
#  candidate, and on a store keeping a three-disk cone across the pass — 56 worlds, some 180
#  weighings — the read cost 74 ms and answered nothing; `?x planning:weighs ?about ; …` costs
#  4. Only a weighing says `planning:weighs`, so the type it no longer asks is not a check
#  given up.
_CANDIDATES_Q = """
SELECT ?for ?about ?from ?child WHERE {
  GRAPH $cat { ?d a orexis:WantGraph }
  GRAPH ?d { ?holder orexis:holds ?for . ?for a orexis:Want $narrow }
  GRAPH $cat {
    ?about a planning:Candidate ; planning:from ?from $leaving .
    ?y planning:weighs ?from ; planning:for ?for ; a planning:Weighing .
    OPTIONAL { ?child planning:by ?about } }
  FILTER NOT EXISTS { GRAPH $cat { ?x planning:weighs ?about ; planning:for ?for } }
  FILTER NOT EXISTS { GRAPH $cat { ?c planning:by ?about . ?z planning:weighs ?c ; planning:for ?for } } }
ORDER BY ?for ?about"""


def unweighed(store, *, for_: str | None = None, leaving: str | None = None, memo=None) -> list[dict]:
    """Every `(for, about)` still to be weighed, in name order: desires in grounds and wants in
    the present ground first, then candidates — each with `from`, the world it leaves, and
    `child`, the world it reached where it was taken.

    NARROWED WHERE THE CALLER KNOWS: `for_` to one want's or desire's, `leaving` to the
    candidates leaving one world — which is what an iteration opens, and asks for nothing
    else. The whole read, asked per iteration and filtered in Python, cost a fifth of a
    two-disk pass; narrowed, the desire branch is not asked at all and the candidate branch
    binds the world.
    """
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    narrow = Raw(f"VALUES ?for {{ <{for_}> }}" if for_ else "")
    out = [] if leaving else rows(store, _IN_GROUNDS_Q, (), cat=cat, narrow=narrow)
    return out + rows(store, _CANDIDATES_Q, (), cat=cat, narrow=narrow,
                      leaving=Raw(f"VALUES ?from {{ <{leaving}> }}" if leaving else ""))
