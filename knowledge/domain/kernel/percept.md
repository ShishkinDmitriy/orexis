---
type: Domain Concept
title: Percept
term: http://example.org/orexis#PerceptGraph
description: >-
  What a sensor said - one reading, in a graph of its own, kept as the premise and not believed. Its
  kind sits beneath orexis:Graph alone, so no reader of the mind is handed one; the readers at the
  boundary name it - the rules of the package that writes it, prediction, a transition handed its
  arrival, and an operation sized as a step is taken. A sensor's percepts form a chain, the latest
  holding now and every older one ended where the next began; what the rules conclude of one is a
  percept too.
---

# What it is

```turtle
# a reading, as sensing writes it: its own node and graph, linked to the one before
GRAPH observed:probe_20260101T120000Z {
  :obs_probe_20260101T120000Z a sosa:Observation ; sosa:madeBySensor :probe ;
      sensing:rawResult 2412 ; sosa:resultTime "2026-01-01T12:00:00Z"^^xsd:dateTime ;
      sensing:previous :obs_probe_20260101T115000Z . }
```

A **percept** is what one sensor said at one instant: an [observation](/domain/sensing/observation.md)
in a graph whose kind is `orexis:PerceptGraph` — sensing's `sensing:ObservationGraph` is beneath it —
received, the agent's own. It is testimony, kept because it is the premise
([a-situated-instance-is-kept-only-when-it-is-testimony](/decisions/a-situated-instance-is-kept-only-when-it-is-testimony.md)),
and it is no belief: what the agent holds of the subject is the subject belief a domain's
[transition](/domain/belief/transition.md) makes when the percept arrives, and the mind reads that
alone ([an-observation-is-a-percept-and-the-mind-reads-only-beliefs](/decisions/an-observation-is-a-percept-and-the-mind-reads-only-beliefs.md)).

# Where its kind sits, and who is handed one

Beneath `orexis:Graph` and nothing else. Every reader of the mind names `orexis:BeliefGraph` or a
kind beneath it — a desire, a precondition and an effect are answered over the beliefs, the
[imaginarium](/domain/planning/imaginarium.md) is filled with the kinds that cross, a ground is laid
from the state graphs, and a world is hashed within what those texts read — so a percept reaches
none of them by construction, and nothing has to remember to leave it out. It was beneath
`orexis:StateGraph` until #944's fourth slice, and the planner was handed every reading as state.

**A revision of a percept is a percept.** What sensing's rules conclude of it — what it is of, its
quantity, whether its sensor is stuck — is still what the sensor said, so revision writes it into a
graph of the source's kind (`belief:RevisionGraph` beside `orexis:PerceptGraph`), and `revisions_of`
finds it beside its source as it finds a belief's.

The readers that name the kind stand at the boundary, and there are four: sensing's own rules, run
by the [deliberator](/domain/belief/deliberator.md) as a percept arrives; the
[prediction](/domain/prediction/prediction.md) package, reading the latest as the observation in
hand; a transition, handed its arrival and no other testimony; and an
[operation](/domain/execution/operation.md) — a command or a saying — sized from the present when a
step is taken. The kind is the kernel's, though sensing alone writes it, because those four are four
packages and none may speak another's word.

# The latest, and the ones kept

Each percept names the one its sensor made before it (`sensing:previous`), so a sensor's percepts
are a chain, and **the latest is the one no percept names**. Its period runs from its instant until
the next reading is due and a grace past it; a reading arriving ends the one before at its own
instant, so every older percept has ended and a reader standing at an instant is handed one per
sensor — the one holding then, which is the latest while it holds. Past its end there is none, which
is what a reading missing is.

Sensing keeps as many of a sensor's percepts as its deepest rule reads — the [stuck](/domain/sensing/stuck.md)
rule's, the agent's `sensing:stuckAfter` — and forgets the oldest past them, with what was concluded
of each. **Nothing else drops one**: no sweep forgets a graph because its period has ended (the
executor's sweep is of its committed steps alone), so an ended percept stays as what the sensor said
then until sensing lets it go. A percept is never a [series](/domain/kernel/series.md): what is kept
is what a rule reads, and history is what a person watches.

# What is not a percept

A [forecast](/domain/sensing/forecast.md) is another party's word about a stretch ahead and is a
belief. A prediction's predicted observation is the agent's own, of a node of its own, and crosses
into the grounds the planner lays; the percept it was made from never does.
