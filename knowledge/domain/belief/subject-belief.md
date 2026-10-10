---
type: Domain Concept
title: Subject belief
term: http://example.org/orexis/belief#SubjectBeliefGraph
description: >-
  What the agent holds true of a subject, in the words of the domain whose transition said it - the
  bed is dry - and no number. Inserted by the transitions an arrival fires into a graph of the
  arrival's own, holding over its period, and taken out where it stands by the next arrival's.
---

# What it is

```turtle
# the bed's soil, in the belief:SubjectBeliefGraph of the observation that made it
:bed climate:soil climate:Dry .
```

A **subject belief** says what the agent holds true of a subject — the bed — in a domain's words: its
**state** (dry), and nothing about how any instrument is wired. It is about the subject, whose name
does not change from one reading to the next, and it speaks no SOSA.

**It holds the state and no number.** The number is the observation's
[reading](/domain/sensing/reading.md), and stays there: the mind compares triples and interprets no
literal, and the two readers of a number stand at the boundary — prediction, an estimator, and a
command, which sizes a step from the present when it is taken. Copied in, the number would be the
observation's testimony said twice, and the subject belief would change with every reading that
wobbles inside its state.

# Where it is kept

In a `belief:SubjectBeliefGraph`: one per arrival, named from it for eyes, the arrival's owner's and
derived, holding over the arrival's period — an [observation](/domain/sensing/observation.md)'s, so a
silence ends it as it ends the observation. It is beneath `orexis:StateGraph`, the agent's own state,
and kept in a volume lived in.

It is not derived from its arrival in PROV's sense. A [revision](/domain/belief/revision.md) is, and
goes when its source is forgotten; a subject belief outlives the observation it was made of, since
the next arrival must read it, until a [transition](/domain/belief/transition.md) takes it out. A graph
emptied that way is forgotten with its row; one a later arrival of the same name writes into again
takes that arrival's period.

# How it is made

A domain's transitions make it, fired by an arrival of the kind each declares, reading the state
before as a premise. Climate's soil and air make the [soil](/domain/actuation/soil.md) and the
[air](/domain/actuation/air.md), on an observation of soil moisture or air temperature: each deletes
what the agent held of the subject's soil or air and inserts the new state, held past the range's
[margin](/domain/sensing/margin.md) by the one it replaces. A subject stating no operating range for
the property gets none, a survival range judges none, and a property with no transition — humidity,
pressure, rain, a battery's voltage — is believed of nothing.

# What reads it

Nothing yet. Desires, actions, drifts and prediction read the observation and its sides as they did,
so no world's behaviour moved with it; making the mind read the subject belief instead, and a
predicted stretch fire its own transition, is the rest of #944.
