---
type: Domain Concept
title: Transition
term:
  - http://example.org/orexis/belief#firesOn
  - http://example.org/orexis/belief#delete
description: >-
  A rule that changes a state rather than concluding of it - a construct for what it inserts, a
  delete for what it takes out, grouped by order - fired once by the arrival of a graph of the kind
  it declares, and applied by the belief package's one machine. An action's effect is a transition
  the agent causes; a percept's is one the world causes. Testimony is never its target.
---

# What it is

```turtle
climate:soilRule a sh:SPARQLRule ;
    belief:firesOn sensing:ObservationGraph ;
    belief:delete """DELETE { ?subject climate:soil ?before } WHERE { … ?subject climate:soil ?before }""" ;
    sh:construct """CONSTRUCT { ?subject climate:soil ?state } WHERE { … }""" .
```

A **transition** is a `sh:SPARQLRule` whose `sh:construct` says what applying it inserts, whose
`belief:delete` — a `DELETE … WHERE` naming no graph — says what it takes out, or both. Its result
is not re-derivable from anything still held, since one of its premises is the state it replaced: it
is the state. That is what tells it from a [revision](/domain/belief/revision.md), which only adds,
runs to a fixpoint and is a function of its source; `revise` passes over any rule stating
`belief:firesOn`, and so does planning's [bridge](/domain/planning/bridge.md) reader.

# One machine, two callers

`agent/belief/transition.py` groups the rules by `sh:order`, an absent order nought. Each order is
asked whole before any of it is applied: every construct is run, and every delete is asked as the
`CONSTRUCT` its own template and pattern spell, over the same graphs, so two rules of one order read
one state. Then what the deletes matched is taken out of the graphs the caller names, and what the
constructs made goes into the one graph the caller names — removals first. A later order reads what
the earlier made. A text that will not bind or run, a delete stating `WITH` or `USING`, and one that
is no `DELETE … WHERE` change nothing and are said in the log.

- **Planning** applies an action's [effect](/domain/planning/effect.md) through it, in the possible
  world a step makes: the world's graphs are read, and the new world is both what is taken from and
  what is added to.
- **The belief package** applies a percept's transition (`fire`), once, when an arrival fires it.

# What fires it, and where it writes

`belief:firesOn` names a graph kind — a class, never an instance — and an arrival fires every
transition stating a kind its catalogue row carries. The [deliberator](/domain/belief/deliberator.md)
takes an arrival in two steps: it is revised until its rules settle, so a transition reads the
quantity the pipeline concluded and not the raw count, and then the transitions it fires are applied.
Each reads the arrival with its revisions, the public graphs, and every state graph the agent
derived, whatever its period.

What an order inserts goes into the arrival's own [subject belief](/domain/belief/subject-belief.md)
graph, holding over the arrival's period, so a silence ends what it says. What an order deletes is
taken out of whichever of the agent's derived state graphs holds it, and a graph emptied so is
forgotten with its row. **Testimony is never a target**: a graph received or heard, a public graph,
an ontology and a revision are read and never written to.

# Once, in turn, within a budget

Each order costs one rule execution per rule, revision's unit, and is applied whole or not at all;
an order begins while any of the budget is left. Where the budget runs out between orders the
deliberator keeps the arrival queued with the orders done, and the next pass applies the rest, never
an order twice. Arrivals are transitioned on in the order they came: one whose revision or
transitions are cut holds the transitions of every arrival queued after it, unless it fires none;
and a graph written again is a new arrival and joins the end of the queue.

# Seams

- **A predicted arrival fires nothing yet.** Climate's transitions fire on an observation, and a
  prediction's graph is of another kind; a predicted stretch's transition, confined to the
  prediction's own graphs, is #944's third slice
  ([a-transition-changes-the-state-and-an-inference-only-concludes](/decisions/a-transition-changes-the-state-and-an-inference-only-concludes.md)).
- **A restart repeats a cut between orders.** The revision row says an arrival unfinished, and a
  deliberator made again revises it and applies its transitions from the first order. Every shipped
  transition is one order, which makes that exact; a set of several cut between them would apply
  the first again. The trigger is a domain shipping a transition of a second order.
- **A pass is run where a graph is written.** An arrival left waiting with nothing written after it
  waits for the next write — the next reading, a prediction — as a revision cut short always has.
