---
type: Domain Concept
title: Transition
term:
  - http://example.org/orexis/belief#triggeredBy
  - http://example.org/orexis/belief#delete
description: >-
  A rule that changes a state rather than concluding of it - a construct for what it inserts, a
  delete for what it takes out, grouped by order - triggered once by the arrival of a graph of the
  kind it declares, and applied by the belief package's one machine into a state graph the runner
  prepares. An action's effect is a transition the agent causes; a percept's is one the world
  causes. Testimony is never its target. What a percept's transition writes is a subject belief.
---

# What it is

```turtle
climate:soilRule a sh:SPARQLRule ;
    belief:triggeredBy sensing:ObservationGraph ;
    belief:delete """DELETE { ?subject climate:soil ?before } WHERE { … ?subject climate:soil ?before }""" ;
    sh:construct """CONSTRUCT { ?subject climate:soil ?state } WHERE { … }""" .
```

A **transition** is a `sh:SPARQLRule` whose `sh:construct` says what applying it inserts, whose
`belief:delete` — a `DELETE … WHERE` naming no graph — says what it takes out, or both. Its result
is not re-derivable from anything still held, since one of its premises is the state it replaced: it
is the state. That is what tells it from a [revision](/domain/belief/revision.md), which only adds,
runs to a fixpoint and is a function of its source; `revise` passes over any rule stating
`belief:triggeredBy`, and so does planning's [bridge](/domain/planning/bridge.md) reader.

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
- **The belief package** applies a percept's transition (`trigger`), once, when an arrival triggers
  it.

# What triggers it

As a database trigger runs once when a row of its table is inserted, and may delete and insert, **an
arrival triggers the transitions whose `belief:triggeredBy` names a kind its catalogue row
carries** — a class, never an instance, so a transition triggered by a kind is triggered by every kind
beneath it. That is all a transition declares. The [deliberator](/domain/belief/deliberator.md)
takes an arrival in two steps: it is revised until its rules settle, so a transition reads the
quantity the pipeline concluded and not the raw count, and then the transitions it triggers are
applied.

# Where it reads and writes: the runner's

A rule never knows the kind of graph it writes; each runner prepares its own target. Inference writes
into its source's revision graph, and an effect into the possible world it forked, in place. For a
transition `trigger` prepares a state graph of the arrival's own — the kernel's `orexis:StateGraph`,
the arrival's owner's and derived, holding over the arrival's period, named from the arrival for
eyes — so a silence ends what it says as it ends the arrival. One a later arrival of the same name
writes into again takes that arrival's period.

Each order reads the arrival with its revisions, the public graphs, and every state graph the agent
derived, whatever its period. What it deletes is taken out of whichever of those holds it, and a
graph emptied so is forgotten with its row. **Testimony is never a target**: a graph received or
heard — an observation is a state graph too, and received — a public graph, an ontology and a
revision are read and never written to. The target says no `prov:wasDerivedFrom`: a revision goes
when its source is forgotten, and this outlives the arrival it was made of, since the next arrival
must read it, until a later transition takes its rows out.

# What a percept's transition writes: a subject belief

```turtle
# the bed's soil, in the state graph of the observation that made it
:bed climate:soil climate:Dry .
```

A **subject belief** is what the agent holds true of a subject — the bed — in the words of the domain
whose transition said it: its **state** (dry), and nothing about how any instrument is wired. It is
about the subject, whose name does not change from one reading to the next, and it speaks no SOSA.
There is one per subject and property: each transition deletes what the agent held of the subject's
soil or air before inserting the new state.

**It holds the state and no number.** The number is the observation's
[reading](/domain/sensing/reading.md), and stays there: the mind compares triples and interprets no
literal, and the two readers of a number stand at the boundary — prediction, an estimator, and a
command, which sizes a step from the present when it is taken. Copied in, the number would be the
observation's testimony said twice, and the subject belief would change with every reading that
wobbles inside its state.

Climate's transitions make the [soil](/domain/actuation/soil.md) and the
[air](/domain/actuation/air.md), on an observation of soil moisture or air temperature, each held
past the range's [margin](/domain/sensing/margin.md) by the state it replaces. A subject stating no
operating range for the property gets none, a survival range judges none, and a property with no
transition — humidity, pressure, rain, a battery's voltage — is believed of nothing. Nothing reads a
subject belief yet: desires, actions, drifts and prediction read the observation and its sides as
they did, so no world's behaviour moved with it; making the mind read it instead is the rest of #944.

# Once, in turn, within a budget

Each order costs one rule execution per rule, revision's unit, and is applied whole or not at all;
an order begins while any of the budget is left. Where the budget runs out between orders the
deliberator keeps the arrival queued with the orders done, and the next pass applies the rest, never
an order twice. Arrivals are transitioned on in the order they came: one whose revision or
transitions are cut holds the transitions of every arrival queued after it, unless it triggers none;
and a graph written again is a new arrival and joins the end of the queue.

# Seams

- **A predicted arrival triggers nothing yet.** Climate's transitions are triggered by an
  observation, and a prediction's graph is of another kind; a predicted stretch's transition,
  confined to the prediction's own graphs, is #944's third slice
  ([a-transition-changes-the-state-and-an-inference-only-concludes](/decisions/a-transition-changes-the-state-and-an-inference-only-concludes.md)).
- **A restart repeats a cut between orders.** The revision row says an arrival unfinished, and a
  deliberator made again revises it and applies its transitions from the first order. Every shipped
  transition is one order, which makes that exact; a set of several cut between them would apply
  the first again. What would reopen it is a domain shipping a transition of a second order.
- **A pass is run where a graph is written.** An arrival left waiting with nothing written after it
  waits for the next write — the next reading, a prediction — as a revision cut short always has.
