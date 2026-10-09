---
type: Domain Concept
title: Subject belief
term:
  - http://example.org/orexis/sensing#SubjectBeliefGraph
  - http://example.org/orexis/sensing#judged
  - http://example.org/orexis/sensing#valueAs
  - http://example.org/orexis/sensing#stateAs
  - http://example.org/orexis/sensing#belowAs
  - http://example.org/orexis/sensing#insideAs
  - http://example.org/orexis/sensing#aboveAs
description: >-
  What the agent holds true of a subject for one observable property, in the words of the domain
  that owns the property - its state and its value. One per key, made of the latest observation
  judged beside the subject belief it replaces, and replaced whole; the state is held by the
  subject belief itself, with the range's margin.
---

# What it is

```turtle
# the bed's soil, in a sensing:SubjectBeliefGraph of the grower's own
:bed climate:soil climate:Dry ; climate:moisture 0.3001 .
```

A **subject belief** says what the agent holds true of a subject — the bed — for one
`sosa:ObservableProperty` — its soil moisture: the **state** the subject is in, which the domain
names (dry), and the **value** (0.3001). It is about the subject, whose name does not change from
one reading to the next, and it speaks the domain's words and no SOSA. There is one per key, a
subject and a property, in a `sensing:SubjectBeliefGraph` of the agent's own: derived, holding over
the period of the [observation](/domain/sensing/observation.md) it was made of, so it ends with that
observation and a silence ends it too, and kept in a volume lived in. The kind is beneath
`orexis:StateGraph`, the state a met-test reads.

The subject is the observation's feature of interest, or what that is a sample of: whichever states
an operating range for the property, the [region](/domain/sensing/region.md) its state is judged
against. A survival range is judged into none, since nothing in the mind reads it.

# How a domain says it

On the property, in sensing's words, the domain that owns it says which of its words carry the
belief: `sensing:valueAs` the predicate the value is believed in, `sensing:stateAs` the one the state
is, and `sensing:belowAs`, `sensing:insideAs` and `sensing:aboveAs` the state for each side of the
subject's operating range. Climate says them of the [soil](/domain/actuation/soil.md) and the
[air](/domain/actuation/air.md). A property whose domain says nothing — humidity, pressure, rain, a
battery's voltage — gets no subject belief, and a subject stating no operating range for a property
gets none either, having no state to be judged in.

# How it is made

**One rule judges, and the domain only names.** Sensing's rule (`agent/sensing/rules.ttl`) reads the
observation's [reading](/domain/sensing/reading.md), the subject's operating range for the property,
its [margin](/domain/sensing/margin.md), the domain's declarations and the subject belief it will
replace, and concludes the state, `sensing:judged`, as a [revision](/domain/belief/revision.md) of
the observation. Written once for every property, the hold cannot drift between them, and a domain
adds a property by naming three states. The judgment sits on the observation, never as the
subject's state, because a conclusion a rule shares with a graph it reads is no inference, and the
state judged is most often the one believed before.

**Sensing then writes it, replacing the one before whole** (`believe`). A rule concludes and never
deletes, and one premise of a subject belief is the subject belief it replaced, so it is written and
not derived: kept beside testimony because a premise of it is gone. Sensing's part hears the
[deliberator](/domain/belief/deliberator.md) say what it revised, and for each observation the rule
judged it forgets the graph holding the key's subject belief before, found by its content, and
writes the new one: the state judged, and the reading as the value. A revision a budget cut short
is continued beside the same subject belief, which nothing replaces until the judgment is there.

The readings one message carries are judged in turn, each beside the subject belief the reading
before it made, since the pass runs on one thread and revises each as it is written. Where a budget
cut the earlier short, the later is judged beside the subject belief the message found, and one made
of a later observation is never replaced by one of an earlier.

# What reads it

Nothing yet. Desires, actions, drifts and prediction read the observation and its sides as they did,
so no world's behaviour moved with it; what makes the mind read the subject belief instead, and a
predicted number become a predicted one, is the rest of #944.
