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

**THE CHILD IS FORKED FROM THE GROUND HOLDING AT ITS LANDING** (#596). The grounds are the
present with each prediction applied in turn, one per period; a step whose landing falls in a
later period than the world it is taken in would, forked from that world, be judged against the
present's readings plus the plan's diffs, with what the predictions say holds by then unseen — a
pot drying while the plan runs. So where the ground at the child's earliest landing is not the one
its parent stands in, the child is a copy of THAT ground with every step on the path replayed onto
it in order, each with its own filling, and then this step's effect; a step whose effect changes
nothing there is not a move, exactly as in its parent. The predictions keep a reading's node and
replace its value, so a filling naming the reading finds it in every ground. Where the landing
stays inside the parent's period — hanoi, the courier, a dose landing within a cadence — nothing
is replayed and the child is forked from its parent, as it always was.

**AND WHAT THE EFFECT CHANGED IS SAID BEFORE THE REPLAYED GROUND GOES** (#919). Such a child differs
from its parent by the step's effect AND by everything the predictions moved between the two
periods; the step's prediction is the first alone, so the child against the replayed ground, each
way, is written into `<child>.adds` and `<child>.retracts`, derived from the child, and
`extract_plan` copies those where it would otherwise diff the child against its parent. A child
forked from its parent needs nothing written: the two differ by the effect and nothing else.

AN EFFECT IS RULES, GROUPED BY ORDER. An action's `planning:effect` holds `sh:rule`s, each a
`sh:SPARQLRule` whose `sh:construct` yields what applying it ADDS, or whose `planning:update` is a
`DELETE … WHERE` taking away whatever stands in the place the step changes, which nobody can name
in advance. Every rule of one `sh:order` reads the same world — the construct is asked, and the
delete's WHERE matched, before any of that order is applied — its deletions go first and its
additions after, and a later order reads the world the earlier ones made. A delete names no
graph: it is run `WITH` the new world and `USING` every graph of it (`store.scoped`). What
SHACL runs over beliefs only ever concludes; this runs over a possible world, where taking
something away is the point.

**The vocabulary is SHACL's; the engine is not.** pySHACL will execute `sh:SPARQLRule`, but
only as forward-chaining inference to a fixpoint; a plan step is one rule against one
hypothesis, the opposite shape. A stored `sh:construct` is just a query, and this project has
an engine that runs queries. See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md.

THE CHILD IS NAMED BY THE CANDIDATE'S MINT NUMBER, read off the candidate's row and never off
its name (#486): `admit` minted the candidate `possible/<n>.by` with `planning:minted n`, and
the world it makes is `possible/<n>` carrying the same number, so the edge and the world at
its end are one spelling apart, for eyes, and one number on the rows. A name is for eyes:
every reader asks `planning:by` and `planning:from`, and the frontier's tie-break asks
`planning:minted`. The path that reaches a world is the rows, never its spelling, so a name
is the same length at depth eight as at depth one.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from agent.execution.ontology import ADDS_GRAPH, RETRACTS_GRAPH
from agent.hash_named_graph import digest_of
from agent.ontology import ACTION, PUBLIC, local_of
import pyoxigraph as ox

from agent.store import (Raw, add_quads, bind, bindings, catalogue_of, clear_graph, closed, construct, fork,
                                graphs_of, instant, query, remember, render, rows, scoped, update)

from .admit import POSSIBLE
from .ontology import GROUND_GRAPH, POSSIBLE_GRAPH
from .world_at import world_at

#  THE CATALOGUE IS BOUND, NOT FOUND, IN THE HOT READS: `GRAPH ?cat { ?cat a
#  orexis:CatalogueGraph . … }` makes the engine evaluate the group per named graph, and with
#  a store of sixteen possible worlds each such read cost 0.5 to 1.0 ms where a read over one
#  bound graph costs 0.1 to 0.2 — measured on the two-disk bench. The name is asked of the
#  store once per pass (`catalogue_of`, remembered) and spliced as `$cat`: a reader asking
#  the store for the catalogue's name is what the rule allows; spelling it is what it refuses.

log = logging.getLogger("take")

#  THE ACTION'S TEXTS, read off public knowledge like everything else. `?rule` is bound by
#  SUBSTITUTION (#500), the engine's own parameter, projected. `STR(?takes)` because
#  GROUP_CONCAT over an IRI binds nothing in this engine.
_RULE_Q = """
SELECT ?rule ?lands ?costs (GROUP_CONCAT(DISTINCT STR(?p); separator=" ") AS ?takes) WHERE {
  ?rule a orexis:Action .
  OPTIONAL { ?rule orexis:takes ?p }
  OPTIONAL { ?rule planning:landsAfter ?lands }
  OPTIONAL { ?rule planning:costs ?costs }
} GROUP BY ?rule ?lands ?costs LIMIT 1"""

#  ITS EFFECT'S RULES, by order — an absent order is 0, as SHACL says. `?rule` projected, since
#  the engine substitutes only a variable the query projects.
_EFFECT_Q = """
SELECT ?rule ?order ?construct ?update WHERE {
  ?rule planning:effect/sh:rule ?r .
  OPTIONAL { ?r sh:order ?o } OPTIONAL { ?r sh:construct ?construct } OPTIONAL { ?r planning:update ?update }
  BIND(COALESCE(?o, 0) AS ?order) }
ORDER BY ?order"""

#  THE CANDIDATE'S ROW: the world it is taken in, when that world is — the start of its period
#  and, for a possible world, its end; a ground's end is when it stops holding, which is not when
#  the search stands, so a ground is a point — the action it fills, its mint number, which names
#  the world it makes, and every parameter it is filled with — the parameter's IRI and the
#  value, one row each. A candidate stating no mint number was admitted by nobody, and is refused.
_CANDIDATE_Q = """
SELECT ?from ?start ?end ?spent ?action ?minted ?p ?v WHERE {
  GRAPH $cat { $cand planning:from ?from ; planning:fills ?action ; planning:minted ?minted .
    ?from dcterms:temporal ?period . ?period orexis:start ?start .
    OPTIONAL { ?from a planning:PossibleGraph . ?period orexis:end ?e }
    OPTIONAL { ?from planning:spent ?s }
    OPTIONAL { $cand ?p ?v . FILTER(?p NOT IN (planning:from, planning:fills, planning:minted, rdf:type)) } }
  BIND(COALESCE(?e, ?start) AS ?end) BIND(COALESCE(?s, 0.0) AS ?spent) }"""

#  WHOM THE AGENT ACTS FOR, off the world graph — `$subject` in a rule text.
_ACTS_FOR_Q = """SELECT ?for WHERE { $me orexis:actsFor ?for } LIMIT 1"""


#  THE PATH TO A WORLD: every candidate taken from the ground down to the world itself, in the
#  order the worlds were minted, which is the order the steps are taken in.
_PATH_Q = """
SELECT ?c WHERE { GRAPH $cat { $world (planning:by/planning:from)* ?w . ?w planning:by ?c ; planning:minted ?m } }
ORDER BY ?m"""

#  A WORLD'S OWN ROW: every kind the vocabulary puts a possible graph beneath, how it arrived,
#  what it holds by hash, what reaching it spent, when it is — the period from the earliest to
#  the latest the path's landings reach it, as a ground says when it holds — its mint number,
#  the candidate's, and the candidate that made it.
_WORLD_U = """
INSERT { GRAPH ?cat { $world a $kinds ; orexis:arrivedBy orexis:Derived ; orexis:hash $hash ;
                      planning:spent $spent ; planning:minted $minted ; planning:by $cand ;
                      dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start $start ; orexis:end $end ] } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"""

#  WHAT THE EFFECT CHANGED, IN THE WORLD IT WAS APPLIED TO, where that world is not the one the
#  candidate was taken in and is about to go (#919): the child against the ground at its landing
#  with the path replayed, `$base`, each way, into two graphs the child's row cannot hold and
#  whose rows say they were derived from it — the kinds a step's prediction is, since that is what
#  `extract_plan` makes of them. The diff is the engine's, as the step's own is.
_CHANGED_U = """
INSERT { GRAPH $adds { ?s ?p ?o } } WHERE { GRAPH $world { ?s ?p ?o } FILTER NOT EXISTS { GRAPH $base { ?s ?p ?o } } } ;
INSERT { GRAPH $retracts { ?s ?p ?o } } WHERE { GRAPH $base { ?s ?p ?o } FILTER NOT EXISTS { GRAPH $world { ?s ?p ?o } } } ;
INSERT { GRAPH ?cat { $adds a $addskinds ; orexis:arrivedBy orexis:Derived ; prov:wasDerivedFrom $world .
                      $retracts a $retractskinds ; orexis:arrivedBy orexis:Derived ; prov:wasDerivedFrom $world } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"""



def take(store, cand: str, me: str, *, memo=None, within: frozenset | None = None) -> bool:
    """Fork the world `cand` reaches and write its row. False, and nothing made, where the
    candidate's effect changes nothing in the world it leaves. `within` is what a world of this
    imaginarium is identified by, and the child is hashed within it as `lay_ground` hashed its
    ground — or the two never match.

    WHAT THE STEP COSTS AND HOW LONG IT TAKES TO LAND are asked of the world it is taken IN,
    before anything is applied — a cost read off the state it is about to change would answer
    about the change. The child's period is the parent's moved by the landing's band — its start
    by the least, its end by the most — written and not derived, because this engine binds
    nothing for duration arithmetic; a landing declared as nothing is nought twice.
    """
    binding = _binding(store, cand, me, memo)
    minted = binding["minted"]
    child = f"{POSSIBLE}{minted}"
    cost = _figure(store, cand, me, memo, "costs", "cost") or 0.0
    least, most = _landing(store, cand, me, memo)
    start = datetime.fromisoformat(binding["start"]) + timedelta(seconds=least)
    end = datetime.fromisoformat(binding["end"]) + timedelta(seconds=most)
    #  THE GROUND THE CHILD LANDS IN, against the one its parent stands in: the same, and the child
    #  is forked from its parent; a later one, and it is forked from that ground with the path
    #  replayed, since what holds there is what the step's effect changes.
    lands_in = _ground_at(store, start, memo)
    stands_in = binding["from"] if binding["from"] in _grounds(store, memo) else \
        _ground_at(store, datetime.fromisoformat(binding["start"]), memo)
    if lands_in is None or lands_in == stands_in:
        made = _apply(store, cand, child, me, memo)
    else:
        base = _replayed(store, cand, child, lands_in, me, memo)
        made = _apply(store, cand, child, me, memo, base=base,
                      graphs=[base if g == lands_in else g for g in world_at(store, lands_in, memo=memo)])
        if made:
            _changed(store, child, base, memo)
        clear_graph(store, base)
    if not made:
        return False
    #  EVERY KIND A POSSIBLE GRAPH IS BENEATH, once per pass: the closure is materialised at
    #  genesis, so one `rdfs:subClassOf` step is every step, and a row written with them all
    #  is what lets a reader ask `?g a orexis:WorkingGraph` and walk no path.
    kinds = remember(memo, ("closed", POSSIBLE_GRAPH), lambda: closed(store, POSSIBLE_GRAPH))
    #  THE MINT NUMBER IS THE CANDIDATE'S: `admit` drew it from the store's counter when it wrote
    #  the row, and the world carries it on, so nothing here counts.
    update(store, bind(_WORLD_U, world=child, cand=cand,
                       kinds=Raw(" , ".join(f"<{k}>" for k in kinds)),
                       hash=Raw(f'"{digest_of(store, child, within)}"'),
                       spent=binding["spent"] + cost, start=instant(start), end=instant(end), minted=minted))
    return True


def _apply(store, cand: str, into: str, me: str, memo, *, base: str | None = None, graphs=None) -> bool:
    """Make `into` out of `base` — the world `cand` is taken in, unless the caller hands the ground
    at its landing with the path replayed — with the action's effect applied, order by order,
    reading `graphs`, the world's at its instant. False, and no graph made, where the effect says
    NOTHING about this world — no rule stated, or every rule coming to nothing — which is not a
    move.

    THE FORK IS MADE AT THE FIRST ORDER THAT CHANGES SOMETHING: until then a construct is asked
    of the world the candidate leaves, which is the world it would read anyway, so a candidate
    changing nothing costs no copy. A delete is taken as a change, since what it matches is not
    known until it runs."""
    binding = _binding(store, cand, me, memo)
    rule = _rule(store, binding["action"], memo)
    if rule is None:
        return False
    source = base or binding["from"]
    leaves = graphs if graphs is not None else world_at(store, binding["from"], memo=memo)
    tokens = _tokens(binding)
    forked = False
    for order in sorted({r["order"] for r in rule["rules"]}):
        rules = [r for r in rule["rules"] if r["order"] == order]
        scope = [into if g == source else g for g in leaves]
        added = [t for r in rules for t in _run(store, r.get("construct"), tokens, scope if forked else leaves)]
        texts = [r["update"] for r in rules if r.get("update")]
        if not forked and not added and not texts:
            continue
        deletes = [d for d in (_delete(text, into, tokens, scope) for text in texts) if d is not None]
        if not forked:
            fork(store, source, into, added, deletes)
            forked = True
            continue
        _change(store, into, added, deletes)
    return forked


def _replayed(store, cand: str, child: str, ground: str, me: str, memo) -> str:
    """A copy of `ground` with every step on the path to `cand`'s world applied onto it in order,
    each with its own filling — the world the step `cand` is taken in, as it stands in the ground
    the step lands in. Named `<child>.base`, and the caller's to clear once the child is forked
    from it. Measured on the two-tank plans case: a replayed fork costs two copies of a ground
    where a plain fork costs one, and nothing is replayed where the landing stays in the parent's
    period, which is every shipped world's today."""
    binding = _binding(store, cand, me, memo)
    base = f"{child}.base"
    clear_graph(store, base)
    fork(store, ground, base, [], [])
    graphs = [base if g == ground else g for g in world_at(store, ground, memo=memo)]
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    path = [r["c"] for r in rows(store, _PATH_Q, (), world=binding["from"], cat=cat)]
    for step in path:
        taken = _binding(store, step, me, memo)
        rule = _rule(store, taken["action"], memo)
        if rule is None:
            continue
        tokens = _tokens(taken)
        for order in sorted({r["order"] for r in rule["rules"]}):
            rules = [r for r in rule["rules"] if r["order"] == order]
            added = [t for r in rules for t in _run(store, r.get("construct"), tokens, graphs)]
            texts = [r["update"] for r in rules if r.get("update")]
            deletes = [d for d in (_delete(text, base, tokens, graphs) for text in texts) if d is not None]
            _change(store, base, added, deletes)
    log.debug("%s lands in %s: %d step(s) replayed there", local_of(child), ground.rsplit("/", 1)[-1], len(path))
    return base


def _changed(store, world: str, base: str, memo) -> None:
    """Say what the effect changed in `base`, the world `world` was forked from, as two graphs
    derived from `world` — `<world>.adds` and `<world>.retracts` — before `base` is cleared.

    ONLY WHERE THE CHILD WAS REPLAYED. Forked from its parent, a world differs from the world its
    candidate was taken in by the effect and nothing else, so that diff IS the effect's change and
    `extract_plan` takes it there. Forked from a later ground, it differs also by everything the
    predictions moved between the two periods — another van's next cell, the drain of a tank — and
    the one graph that told the two apart, the base, is gone by the time a plan is read. Written
    for every fork it would cost two diffs and four rows on every candidate taken, to say what the
    parent already says."""
    adds = remember(memo, ("closed", ADDS_GRAPH), lambda: closed(store, ADDS_GRAPH))
    retracts = remember(memo, ("closed", RETRACTS_GRAPH), lambda: closed(store, RETRACTS_GRAPH))
    update(store, bind(_CHANGED_U, world=world, base=base, adds=f"{world}.adds", retracts=f"{world}.retracts",
                       addskinds=Raw(" , ".join(f"<{k}>" for k in adds)),
                       retractskinds=Raw(" , ".join(f"<{k}>" for k in retracts))))


def _change(store, into: str, added, deletes) -> None:
    """One order of an effect applied in place: its deletions first, its additions after."""
    for text in deletes:
        try:
            update(store, text)
        except Exception as exc:                                    # noqa: BLE001
            log.error("an effect's delete would not run, so it deletes nothing: %s", exc)
    add_quads(store, (ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(into)) for t in added))


def _tokens(binding: dict) -> dict:
    """The `$tokens` a rule text takes, off a candidate's binding: everything but what the caller
    reads of the row."""
    return {k: v for k, v in binding.items() if k not in ("action", "from", "minted", "start", "end", "spent")}


def _grounds(store, memo) -> frozenset:
    """Every ground laid in the store, once per pass."""
    return remember(memo, ("grounds",), lambda: frozenset(graphs_of(store, GROUND_GRAPH)))


def _ground_at(store, at: datetime, memo) -> str | None:
    """The ground holding at `at`, or None before the first — remembered per instant, since every
    fork of a world landing at nought asks about the same one."""
    return remember(memo, ("ground_at", at), lambda: next(iter(graphs_of(store, GROUND_GRAPH, at=at)), None))


def _delete(text: str, into: str, tokens: dict, graphs) -> str | None:
    """One `planning:update` rule, bound and scoped to the world it deletes from — or None, said in
    the log, where it will not bind or names graphs of its own.

    It is not optional where a node is replaced: the sensed graph upserts one observation node
    per (subject, property), so an effect predicting a reading that did not delete the side it
    replaces would leave two on one node."""
    try:
        return scoped(bind(text, **tokens), into, graphs)
    except Exception as exc:                                        # noqa: BLE001
        log.error("an effect's delete would not bind, so it deletes nothing: %s", exc)
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
    taken in), who is asking (`$me`), whom for (`$subject`), when (`$now`, the start of that
    world's period) and what it is filled with, one token per parameter under the parameter's
    local part — one spelling serving three places (an-action-takes-parameters). With
    `action`, which the texts are read off, `from`, for the caller asking about that world,
    `minted`, the number that names the child, and the world's `start` and `end`, which the
    child's period is moved from — none of which is a token.

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
               "now": instant(datetime.fromisoformat(found[0]["start"])),
               "action": found[0]["action"], "from": found[0]["from"], "minted": int(found[0]["minted"]),
               "start": found[0]["start"], "end": found[0]["end"], "spent": float(found[0]["spent"])}
        for r in found:
            if r.get("p"):
                out[local_of(r["p"])] = r["v"]
        return out
    return remember(memo, ("binding", cand), fetch)


def _rule(store, action: str, memo) -> dict | None:
    """What an action carries for a search: its texts, and its effect's rules in order — or None
    for an action that states no effect, which no world is made by.

    REMEMBERED FOR THE PASS (#552): the text is public knowledge and only a write can
    change it, yet it was fetched on every fork by three callers each.
    """
    def fetch():
        found = bindings(query(store, _RULE_Q, graphs_of(store, ACTION), {"rule": action}))
        rules = [{"order": float(r["order"]), "construct": r.get("construct"), "update": r.get("update")}
                 for r in bindings(query(store, _EFFECT_Q, graphs_of(store, ACTION), {"rule": action}))]
        return {**found[0], "rules": rules} if found and rules else None
    return remember(memo, ("rule", action), fetch)


def _landing(store, cand: str, me: str, memo) -> tuple[float, float]:
    """How long after the act the world change can show, as the band the action's `landsAfter`
    answers — `?least` and `?most`, in seconds — asked over the world the candidate is taken in.
    Nought twice where the action declares none or the text declines, which is a step the world
    shows the instant it is taken; a text binding only one of the two, or an older `?seconds`,
    is a package's bug, said in the log and read as nought."""
    row = _answer(store, cand, me, memo, "lands")
    if row is None:
        return 0.0, 0.0
    least, most = _bound(row, "least"), _bound(row, "most")
    if least is None or most is None:
        log.error("the landing of this action binds no ?least and ?most, so it lands at once")
        return 0.0, 0.0
    return min(least, most), max(least, most)


def _figure(store, cand: str, me: str, memo, text: str, column: str) -> float | None:
    """One of a rule's SELECTs that answers with a number — `costs`, what taking the act would
    spend in the wallet's unit (#466) — asked, never computed, so the figure a planner plans
    against is the package's own. None where the rule declines — no text, or premises that do
    not hold — which the caller reads as free."""
    row = _answer(store, cand, me, memo, text)
    return None if row is None else _bound(row, column)


def _bound(row, column: str) -> float | None:
    """What a solution binds `column` to, as a number — None where it binds nothing, or a variable
    the text does not project."""
    try:
        term = row[column]
    except (KeyError, IndexError, ValueError):
        return None
    return None if term is None else float(term.value)


def _answer(store, cand: str, me: str, memo, text: str):
    """The first row of one of the action's SELECTs — `costs`, `lands` — asked over the world the
    candidate is taken in, through the rules' own door, so it sees exactly what the CONSTRUCT
    sees (#472); None where the action states no such text, the text yields no row, or it will
    not run, which is a package's bug and must not take an agent down."""
    binding = _binding(store, cand, me, memo)
    rule = _rule(store, binding["action"], memo)
    if rule is None or not rule.get(text):
        return None
    tokens = _tokens(binding)
    try:
        found = construct(store, bind(rule[text], **tokens),
                          world_at(store, binding["from"], memo=memo))
    except Exception as exc:                                        # noqa: BLE001
        log.error("%s query for this action would not run: %s", text, exc)
        return None
    return found[0] if found else None
