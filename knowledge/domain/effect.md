---
type: Domain Concept
title: Effect
description: >-
  What taking a means would MAKE TRUE, stated by the package that owns the acting as a SHACL-AF
  `sh:SPARQLRule` — a condition, a construct for what it adds, and `ag:retracts` for what it
  removes, which is ours because the standard has no deletion. It is what turns an affordance
  row from "this is available" into something a planner can reason about, and it carries the
  timing (`ag:landsAfter`) and the route by which it becomes knowable (`ag:confirmedBy`) so that
  the number a planner predicts and the number a keeper later verifies cannot be two numbers.
  Most means have no effect, and that is an ordinary answer.
---

# What it is

An [affordance](/domain/affordance.md) row says a [lever](/domain/lever.md) is available. It does
not say what pulling it would achieve — and a goal that is a shape needs exactly that, because
matching a goal to a lever means asking what the lever would make true.

So a package ships `effects.ttl` beside its `affordances.rq`, found the same way and named by
nothing: one `sh:SPARQLRule` per [means](/domain/means.md), loaded into the effect graph at
genesis. The vocabulary is SHACL Advanced Features' — `sh:condition` for the shape that must hold
before it may run, `sh:construct` for the query yielding the triples applying it would add. One
term is ours, `ag:retracts`, because the standard has none: SHACL rules exist to add entailments,
so nothing in it can say a thing stops being true.

**The engine is not SHACL's.** pySHACL will execute a `sh:SPARQLRule`, but only forward-chaining
to a fixpoint, mutating the graph — and a plan step is one rule against one hypothesis, which is
the opposite shape. A stored `sh:construct` is just a query, and this project already has an
engine that runs queries.

# Retraction is not decoration

The sensed graph **upserts** — one observation node per (subject, property), DELETE then INSERT
— so an effect predicting a reading that left the old one standing would put two results on one
node. A shape asking whether ANY reading sits past an edge would then answer about the reading
the dose just replaced, and a planner would reject the plan that works.

Order matters for the same reason: retract, then add. Observe's construct reuses the very node its
retraction names, so done the other way round the addition is removed by the retraction meant to
precede it and the possible world comes back holding neither reading.

# Two rules ship, and the pair is instructive

- **Observe** carries the current value forward with a new `sosa:resultTime`. Looking changes what
  you KNOW and nothing else, and the tempting error — predicting a reading inside the region,
  since that is what the agent wants — would teach a planner that a thirsty plant can be watered
  by looking at it.
- **Actuate** predicts the post-dose reading, which is the case that decided the whole shape of
  this: **opening a valve adds no triple.** It changes a number a later observation reports, and
  only a template that can predict the number can say so.

**Acquire is the third and it is honestly optimistic**: an agent does not control whether it wins,
so the rule predicts the world in which the bid clears. That is what planning does everywhere — a
STRIPS schema states what an action achieves, not what it achieves times a probability — and the
uncertainty lives in re-planning and monitoring, which is where this project already puts it.

# The prediction has ONE source, and it is enforced rather than intended

`litres / conversion` was already written twice in Python — the bidder sizing its expectation, the
actuator sizing its self-dose — before anything asked what a dose would do. The actuator now runs
the rule and subtracts rather than computing its own, so the number a planner uses to decide
whether dosing helps is the number the keeper later holds the world to.

Two numbers would mean an agent planning against one future and verifying against another, and
the failure would look like a device lying rather than like arithmetic disagreeing with itself.

# When it lands, and how you would know

Two more terms hang off the rule, for the same single-source reason one axis over.

`ag:landsAfter` is a SELECT yielding `?seconds`: how long until the WORLD CHANGE completes. A
query and not a number, because the duration is a function of the act — a two-litre dose holds a
valve open longer than a half-litre one. **Zero is a real answer** and the honest one for a look.

`ag:confirmedBy` names the route by which it becomes knowable, and there are four:

| route | means | example |
|---|---|---|
| `ag:ByConstruction` | saying makes it so | a claim issued, a debt demanded |
| `ag:ByReport` | a device says what it did | a valve's status channel |
| `ag:ByObservation` | a later reading shows it | the pot moved |
| `ag:Unconfirmed` | nothing will ever say | a valve with no status channel and no witness |

**Constitutive effects are the ones worth naming.** Conflating them with causal ones produces code
that verifies an agent really did write down what it just wrote down — and, worse, leaves a
planner waiting for a confirmation nobody will send.

The route says how you would find out and **nothing about whether there is anything to find out**.
The planner once used it for the second question, deciding which acts end a plan by asking the
route; every shipped effect answers `ag:ByObservation`, so every lever ended a plan and the search
never reached its second step. A discriminator whose every answer is the same one is not
discriminating.

# Most means have no effect, and that is fine

A lever whose consequences nobody has written down still works — the reflex can take it — it is
only one a planner cannot reason about. Every caller must take the absence as an ordinary answer,
because treating it as an error would make shipping a package a two-file obligation.

What a search must NOT do is conclude from a partial menu. A plan that passed over any lever is
marked partial and defers, because the lever it could not simulate may be the one that works.
