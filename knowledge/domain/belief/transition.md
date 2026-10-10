---
type: Domain Concept
title: Transition
term:
  - http://example.org/orexis/belief#Transition
  - http://example.org/orexis/belief#delete
description: >-
  A rule that changes a state rather than concluding of it - a construct for what it inserts, a
  delete for what it takes out, grouped by order - typed belief:Transition and declaring no trigger.
  Every arrival of testimony triggers every transition once, its WHERE saying what it is about, and
  the belief package's one machine applies it into a state graph the runner prepares. An action's
  effect is a transition the agent causes; a percept's is one the world causes, and a predicted
  observation arriving in a ground the planner lays triggers it there, changing the ground alone.
  Testimony is never its target. What a percept's transition writes is a subject belief, and the
  mind reads nothing else.
---

# What it is

```turtle
climate:soilRule a belief:Transition ;
    belief:delete """DELETE { ?subject climate:soil ?before } WHERE { ?obs sosa:observedProperty climate:SoilMoisture … }""" ;
    sh:construct """CONSTRUCT { ?subject climate:soil ?state } WHERE { ?obs sosa:observedProperty climate:SoilMoisture … }""" .
```

A **transition** is a `belief:Transition`, a SPARQL rule — the class is beneath `sh:SPARQLRule` —
whose `sh:construct` says what applying it inserts, whose `belief:delete` — a `DELETE … WHERE`
naming no graph — says what it takes out, or both. Its result is not re-derivable from anything
still held, since one of its premises is the state it replaced: it is the state. That is what tells
it from a [revision](/domain/belief/revision.md), which only adds, runs to a fixpoint and is a
function of its source. The type is how the runner finds a transition, and how `revise` and
planning's [bridge](/domain/planning/bridge.md) reader pass over it, whatever other type it states.

# One machine, three runners

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
- **The belief package** applies a percept's transition (`trigger`), once, when an arrival of
  testimony triggers it.
- **Planning** applies the same transitions (`transitions`, the one read of them both use) in each
  ground it lays ahead, once per predicted observation arriving there (`lay_ground`, #944). Below.

# What triggers it

As a database trigger runs once on each row inserted into its table, and may delete and insert,
**an arrival of testimony triggers every transition once.** Testimony is a graph whose catalogue row
says it arrived `orexis:Received` — an instrument's observation, a forecast, a peer's document heard.
Nothing else triggers one: the agent's own graphs, derived or recorded — a prediction, a committed
step, the very state a transition writes — and what the sovereign asserted trigger none, so a
transition's output can never trigger it again. A transition declares no trigger at all.

**Its WHERE says what it is about.** It is handed the arrival and no other testimony, so climate's
`?obs sosa:observedProperty climate:SoilMoisture` can match only a soil reading that has just
arrived; on an air reading it matches nothing and changes nothing, though both of climate's
transitions run on every reading. The [deliberator](/domain/belief/deliberator.md) takes an arrival
in two steps: it is revised until its rules settle, so a transition reads the quantity the pipeline
concluded and not the raw count, and then the transitions it triggers are applied.

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
heard — a percept, which is no state and is read as the arrival alone — a public graph, an ontology and a
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
transition — humidity, pressure, rain, a battery's voltage — is believed of nothing. **The mind
reads nothing else** (#944): a [desire](/domain/planning/desire.md) asks the bed's soil and air, and
the dose, the heating and the market's presenting take the [subject](/domain/actuation/subject.md)
and speak its state in their preconditions and effects. A reading's number has two readers left,
both at the boundary: a command sizing a step when it is taken, and a drift.

# In a ground: a predicted observation arriving

A prediction is the agent's own and no testimony, so in the belief base it triggers nothing. But a
[ground](/domain/prediction/prediction.md) the planner lays ahead is the period before it with the
prediction applied, and the prediction's predicted observation ARRIVES there as a received one
arrives in the present: `lay_ground` runs every transition it triggers, once, order by order, through
this machine. Each order reads the predicted observation with its revisions, the public graphs, and
the agent's own state as the ground before it left it — kept apart from the ground while the grounds
are laid, since a ground is one graph and holds testimony beside the state, and a transition is
handed no testimony but its arrival. What an order deletes is taken out of the ground and what it
inserts put into it: the runner's target is the ground being laid, and the present is never written
to. So a bed believed dry and resting at 0.3001 is foreseen dry, the hold reaching the forecast, and
a ground that comes to hold what the one before held is still no period
(`agent/planning/tests/lay_ground/a_predicted_reading_is_judged_beside_the_state_the_ground_before_held.trig`).
No budget is spent there: a ground holds what its predictions make of it, whole, or it is no ground.

# Once, in turn, within a budget

Every transition is asked on every arrival of testimony, whether its WHERE matches or not, so what
the transitions cost is their number times the testimony that arrives. Each order costs one rule
execution per rule, revision's unit, and is applied whole or not at all;
an order begins while any of the budget is left. Where the budget runs out between orders the
deliberator keeps the arrival queued with the orders done, and the next pass applies the rest, never
an order twice. Arrivals are transitioned on in the order they came: one whose revision or
transitions are cut holds the transitions of every arrival queued after it, unless it triggers none;
and a graph written again is a new arrival and joins the end of the queue.

# Seams

- **A predicted arrival triggers nothing in the belief base.** It triggers its transitions in the
  ground it is laid into and nowhere else, so the predictions in the store hold numbers and no state;
  what would change that is a reader of a prediction that is no ground
  ([a-transition-changes-the-state-and-an-inference-only-concludes](/decisions/a-transition-changes-the-state-and-an-inference-only-concludes.md)).
- **A forecast is testimony, and triggers every transition.** An observation in it of a property a
  transition is about would be judged as a reading is, over the forecast's stretch. The one shipped
  forecast is the terrace's precipitation, which no transition is about; a domain forecasting a
  property it judges says in its WHERE which it means.
- **A restart repeats a cut between orders.** The revision row says an arrival unfinished, and a
  deliberator made again revises it and applies its transitions from the first order. Every shipped
  transition is one order, which makes that exact; a set of several cut between them would apply
  the first again. What would reopen it is a domain shipping a transition of a second order.
- **A pass is run where a graph is written.** An arrival left waiting with nothing written after it
  waits for the next write — the next reading, a prediction — as a revision cut short always has.
