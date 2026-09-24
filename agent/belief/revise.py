"""`revise`: what the rules the store holds conclude of one graph — its revisions — written
beside it, within a budget.

**THE RULES ARE SHACL 1.2 INFERENCE RULES', RUN AS THE DRAFT SAYS.** Every graph the catalogue
types `sh:RulesGraph` is a rules graph, and what is run is its DEFAULT RULE SET: every rule in
it that is a `sh:SPARQLRule` with a `sh:construct`, global — not linked to a shape by `sh:rule`,
since a shape rule runs per focus node and nothing here has one — and not `sh:deactivated`. A
package's `sh:RuleSet` with `sh:hasRule` and `sh:includesRuleSet` is how it ships them, and the
default rule set is what a reader of the graph gets without being told which set to run.

**LAYER BY LAYER, TO A FIXPOINT, OVER THE EVALUATION GRAPH — SECTION 8 OF THE DRAFT.** The
evaluation graph is what the caller hands as standing beside the source, the source itself,
and what has been concluded of it so far. Within a layer (`sh:layer`, ascending, 0 unless
said) one iteration runs every `sh:runOnce` rule FIRST, then the iterating rules are run
again while an iteration concludes something new; within an iteration the rules run in order
(`sh:order`, ascending, 0 unless said), and rules of ONE order are run over the same state and
see none of each other's inferences until they have all run — the draft's "executed
concurrently". What is inferred is what is NOT in the base graph: a rule restating a fact the
evaluation graph already holds infers nothing. A rule of a type this engine cannot execute —
a `sh:TripleRule`, or a shape rule, which runs per focus node and has none here — is the
failure the draft says to report, and here that is an error in the log naming the rule, once
per pass, since a package's bug must not take an agent down; a construct that will not run is
reported the same way and the rest of the rule set runs, where the draft would fail it whole.
Expected derived triples (`sh:expectedPredicate`) and temporary triples are not supported.

**A CEILING ON COMPUTE IS STATED IN THE UNIT THE WORK SPENDS**, and what revision spends is
rule executions: one construct run. `budget` is this call's, and it replaces a cap on
iterations the module used to choose for itself. A group of one order is run whole or not at
all; when the budget is spent before a layer settles, what was concluded stands, the revision
graph's row says `belief:settled false`, and the next call CONTINUES from what is held rather
than starting over — a run-once rule runs again in that call's first iteration, and what it
concludes twice is written once. So a rule set that mints fresh content every iteration, the
draft's own worry and the reason `sh:runOnce` exists, spends a budget and stops, and is said
in the log every pass instead of looping. The answer is what this call spent.

**A RULE CONCLUDES AND NEVER DELETES.** What comes out is written into the source's own revision
graph, the draft's inference graph, and never into the source. Nothing is retracted: what
replaces a conclusion is its source being rewritten, and a source not marked unsettled begins
by forgetting what was concluded of it before.

**A FACT ALREADY CONCLUDED IS NOT WRITTEN TWICE, AND A BLANK NODE IS ITS CONTENT.** A construct
whose template mints a blank node mints a fresh one every run, so by label every iteration would
conclude something new and no fixpoint would come; by content (`hash_named_graph.forms`, the
same reading the world's hash takes) the second iteration's node says what the first's said and
is not written.

**THE CALLER SAYS WHAT STANDS BESIDE THE SOURCE** (`read`), as every reader here states the
kinds it reads. The texts are unqualified patterns over that union — a rule does not say which
world it reads (#666) — and take no `$tokens`: a rule is about the world and not about who
holds it. Rules run on the PRESENT only, a reading when it is written and a prediction when it
is predicted, never in a search: planning speaks the derived vocabulary and an effect writes its
conclusion itself.

**CONCLUDE, THEN CLASSIFY.** A graph with no catalogue row is invisible to every reader by
kind, so a writer that means its graph never to be seen without its revisions writes the graph,
calls this, and classifies it last; the revision graph's row copies the source's owner and
period where the source's row already states them, and says derived-from either way.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.hash_named_graph import forms
from agent.ontology import OREXIS
from agent.store import (Raw, catalogue_of, construct, entry, forget_graph, graphs_of, quads,
                         remember, rows, update)

from .ontology import DERIVED_FROM, REVISION_GRAPH, RULES_GRAPH, SETTLED, revision_graph

log = logging.getLogger("revise")

#  RULE EXECUTIONS one call may spend, unless the caller says otherwise.
BUDGET = 64

#  THE DEFAULT RULE SET of every rules graph: every active rule of any kind — `sh:SPARQLRule`
#  or another type beneath `sh:Rule` — with where the draft places it, its construct where it
#  has one, and whether a shape links it, so that what cannot be run is reported rather than
#  passed over. Read by kind, as every reader here states the kinds it reads.
_RULES_Q = """
SELECT ?rule ?type ?construct ?layer ?order ?once ?shape WHERE {
  ?rule a ?type . FILTER(?type IN (sh:SPARQLRule, sh:TripleRule, sh:Rule))
  OPTIONAL { ?rule sh:construct ?construct }
  OPTIONAL { ?rule sh:layer ?layer } OPTIONAL { ?rule sh:order ?order }
  OPTIONAL { ?rule sh:runOnce ?once }
  OPTIONAL { ?shape sh:rule ?rule }
  FILTER NOT EXISTS { ?rule sh:deactivated true } }"""

#  WHOSE THE SOURCE IS AND WHEN IT HOLDS, off its row: the revisions are the same.
_SOURCE_Q = """
SELECT ?owner ?start ?end WHERE {
  GRAPH $cat { OPTIONAL { $source orexis:beliefsOf ?owner }
               OPTIONAL { $source dcterms:temporal ?p .
                          OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } }
LIMIT 1"""

#  WHETHER A REVISION GRAPH'S RULES SETTLED, off its row; no row is settled, since a source
#  never revised has nothing to continue.
_SETTLED_Q = """ASK { GRAPH $cat { $graph $settled false } }"""


def revise(store, source: str, *, read=(), budget: int = BUDGET, memo=None) -> int:
    """Conclude what the rules the store holds say follows from `source` beside `read` — the
    source's revisions — into its revision graph, layer by layer towards a fixpoint, spending
    at most `budget` rule executions. What this call spent.

    A source whose row says its rules did not settle is CONTINUED from what is held; any
    other has what was concluded of it before forgotten first. Where nothing is concluded
    and the rules settled there is no graph and no row.
    """
    into = revision_graph(source)
    cat = Raw(f"<{catalogue_of(store)}>")
    continuing = bool(store.query(_bind_settled(cat, into), prefixes=_NAMESPACES))
    held: list[ox.Triple] = []
    if continuing:
        held = [ox.Triple(q.subject, q.predicate, q.object) for q in quads(store, into)]
    else:
        forget_graph(store, into)
    layers = remember(memo, ("rules",), lambda: _layers(store))
    if not layers:
        return 0
    evaluation = list(dict.fromkeys([*read, source, into]))
    base = [ox.NamedNode(g) for g in evaluation if g != into]
    spent = 0
    settled = True
    for layer, orders in layers:
        #  ONE ITERATION OVER THE RUN-ONCE RULES FIRST, then the iterating rules while new.
        once = [(order, [r for r in rules if r["once"]]) for order, rules in orders]
        iterating = [(order, [r for r in rules if not r["once"]]) for order, rules in orders]
        rounds = [once]
        while rounds:
            groups = rounds.pop(0)
            concluded = 0
            for _, due in groups:
                if not due:
                    continue
                if spent >= budget:
                    settled = False
                    break
                #  ONE ORDER, ONE STATE: every rule of the order is asked before any of their
                #  conclusions is written, so none sees another's.
                added = []
                for rule in due:
                    spent += 1
                    try:
                        added += construct(store, rule["construct"], evaluation)
                    except Exception as exc:                            # noqa: BLE001
                        #  A rule that will not run is a package's bug and must not take an
                        #  agent down: the others conclude, and the log says which did not.
                        log.error("rule %s would not run over %s: %s", rule["rule"], source, exc)
                fresh = _novel(held, _inferred(store, added, base))
                if fresh:
                    store.extend(ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(into)) for t in fresh)
                    held.extend(fresh)
                    concluded += len(fresh)
            if not settled:
                break
            if groups is once or concluded:
                rounds.append(iterating)
        if not settled:
            log.warning("the rules over %s did not settle within %d execution(s) at layer %s; "
                        "what they concluded stands, and the next pass continues", source, budget, layer)
            break
    if not held:
        return spent
    _describe(store, source, into, settled, continuing)
    log.debug("%d revision(s) of %s after %d execution(s)%s", len(held), source, spent,
              "" if settled else ", not settled")
    return spent


def _novel(held: list, added: list) -> list:
    """The triples of `added` that say something `held` does not — by canonical form, in the
    universe of both, so a blank node minted again with the content of one already held is
    the same fact and a second solution of one construct minting the same content is too."""
    if not added:
        return []
    shapes = forms([*held, *added])
    seen = set(shapes[:len(held)])
    out = []
    for triple, form in zip(added, shapes[len(held):]):
        if form in seen:
            continue
        seen.add(form)
        out.append(triple)
    return out


def _inferred(store, added: list, base: list) -> list:
    """The triples of `added` the base graph does not already hold — what the draft calls
    inferred: a rule restating a fact of the evaluation graph infers nothing."""
    return [t for t in added if not any(
        next(iter(store.quads_for_pattern(t.subject, t.predicate, t.object, g)), None) is not None
        for g in base)]


def _layers(store) -> list[tuple[float, list[tuple[float, list[dict]]]]]:
    """The default rule set of every rules graph, as the draft executes it: layers ascending,
    and within a layer the rules grouped by order ascending — `[(layer, [(order, rules)])]`,
    each rule a dict with its construct and whether it runs once. A rule this engine cannot
    execute — not a SPARQL rule, or linked to a shape — is the failure the draft says to
    report, logged once per pass and left out."""
    found = []
    seen: dict = {}
    for r in rows(store, _RULES_Q, graphs_of(store, RULES_GRAPH)):
        entry_ = seen.setdefault(r["rule"], {"types": set(), "shape": None, "row": r})
        entry_["types"].add(r["type"])
        entry_["shape"] = entry_["shape"] or r.get("shape")
    for rule, about in sorted(seen.items()):
        r = about["row"]
        if about["shape"]:
            log.error("rule %s is a shape rule of %s, which this engine cannot execute: it runs per "
                      "focus node and nothing here has one", rule, about["shape"])
            continue
        if "http://www.w3.org/ns/shacl#SPARQLRule" not in about["types"] or not r.get("construct"):
            log.error("rule %s is of a type this engine cannot execute (%s)", rule,
                      ", ".join(sorted(t.rsplit("#", 1)[-1] for t in about["types"])))
            continue
        found.append({"rule": rule, "construct": r["construct"],
                      "layer": float(r.get("layer") or 0), "order": float(r.get("order") or 0),
                      "once": (r.get("once") or "").lower() == "true"})
    found.sort(key=lambda r: (r["layer"], r["order"], r["rule"]))
    layers: dict = {}
    for r in found:
        layers.setdefault(r["layer"], {}).setdefault(r["order"], []).append(r)
    return [(layer, sorted(orders.items())) for layer, orders in sorted(layers.items())]


def _describe(store, source: str, into: str, settled: bool, continuing: bool) -> None:
    """The revision graph's row: derived, from `source`, the source's owner's, for the
    source's period, and whether its rules settled — the flag replaced where the row stands."""
    cat = Raw(f"<{catalogue_of(store)}>")
    flag = "true" if settled else "false"
    if continuing:
        update(store, f"""
DELETE {{ GRAPH {cat} {{ <{into}> <{SETTLED}> ?was }} }}
INSERT {{ GRAPH {cat} {{ <{into}> <{SETTLED}> {flag} }} }}
WHERE  {{ GRAPH {cat} {{ <{into}> <{SETTLED}> ?was }} }}""")
        return
    row = next(iter(rows(store, _SOURCE_Q, (), cat=cat, source=source)), {})
    update(store, f"""
INSERT DATA {{
  {entry(store, into, REVISION_GRAPH, OREXIS + "Derived", row.get("owner"), row.get("start"), row.get("end"))}
  GRAPH {cat} {{ <{into}> <{DERIVED_FROM}> <{source}> ; <{SETTLED}> {flag} . }} }}""")


from agent.store import NAMESPACES as _NAMESPACES, bind as _bind  # noqa: E402


def _bind_settled(cat: Raw, graph: str) -> str:
    return _bind(_SETTLED_Q, cat=cat, graph=graph, settled=SETTLED)
