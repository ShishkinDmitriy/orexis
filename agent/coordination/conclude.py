"""`conclude`: what an agent concludes of its conflicts, each from its own documents
(knowledge/domain/coordination/conflict.md).

**EACH AGENT DECIDES ITSELF THAT THERE IS A CONFLICT.** An answer that is not empty — one the agent said, or
one it heard — under a constraint both hold is a conflict with that peer, read by the same rule by both and
told to neither. Two answers between one pair under one constraint are one conflict, named for the pair and
the constraint (`conflict_of`), so both agents name it alike. It STANDS while the peer is believed in range,
whatever the answers say after: two plans that no longer meet are what yielding made of them, and a conflict
ended there would stop the laying that keeps them apart. A peer believed nowhere ends it, and a later answer
that is not empty begins it again in a later round.

**ROUNDS.** A standing conflict's draw is the one of its present round (`draw_of`). Undecided for the
agent's patience, it restarts in the next round; a peer heard drawing in a later round brings this agent to
it, so two agents whose clocks parted meet in one draw again; and past the rounds the agent states of itself
the peer is SILENT, and this agent yields to it as a loser does.

**WHO WON IS ASKED, NOT TRIGGERED.** Every outcome a world's rules ship (`coordination:Outcome`) is asked each
pass over everything the agent believes, and what it concludes of the present round's draw is written beside the
conflict as `coordination:wonBy`: a peer's word is a statement no reader of the mind is handed, and what is
extracted of it is the agent's own and triggers no transition, so a rule that waited for an arrival would wait
for ever. A winner once concluded stands for the round, whatever is said after.

WRITTEN WHERE IT CHANGED, as one belief of the agent's own (`conflicts_graph`), derived and stamped, which a
draw's documents read.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent.hash_named_graph import hash_named_graph
from agent.ontology import BELIEF, DERIVED, RECEIVED, RECORDED, local_of
from agent.stance import stance
from agent.store import Raw, catalogue_of, construct, entry, forget_graph, graphs_of, rows, update

from .ask import _in_range
from .holdings import _key_of
from .ontology import CONFLICT, COORDINATION, PATIENCE_S, ROUNDS, WON_BY, conflict_of, conflicts_graph, draw_of

log = logging.getLogger("coordination")

PATIENCE = 60.0
BOUND = 3

#  EVERY ANSWER BETWEEN THE AGENT AND A PEER, said or heard, with the constraint and whether it carries a holding.
_ANSWERS_Q = """
SELECT ?g ?asker ?answerer ?constraint (COUNT(?h) AS ?held) WHERE {
  GRAPH $cat { ?g a coordination:AnswerGraph ; orexis:arrivedBy ?arrival . VALUES ?arrival { $recorded $received } }
  GRAPH ?g { ?a a coordination:Answer ; coordination:answeredBy ?answerer ; coordination:over ?constraint ; coordination:answers ?q .
             OPTIONAL { ?a coordination:holding ?h } }
  GRAPH ?qg { ?q coordination:asks ?asker } }
