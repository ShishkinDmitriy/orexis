"""Identify the present among the worlds the last pass imagined, and keep what is under it.

THE PRESENT IS IDENTIFIED, NEVER ASSERTED
(the-future-is-a-cone-and-the-present-is-identified-in-it). A possible world is a prediction
of what the world comes to if the steps reaching it are taken; the ground just laid is what
was observed. Where a world the last pass kept holds what the ground holds — the same facts,
by hash — that world is the one the real one landed in, and its cone is the search already
done from here: the candidates leaving it are handed to the ground, every world beneath it is
re-stamped to stand where the ground stands, and everything else the last pass made — its
grounds, the siblings and their cones, the match itself, whose facts the ground now carries —
goes, with the weighings and candidates about it. Where nothing matches, the world surprised
the agent and nothing it imagined is about the present: everything goes, and the search starts
from the ground as a first pass would.

THE OLD PRESENT MATCHES TOO. A pass a minute later with nothing happened in between lays a
ground whose hash the last present's repeats, so the whole cone is kept under the new ground
and the search reads its way to the same plan without forking a world. This is the common
rerun, and it is the case a match among the children alone would have thrown away.

WHAT SHIFTS AND WHAT DOES NOT. `planning:atInstant` moves by the stretch from the match's
instant to the ground's, because a plan is placed at the instant of the root it is found from
and the root moved; `planning:spent` is rebased by what the match had spent, because spent is
the cost from the root. A kept world's FACTS do not move — they are the ground's plus the diffs
of its steps, which is what the hash guarantees. What is not re-asked is which candidates leave
a kept world: they were admitted at the instant it stood at in the last pass, and a fact that
holds by period — a round, a claim — may have begun or ended since. A candidate that appeared
is filled in by `admit`, which writes only what a world does not already admit; one that ended
is found when the step is taken, as every step is. That is the seam, and the executor's check
is what makes it safe.

THE MATCH IS BY HASH AND NOTHING ELSE — never by the name a graph was laid under and never by
where in the tree it sits. Two worlds may repeat one hash (a candidate whose fork repeated a
world already seen makes a graph before it is known to repeat); the first minted is the one
the search expanded, so it is the match, and a ground of the last pass ranks before any
world. A world attached to the new ground BY NAME — a ground re-laid under the name of the
last one, a test clock that did not move — is not the match and not kept: what hangs there was
forked from facts the ground may no longer hold, and `lay_ground` took the old graph's
verdicts with the graph.
"""

from __future__ import annotations

import logging

from orexis.agent.store import Raw, bind, catalogue_of, clear_graph, rows, update

log = logging.getLogger("reroot")

_HASH_Q = """SELECT ?h WHERE { GRAPH $cat { $ground orexis:hash ?h } }"""

#  THE MATCH: a world of the last pass — possible, or a ground not laid from this one — holding
#  the ground's facts, the earliest minted first and a ground before any world.
_MATCH_Q = """
SELECT ?w WHERE {
  GRAPH $cat {
    ?w orexis:hash $hash . FILTER(?w != $ground)
    { ?w a planning:PossibleGraph } UNION { ?w a planning:GroundGraph }
    FILTER NOT EXISTS { ?w prov:wasDerivedFrom+ $ground }
    FILTER NOT EXISTS { ?w (planning:by/planning:from)+ $ground }
    OPTIONAL { ?w planning:minted ?m } }
  BIND(COALESCE(?m, 0) AS ?minted) }
ORDER BY ?minted ?w LIMIT 1"""

