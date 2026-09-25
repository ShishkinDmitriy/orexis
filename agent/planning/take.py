"""Taking one candidate: the world it reaches, forked from the world it leaves with the
action's effect applied, and that world's own row — what is true of it whoever asks.

**ONE ACT, AND EVERYTHING THE ACT ASKS.** What a candidate's rules are filled with, what the
action's row says, what taking it costs and how long it takes to land, and the running of its
effect into the new world were three modules — `effects`, `apply_effects` and this — with one
caller between them, this. A question only one act asks is that act's, so they are here as
its parts, and a reader who wants to know what taking a candidate does opens one file.

**EVERYTHING IT NEEDS IS ON THE CANDIDATE'S ROW OR THE PARENT'S**, read in ONE query: which
world it is taken in, what it fills, what that world spent and when it is; the action's texts
off public knowledge; the next mint number off the pass's memo, read from the store once. `me` is the one
identifier a process is handed. False where the action's rules say nothing about this world
— no effect stated, or a construct and a retraction that both come to nothing — which is not
a move, and the caller's weighing then says the candidate repeats the world it left.

An action states its effect in two halves that are not the same KIND of thing. `sh:construct`
is SHACL-AF's and holds a query yielding the triples applying it would ADD, asked of the world
the candidate is taken in. `orexis:retracts` is ours, because the standard has none, and holds
a `DELETE … WHERE` naming `GRAPH $state` — an ACT, run against the world the candidate MAKES.
The asymmetry is the domain's: what an effect adds is concrete, and what it takes away is
whatever is standing in that place, which nobody can name in advance. The order the halves go
in is `fork.py`'s, shared with the boundary a prediction makes.

**The vocabulary is SHACL-AF's; the engine is not.** pySHACL will execute `sh:SPARQLRule`, but
only as forward-chaining inference to a fixpoint; a plan step is one rule against one
hypothesis, the opposite shape. A stored `sh:construct` is just a query, and this project has
an engine that runs queries. See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md.

THE CHILD IS NAMED FOR THE CANDIDATE, `<child>.by` being `admit`'s spelling of a candidate,
so the edge and the world it makes are one spelling apart. A name is for eyes: every reader
asks `planning:by` and `planning:from`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from agent.hash_named_graph import digest_of
from agent.ontology import ACTION, PUBLIC, local_of
from agent.store import (Raw, bind, bindings, catalogue_of, closed, construct, fork,
                                graphs_of, instant, query, remember, render, rows, update)

from .ontology import POSSIBLE_GRAPH
from .world_at import world_at

#  THE CATALOGUE IS BOUND, NOT FOUND, IN THE HOT READS: `GRAPH ?cat { ?cat a
#  orexis:CatalogueGraph . … }` makes the engine evaluate the group per named graph, and with
#  a store of sixteen possible worlds each such read cost 0.5 to 1.0 ms where a read over one
#  bound graph costs 0.1 to 0.2 — measured on the two-disk bench. The name is asked of the
#  store once per pass (`catalogue_of`, remembered) and spliced as `$cat`: a reader asking
#  the store for the catalogue's name is what the rule allows; spelling it is what it refuses.

log = logging.getLogger("take")

#  THE ACTION'S TEXTS, read off public knowledge like everything else. `?rule` is bound by
#  SUBSTITUTION (#500), the engine's own parameter, projected. An action with no construct
#  states no effect and is not returned. `STR(?takes)` because GROUP_CONCAT over an IRI binds
#  nothing in this engine.
_RULE_Q = """
SELECT ?rule ?construct ?available ?retracts ?lands ?costs (GROUP_CONCAT(DISTINCT STR(?p); separator=" ") AS ?takes) WHERE {
  ?rule a orexis:Action ; sh:construct ?construct .
  OPTIONAL { ?rule orexis:takes ?p }
  OPTIONAL { ?rule orexis:available ?available }
  OPTIONAL { ?rule orexis:retracts ?retracts }
  OPTIONAL { ?rule orexis:landsAfter ?lands }
  OPTIONAL { ?rule orexis:costs ?costs }
} GROUP BY ?rule ?construct ?available ?retracts ?lands ?costs LIMIT 1"""

#  THE CANDIDATE'S ROW: the world it is taken in, when that world is, the action it fills,
#  and every parameter it is filled with — the parameter's IRI and the value, one row each.
_CANDIDATE_Q = """
SELECT ?from ?at ?spent ?action ?p ?v WHERE {
  GRAPH $cat { $cand planning:from ?from ; planning:fills ?action .
    OPTIONAL { ?from planning:atInstant ?a } OPTIONAL { ?from dcterms:temporal/orexis:start ?start }
    OPTIONAL { ?from planning:spent ?s }
    OPTIONAL { $cand ?p ?v . FILTER(?p NOT IN (planning:from, planning:fills, rdf:type)) } }
  BIND(COALESCE(?a, ?start) AS ?at) BIND(COALESCE(?s, 0.0) AS ?spent) }"""

#  WHOM THE AGENT ACTS FOR, off the world graph — `$subject` in a rule text.
_ACTS_FOR_Q = """SELECT ?for WHERE { $me orexis:actsFor ?for } LIMIT 1"""


#  THE HIGHEST MINT NUMBER IN THE STORE — the worlds are the scope's, so the counter is too.
_MINTED_Q = """
SELECT (MAX(?m) AS ?n) WHERE { GRAPH $cat { ?w planning:minted ?m } }"""

#  A WORLD'S OWN ROW: every kind the vocabulary puts a possible graph beneath, how it arrived,
#  what it holds by hash, what reaching it spent, when it is, where it came in the order the
#  pass made worlds, and the candidate that made it.
_WORLD_U = """
INSERT { GRAPH ?cat { $world a $kinds ; orexis:arrivedBy orexis:Derived ; orexis:hash $hash ;
                      planning:spent $spent ; planning:atInstant $at ; planning:minted $minted ;
                      planning:by $cand } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"""


#  THE CANDIDATE'S ROW: the world it is taken in, when that world is, the action it fills,
#  and every parameter it is filled with — the parameter's IRI and the value, one row each.
_CANDIDATE_Q = """
SELECT ?from ?at ?spent ?action ?p ?v WHERE {
  GRAPH $cat {
    $cand planning:from ?from ; planning:fills ?action .
    OPTIONAL { ?from planning:atInstant ?a } OPTIONAL { ?from dcterms:temporal/orexis:start ?start }
    OPTIONAL { ?from planning:spent ?s }
    OPTIONAL { $cand ?p ?v . FILTER(?p NOT IN (planning:from, planning:fills, rdf:type)) } }
  BIND(COALESCE(?a, ?start) AS ?at) BIND(COALESCE(?s, 0.0) AS ?spent) }"""

#  WHOM THE AGENT ACTS FOR, off the world graph — `$subject` in a rule text.



def take(store, cand: str, me: str, *, memo=None) -> bool:
    """Fork the world `cand` reaches and write its row. False, and nothing made, where the
    candidate's effect changes nothing in the world it leaves.

    WHAT THE STEP COSTS AND HOW LONG IT TAKES TO LAND are asked of the world it is taken IN,
    before anything is applied — a cost read off the state it is about to change would answer
    about the change. `planning:atInstant` is the parent's instant plus the landing, written
    and not derived, because this engine binds nothing for duration arithmetic.
    """
    child = cand.removesuffix(".by")
    binding = _binding(store, cand, me, memo)
    cost = _figure(store, cand, me, memo, "costs", "cost") or 0.0
    lands = _figure(store, cand, me, memo, "lands", "seconds") or 0.0
    if not _apply(store, cand, child, me, memo):
        return False
    #  EVERY KIND A POSSIBLE GRAPH IS BENEATH, once per pass: the closure is materialised at
    #  genesis, so one `rdfs:subClassOf` step is every step, and a row written with them all
    #  is what lets a reader ask `?g a orexis:WorkingGraph` and walk no path.
    kinds = remember(memo, ("closed", POSSIBLE_GRAPH), lambda: closed(store, POSSIBLE_GRAPH))
    #  THE MINT COUNTER IS THE PASS'S: read off the store once, advanced per world made. The
    #  store stays the truth — a pass resumed reads MAX again — and reading MAX per world
    #  cost a tenth of a search on the two-disk bench.
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    minted = remember(memo, ("minted",), lambda: int(rows(store, _MINTED_Q, (), cat=cat)[0].get("n") or 0)) + 1
    if memo is not None:
        memo.put(("minted",), minted)
    at = datetime.fromisoformat(binding["at"]) + timedelta(seconds=lands)
    update(store, bind(_WORLD_U, world=child, cand=cand,
                       kinds=Raw(" , ".join(f"<{k}>" for k in kinds)),
                       hash=Raw(f'"{digest_of(store, child)}"'),
                       spent=binding["spent"] + cost, at=instant(at), minted=minted))
    return True


def _apply(store, cand: str, into: str, me: str, memo) -> bool:
    """Make `into` out of the world `cand` is taken in, with the action's effect applied: what
    it makes true added, what it replaces deleted. False, and no graph made, where the
    action's rules say NOTHING about this world — no effect stated, or a construct and a
    retraction that both come to nothing — which is not a move.

    The construct is asked BEFORE the fork exists, of the world the candidate leaves, so it
    never sees the deletion; **the retraction is re-bound to `into`**, because that is what
    it deletes from — the one place the two halves differ.
    """
    binding = _binding(store, cand, me, memo)
    rule = _rule(store, binding["action"], memo)
    if rule is None:
        return False
    tokens = {k: v for k, v in binding.items() if k not in ("action", "from", "at", "spent")}
    added = _run(store, rule.get("construct"), tokens, world_at(store, binding["from"], memo=memo))
    retract = _retraction(rule.get("retracts"), into, tokens)
    if not added and retract is None:
        return False
    fork(store, binding["from"], into, added, [retract] if retract is not None else [])
    return True


def _retraction(text: str | None, into: str, tokens: dict) -> str | None:
    """One action's `orexis:retracts`, bound to the graph it deletes from — or None.

    IT READS THE WORLD AND NOT THE DATASET: an UPDATE's WHERE reads the unnamed default graph
    unless `USING` says otherwise, and `Store.update` takes no dataset — so a retraction names
    `GRAPH $state` in both halves and sees only the world it deletes from. `orexis:retracts`
    exists because SHACL-AF has no deletion, and it is not optional: the sensed graph upserts
    one observation node per (subject, property), so an effect predicting a reading that did
    not retract the node it replaces would leave two results on one node.
    """
    if not text:
        return None
    try:
        return bind(text, **{**tokens, "state": Raw(f"<{into}>")})
    except Exception as exc:                                        # noqa: BLE001
        log.error("an effect's retraction would not bind, so it retracts nothing: %s", exc)
        return None


def _run(store, text: str | None, tokens: dict, graphs) -> list:
    if not text:
        return []
    try:
        return list(construct(store, bind(text, **tokens), graphs))
    except Exception as exc:                                        # noqa: BLE001
        #  A rule that will not run is a package's bug and must not take an agent down: the
        #  lever still works, and what is lost is the ability to reason about it in advance.
        log.error("effect rule for this action would not run: %s", exc)
        return []


def _binding(store, cand: str, me: str, memo) -> dict:
    """The `$tokens` a candidate's rule texts take: which world (`$state`, the one it is
    taken in), who is asking (`$me`), whom for (`$subject`), when (`$now`, that world's
    instant) and what it is filled with, one token per parameter under the parameter's
    local part — one spelling serving three places (an-action-takes-parameters). With
    `action`, which the texts are read off, and `from`, for the caller asking about that world.

    ONE QUERY, remembered for the pass, since the act reads it four times for one candidate.
    """
    def fetch():
        cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
        found = rows(store, _CANDIDATE_Q, (), cand=cand, cat=cat)
        if not found:
            raise LookupError(f"no candidate {cand} — was it admitted?")
        subject = remember(memo, ("acts_for", me), lambda: next(
            (r["for"] for r in rows(store, _ACTS_FOR_Q, graphs_of(store, PUBLIC), me=me)), None))
        out = {"state": Raw(f"<{found[0]['from']}>"), "me": me, "subject": subject or "urn:nobody",
               "now": instant(datetime.fromisoformat(found[0]["at"])),
               "action": found[0]["action"], "from": found[0]["from"],
               "at": found[0]["at"], "spent": float(found[0]["spent"])}
        for r in found:
            if r.get("p"):
                out[local_of(r["p"])] = r["v"]
        return out
    return remember(memo, ("binding", cand), fetch)


def _rule(store, action: str, memo) -> dict | None:
    """The effect rule an action carries, or None for an action an event adopts.

    None is the answer for an action that states neither text — the market's Presenting,
    adopted by an event and admitted by no world — and for nothing else: an action with a
    precondition states an effect, or the gate (`deliberable`, in `onboarding/validate.py`)
    refuses the world before an agent runs (#506).

    REMEMBERED FOR THE PASS (#552): the text is public knowledge and only a write can
    change it, yet it was fetched on every fork by three callers each.
    """
    def fetch():
        found = bindings(query(store, _RULE_Q, graphs_of(store, ACTION), {"rule": action}))
        return found[0] if found else None
    return remember(memo, ("rule", action), fetch)


def _figure(store, cand: str, me: str, memo, text: str, column: str) -> float | None:
    """One of a rule's SELECTs that answers with a number — `costs`, what taking the act would
    spend in the wallet's unit (#466), or `lands`, how long until the world change completes,
    in seconds (#238): asked, never computed, so the figure a planner plans against and the
    figure a waiter waits for are one figure. None where the rule declines — no text, or
    premises that do not hold — which every caller reads as free, or as landing at once.

    One of a rule's SELECTs that answers with a number, asked over the world the candidate
    is taken in — through the rules' own door, so it sees exactly what the CONSTRUCT sees
    (#472). A rule that will not run is a package's bug and must not take an agent down."""
    binding = _binding(store, cand, me, memo)
    rule = _rule(store, binding["action"], memo)
    if rule is None or not rule.get(text):
        return None
    tokens = {k: v for k, v in binding.items() if k not in ("action", "from", "at", "spent")}
    try:
        found = construct(store, bind(rule[text], **tokens),
                          world_at(store, binding["from"], memo=memo))
    except Exception as exc:                                        # noqa: BLE001
        log.error("%s query for this action would not run: %s", text, exc)
        return None
    if not found or found[0][column] is None:
        return None
    return float(found[0][column].value)
