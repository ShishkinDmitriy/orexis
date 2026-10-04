"""`refine`: a step's predicted facts, handed one level down as a want — where a rule the store
holds concludes them from other facts.

**THE HIERARCHY IS NEVER DECLARED; IT IS FOUND IN THE RULES.** A step predicts facts in its own
level's words — a hanoi Move, that a disk is on another. Where a rule of a `sh:RulesGraph`
concludes that predicate from facts of another vocabulary — a disk is on what it stands on, by
where the disks stand on the courier's grid — the step is not the level's to take: it is kept
below. So the rule is run BACKWARDS: its head is bound to the predicted fact, and its WHERE, with
those bindings, is the goal the level beneath must reach. That goal becomes a WANT, the agent's
own, whose met-test is exactly that WHERE, and it is planned like any other want, in the scope
its words fall in. Nothing is translated back: when the level beneath gets there, the rule
concludes the step's fact from the present and the executor answers the step from that revision.

This is goal regression through derived predicates, and the whole is Hierarchical Planning in
the Now's shape (Kaelbling and Lozano-Pérez, 2011), with the hierarchy found in the rules a
world combines rather than written into the actions (knowledge/domain/planning/refinement.md).

**A RULE THAT CANNOT RUN BACKWARDS IS NOT A BRIDGE.** Its head must be one triple whose subject
and object are constants or variables its WHERE binds plainly; anything else — a head of two
triples, a `BIND` into a head variable — is left out and said in the log, so a step it would
have concluded is taken as it would be with no rule at all.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import GRAPH_PREFIX, OREXIS, STATE, local_of
from agent.store import classify, graphs_of, instant, quads_for_pattern, revisions_of, rows, update

from .bridge import binding, expand, literal, heads, predicted
from .ontology import PLANNING, WANT

log = logging.getLogger("refine")

def refine(store: ox.Store, me: str, step: str, now: datetime) -> str | None:
    """Mint the want that keeps the step `step` below, from the facts it predicts its world gains
    and loses — read off the two graphs the step names, as the terms they are — in the agent
    `me`'s own want graph; the want. None where no rule the store holds concludes any fact it
    adds, which is the answer for every step of a level with nothing beneath it.

    THE GOAL IS THE WORLD THE STEP LANDS IN, NOT ITS DIFF. Every fact of a concluded predicate
    the present holds, less what the step retracts, plus what it adds — each regressed, and all
    of them to hold at once. The diff alone was measured to be too little: `disk_1 on disk_2`
    was reached below by carrying disk_2 over to disk_1, off the peg the upper plan had put it
    on, and the plan above walked on over a world it had not predicted. What the level above
    assumed of the facts a step leaves alone is what its later steps stand on, so the level
    beneath is held to keeping them — the frame, in the level above's own words."""
    bridges = heads(store)
    concluded = {expand(head[1], names) for _, head, _, names in bridges}
    adds, retracts = predicted(store, step)
    if not any(f[1].value in concluded for f in adds):
        return None
    states = graphs_of(store, STATE)
    present = {(q.subject, q.predicate, q.object)
               for p in concluded for g in (*states, *revisions_of(store, *states))
               for q in quads_for_pattern(store, None, ox.NamedNode(p), None, g)}
    target = sorted(present - set(retracts) | {f for f in adds if f[1].value in concluded}, key=str)
    prefixes, conjuncts = set(), []
    for fact in target:
        branches = []
        for declared, head, where, names in bridges:
            bound = binding(head, fact, names)
            if bound is None:
                continue
            branch = where
            for var, term in bound.items():
                branch = re.sub(rf"\?{var}\b", term, branch)
            branches.append(branch)
            prefixes |= set(declared)
        if branches:
            conjuncts.append(" UNION ".join(f"{{ {b} }}" for b in branches))
    if not conjuncts:
        return None
    #  UNMET WHILE ANY FACT OF THE LANDING WORLD HAS NO WAY BELOW THAT HOLDS — one violation per
    #  such fact, so the search's met-test reads a conjunction and each fact its own union.
    goal = " UNION ".join(f"{{ FILTER NOT EXISTS {{ {c} }} }}" for c in conjuncts)
    select = ("\n".join(sorted(prefixes)) + "\n" if prefixes else "") + \
        f"SELECT $this WHERE {{ {goal} }}"
    want = f"{step}.below"
    graph = GRAPH_PREFIX + "want/refined/" + local_of(step)
    shape = f"{want}.met"
    update(store, f"""INSERT DATA {{ GRAPH <{graph}> {{
  <{me}> planning:holds <{want}> .
  <{step}> execution:keptBy <{want}> .
  <{want}> a planning:Want ; planning:metWhen <{shape}> ;
      rdfs:label "what {local_of(step)} comes to, one level down" ;
      prov:generatedAtTime {instant(now)} .
  <{shape}> a sh:NodeShape ; sh:targetNode <{me}> ;
      sh:sparql [ a sh:SPARQLConstraint ; sh:message "{local_of(step)} is not kept below yet" ;
                  sh:select {literal(select)} ] . }} }}""")
    classify(store, graph, WANT, OREXIS + "Recorded", me)   # the agent's own act, not a desire's derivation
    log.info("refining %s into %s — %d fact(s) of the world it lands in, held below",
             local_of(step), local_of(want), len(conjuncts))
    return want