#  THE GROUNDS OF THIS PASS: the one laid and every boundary laid from it.
_LAID_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g prov:wasDerivedFrom* $ground . ?g a planning:GroundGraph } }"""

#  THE CONE: every world reached from the match by taking candidates.
_CONE_Q = """
SELECT DISTINCT ?w WHERE { GRAPH $cat { ?w (planning:by/planning:from)+ $match } }"""

#  EVERYTHING A PASS LAYS OR FORKS.
_MADE_Q = """
SELECT ?w WHERE { GRAPH $cat { ?w a ?kind . VALUES ?kind { planning:PossibleGraph planning:GroundGraph }
                              FILTER(isIRI(?w)) } }"""

#  THE CONE RE-STAMPED: each world's instant moved by the stretch from the match's instant to
#  the ground's, and its spent less what the match had spent. A ground's instant is its
#  period's start and a world's is its own row, whichever the match is. The engine adds a
#  duration to an instant and takes one instant from another (measured on 0.5.9, and
#  `tests/test_reroot.py` pins it, since an operation it lacked would bind nothing and the
#  DELETE would strip every instant in silence).
_RESTAMP_U = """
DELETE { GRAPH $cat { ?w planning:atInstant ?a ; planning:spent ?s } }
INSERT { GRAPH $cat { ?w planning:atInstant ?a2 ; planning:spent ?s2 } }
WHERE  { GRAPH $cat {
  $ground dcterms:temporal/orexis:start ?g0 .
  OPTIONAL { $match planning:atInstant ?m0 } OPTIONAL { $match dcterms:temporal/orexis:start ?m1 }
  OPTIONAL { $match planning:spent ?ms }
  ?w (planning:by/planning:from)+ $match ; planning:atInstant ?a ; planning:spent ?s }
  BIND(COALESCE(?m0, ?m1) AS ?m) BIND(?a + (?g0 - ?m) AS ?a2) BIND(?s - COALESCE(?ms, 0.0) AS ?s2) }"""

#  THE MATCH'S CANDIDATES LEAVE THE GROUND NOW.
_REPARENT_U = """
DELETE { GRAPH $cat { ?c planning:from $match } }
INSERT { GRAPH $cat { ?c planning:from $ground } }
WHERE  { GRAPH $cat { ?c planning:from $match } }"""

#  WHAT THE CATALOGUE SAID OF THE GRAPHS THAT WENT, their periods with them — one text for all
#  of them, where `forget_graph` would be two round trips each over tens of worlds.
_DROP_GRAPHS_U = """
DELETE { GRAPH $cat { ?g ?p ?o . ?period ?pp ?po } }
WHERE  { GRAPH $cat { VALUES ?g { $graphs } ?g ?p ?o .
                      OPTIONAL { ?g dcterms:temporal ?period . ?period ?pp ?po } } }"""

#  EVERY WEIGHING AND CANDIDATE ABOUT A WORLD THAT IS GONE — a weighing of a candidate is about
#  the world the candidate leaves — with the violation rows hanging off a weighing.
_DROP_ROWS_U = """
DELETE { GRAPH $cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH $cat {
  { ?x a planning:Weighing ; planning:weighs ?w . OPTIONAL { ?w planning:from ?f } }
  UNION { ?x a planning:Candidate ; planning:from ?f }
  BIND(COALESCE(?f, ?w) AS ?home) FILTER NOT EXISTS { ?home a ?kind }
  ?x ?p ?o . OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"""


def reroot(store, ground: str) -> str | None:
    """Find the world the last pass imagined that `ground` — the present just laid — landed
    in, hand its cone to the ground, and drop everything else the last pass made. The world
    matched, or None where the present surprised the agent and nothing was kept.

    Handed the ground and nothing else: its hash is on its row, the worlds are in the store,
    and what is kept is what the rows reach.
    """
    cat = Raw(f"<{catalogue_of(store)}>")
    found = next(iter(rows(store, _HASH_Q, (), ground=ground, cat=cat)), None)
    if found is None:
        raise LookupError(f"{ground} has no hash — is it a ground lay_ground laid?")
    match = next((r["w"] for r in rows(store, _MATCH_Q, (), ground=ground, cat=cat,
                                        hash=Raw(f'"{found["h"]}"'))), None)
    kept = {r["g"] for r in rows(store, _LAID_Q, (), ground=ground, cat=cat)}
    if match is not None:
        kept |= {r["w"] for r in rows(store, _CONE_Q, (), match=match, cat=cat)}
        update(store, bind(_RESTAMP_U, ground=ground, match=match, cat=cat))
        update(store, bind(_REPARENT_U, ground=ground, match=match, cat=cat))
    gone = sorted(r["w"] for r in rows(store, _MADE_Q, (), cat=cat) if r["w"] not in kept)
    for graph in gone:
        clear_graph(store, graph)
    if gone:
        update(store, bind(_DROP_GRAPHS_U, cat=cat, graphs=Raw(" ".join(f"<{g}>" for g in gone))))
        update(store, bind(_DROP_ROWS_U, cat=cat))
    if match is None and not gone:
        log.debug("nothing imagined yet: the present is the ground")
    else:
        log.info("the present is %s; %d world(s) kept, %d dropped",
                 "a surprise" if match is None else match.rsplit("/", 1)[-1], len(kept), len(gone))
    return match