GROUP BY ?g ?asker ?answerer ?constraint"""
#  WHAT THE AGENT CONCLUDED BEFORE.
_PRIOR_Q = """
SELECT ?c ?peer ?constraint ?round ?since ?standing ?silent ?winner WHERE { GRAPH $graph {
  ?c a coordination:Conflict ; coordination:with ?peer ; coordination:over ?constraint ; coordination:round ?round ;
     coordination:since ?since ; coordination:draw ?draw . OPTIONAL { ?c coordination:standing ?standing }
  OPTIONAL { ?c coordination:silent ?silent } OPTIONAL { ?draw coordination:wonBy ?winner } } }"""
#  THE LATEST ROUND A PEER WAS HEARD DRAWING A CONFLICT IN, as a draw's documents say it in this package's word.
_HEARD_Q = "SELECT (MAX(?r) AS ?round) WHERE { $conflict coordination:drawnIn ?r }"
#  EVERY OUTCOME THE WORLD'S RULES SHIP, with its text.
_OUTCOMES_Q = """
SELECT ?rule ?text WHERE { ?rule a coordination:Outcome ; sh:construct ?text .
                           FILTER NOT EXISTS { ?rule sh:deactivated true } } ORDER BY ?rule"""
_RULES_GRAPH = "http://www.w3.org/ns/shacl#RulesGraph"


def conclude(store: ox.Store, me: str, at: datetime) -> list[str]:
    """Conclude the conflicts of the self `me` of `store` at `at`, and write them where they changed; the
    graph written, or none."""
    cat = catalogue_of(store)
    if cat is None:
        return []
    patience = timedelta(seconds=stance(store, PATIENCE_S, PATIENCE))
    bound = stance(store, ROUNDS, BOUND)
    graph = conflicts_graph(me)
    prior = {r["c"]: r for r in rows(store, _PRIOR_Q, (), graph=Raw(f"<{graph}>"))}
    won = _won(store)
    met: dict[tuple[str, str], bool] = {}
    for r in rows(store, _ANSWERS_Q, (), cat=Raw(f"<{cat}>"), recorded=RECORDED, received=RECEIVED):
        if me not in (r["asker"], r["answerer"]):
            continue
        peer = r["answerer"] if r["asker"] == me else r["asker"]
        met[(peer, r["constraint"])] = met.get((peer, r["constraint"]), False) or int(r["held"]) > 0
    beliefs = graphs_of(store, BELIEF)
    concluded: dict[str, dict] = {}
    for c, r in prior.items():
        concluded[c] = {"peer": r["peer"], "constraint": r["constraint"], "round": int(r["round"]),
                        "since": datetime.fromisoformat(r["since"]), "standing": r.get("standing") == "true",
                        "silent": r.get("silent") == "true", "winner": r.get("winner")}
    for (peer, constraint), meets in sorted(met.items()):
        c = conflict_of(me, peer, constraint)
        row = concluded.setdefault(c, {"peer": peer, "constraint": constraint, "round": 0, "since": at,
                                       "standing": False, "silent": False, "winner": None})
        row["winner"] = row["winner"] or won.get(draw_of(c, row["round"]))
        decided = row["winner"] is not None
        in_range = peer in _in_range(store, me, _key_of(store, constraint), at)
        if not in_range or not (meets or row["standing"]):
            row["standing"] = False         # ended by the peer going out of range, never by plans that now avoid
            continue                        # each other, which is what yielding made of them
        if not row["standing"]:
            if c in prior and decided:
                row["round"] += 1                 # a later conflict between the pair is a later draw
            row.update(standing=True, since=at, silent=False, winner=won.get(draw_of(c, row["round"])))
            decided = row["winner"] is not None
        heard = rows(store, _HEARD_Q, beliefs, conflict=c)
        if heard and heard[0].get("round") is not None and int(heard[0]["round"]) > row["round"]:
            row.update(round=int(heard[0]["round"]), since=at, winner=won.get(draw_of(c, int(heard[0]["round"]))))
        elif not decided and not row["silent"] and at - row["since"] >= patience:
            row.update(round=row["round"] + 1, since=at, winner=None)
        if not decided and row["round"] >= bound:
            row["silent"] = True
    return _written(store, me, graph, concluded, prior)


def _won(store: ox.Store) -> dict[str, str]:
    """Who won each draw, as every outcome the world's rules ship concludes it over what the agent believes."""
    beliefs = graphs_of(store, BELIEF)
    out: dict[str, str] = {}
    for r in rows(store, _OUTCOMES_Q, graphs_of(store, _RULES_GRAPH)):
        try:
            found = construct(store, r["text"], beliefs)
        except Exception as exc:                                    # noqa: BLE001
            log.error("%s: an outcome would not run, so it concludes nothing: %s", local_of(r["rule"]), exc)
            continue
        for t in found:
            if t.predicate.value == WON_BY:
                out.setdefault(t.subject.value, t.object.value)
    return out


def _written(store: ox.Store, me: str, graph: str, concluded: dict, prior: dict) -> list[str]:
    """The conflicts graph rewritten where what it says changed; the graph, or none."""
    def said(c, row):
        return (row["peer"], row["constraint"], str(row["round"]), row["since"].isoformat(),
                "true" if row["standing"] else None, "true" if row["silent"] else None, row["winner"])
    was = {c: (r["peer"], r["constraint"], r["round"], datetime.fromisoformat(r["since"]).isoformat(),
               r.get("standing"), r.get("silent"), r.get("winner")) for c, r in prior.items()}
    now = {c: said(c, row) for c, row in concluded.items()}
    if now == was:
        return []
    forget_graph(store, graph)
    if not now:
        return []
    facts = []
    for c, row in sorted(concluded.items()):
        facts.append(f"<{c}> a <{CONFLICT}> ; <{COORDINATION}with> <{row['peer']}> ; <{COORDINATION}over> <{row['constraint']}> ; "
                     f"<{COORDINATION}round> {row['round']} ; <{COORDINATION}since> \"{row['since'].isoformat()}\"^^xsd:dateTime ; "
                     f"<{COORDINATION}draw> <{draw_of(c, row['round'])}>"
                     + (f" ; <{COORDINATION}standing> true" if row["standing"] else "")
                     + (f" ; <{COORDINATION}silent> true" if row["silent"] else "") + " .")
        if row["winner"]:
            facts.append(f"<{draw_of(c, row['round'])}> <{WON_BY}> <{row['winner']}> .")
    update(store, f"INSERT DATA {{ GRAPH <{graph}> {{ {' '.join(facts)} }} {entry(store, graph, BELIEF, DERIVED, me)} }}")
    hash_named_graph(store, graph)
    return [graph]
