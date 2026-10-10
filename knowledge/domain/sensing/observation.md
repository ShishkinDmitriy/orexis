---
type: Domain Concept
title: Observation
term:
  - http://www.w3.org/ns/sosa/Observation
  - http://example.org/orexis/sensing#previous
description: >-
  One act of observing, as SOSA says it - which sensor, the number it gave, when - and, concluded by
  sensing's rules, which property of which feature and the quantity. One per reading, named for its
  sensor and its instant, in a graph of its own, and linked to the one its sensor made before by
  sensing:previous - a percept, kept as deep as sensing's rules read and handed to no reader of the
  mind. The premise every prediction is made from, and what triggers a domain's transitions.
---

# What it is

```turtle
# the reading's graph, as `received` writes it: what the sensor gave, and the one before it
:obs_probe_20260920T120000Z a sosa:Observation ; sosa:madeBySensor :probe ; sensing:rawResult 2412 ;
    sosa:resultTime "2026-09-20T12:00:00Z"^^xsd:dateTime ;
    sensing:previous :obs_probe_20260920T115000Z .
# its revision, as sensing's rules conclude it from the topology and the probe's scaling
:obs_probe_20260920T120000Z sosa:observedProperty climate:SoilMoisture ; sosa:hasFeatureOfInterest :fern ;
    sensing:scaledResult 0.414737 ; sosa:hasSimpleResult 0.414737 .
```

Written by [sensing](/domain/sensing/sensing.md)'s `received` into a `sensing:ObservationGraph` of its
own, one per reading: a **percept**, and no state. A new reading does not
replace the one before; it names it, by **`sensing:previous`**, and ends its period at its own
instant, so a sensor's observations are a chain whose latest is the one nothing names. The latest
holds until the next is due and a **grace** past it, or until the next arrives, whichever is first.
The grace is how late a reading may be and still be the promise its sensor's cadence made, one
cadence (`received.GRACE`): a reading late inside it is not missing, and the one in hand is still the
present ([a-reading-late-is-not-a-reading-missing](/decisions/a-reading-late-is-not-a-reading-missing.md)).
What it is OF and its [reading](/domain/sensing/reading.md) are in its revision, a percept too, so a
reader of an observation reads the graph and its revisions together (`store.revisions_of`), as the
prediction and a command do.

The readings one message carries — a sentinel's last quiet sample before the one that broke its
window — are observations of their own in the same chain, oldest first, each ending where the next
begins.

# Why it is kept, and how many

It is testimony, the one thing in the store that is somebody else's word (`orexis:Received`), and
it is the premise: what a rule concludes of it is a [revision](/domain/belief/revision.md) in a
graph derived from it, and what a drift makes of it is a
[prediction](/domain/prediction/prediction.md). Its revisions go when it is forgotten, because they
were about it; its predictions go when the next reading of its sensor is predicted from.

A sensor's last `sensing:stuckAfter` are kept, since the [stuck](/domain/sensing/stuck.md) rule reads
that many, and the oldest past them is forgotten as each new one arrives. So the oldest kept names
one that is gone, and nothing about the past is carried onto the present by its writer.

One thing made of it outlives it: the subject belief a domain's
[transition](/domain/belief/transition.md) inserted when it arrived, which is not derived from it, and
which the next observation of the key's transition reads as the state before and takes out. It holds
over the observation's period as it was when it arrived, so where no next reading comes it ends at
the grace all the same.

# A percept, and who is handed one

A percept is what a sensor said, kept as the premise and not believed
([an-observation-is-a-percept-and-the-mind-reads-only-beliefs](/decisions/an-observation-is-a-percept-and-the-mind-reads-only-beliefs.md)).
Its kind is sensing's alone, beneath `orexis:Graph` and nothing else: no sensing, no observations.
Every reader of the mind names `orexis:BeliefGraph` or a kind beneath it — a desire, a precondition,
an effect, the [imaginarium](/domain/planning/imaginarium.md)'s crossing, a ground, a world's hash —
so an observation reaches none of them by construction, and nothing has to remember to leave it out.

What sensing's rules conclude of one is a percept too: sensing hands each observation to belief's
[deliberator](/domain/belief/deliberator.md) as it arrives, with the kind its revision is to be, its
own, so belief revises it and runs the transitions it triggers knowing no word of sensing's. The
other readers stand where they may speak the word or ask the package that has it: prediction, above
sensing, names the kind to find the observation in hand; an [operation](/domain/execution/operation.md)
names it in its own text, sized from the present when a step is taken; and a transport, beneath,
asks sensing which readings have lapsed (`cadence.lapsed`).

# What is not one

A [forecast](/domain/sensing/forecast.md) is another party's word about a stretch ahead, and is a
belief. A prediction's predicted observation is the agent's own, a node of its own, and crosses into
the grounds the planner lays; the observation it was made from never does.
