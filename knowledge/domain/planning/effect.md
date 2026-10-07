---
type: Domain Concept
title: Effect
term: http://example.org/orexis/planning#effect
description: >-
  What taking an action makes true and false of the world it is taken in - a `planning:Effect`
  holding SHACL rules grouped by `sh:order`, a construct for what is added and a
  `planning:update` for what is deleted, run on the possible world a step makes and never on
  beliefs. The one declaration the search plans on and the world is held to.
---

# What it is

```turtle
planning:effect [ a planning:Effect ;
    sh:rule [ a sh:SPARQLRule ; sh:order 0 ; planning:update """PREFIX courier: <…>
        DELETE { $parcel courier:at ?cell } WHERE { $parcel courier:at ?cell }""" ] ,
            [ a sh:SPARQLRule ; sh:order 1 ; sh:construct """PREFIX courier: <…>
        CONSTRUCT { $parcel courier:carriedBy $van } WHERE { }""" ] ] .
```

The rules read the step's parameters as `$tokens`. `take` forks the world a candidate leaves and
runs them group by group: a construct's triples are added; an update deletes what stands where the
step changes something nobody could name in advance, the runner scoping it `WITH` the new world and
`USING` every graph the world reads. SHACL has only `sh:construct`, so the delete is planning's own
word. A rule of revision never deletes; an effect may, because a possible world is where taking
something away is the point.

# What it speaks

The concepts the rules conclude, not the raw numbers. A dose predicts the soil comes to be
`sensing:inside` its range — what sensing's rules would conclude of the next reading — and does not
predict a moisture value: the step is sized from the present when it is taken, by its command.

# What it is held to

The effect's own change, in the world it was applied to, is what the step predicts, held in
the two graphs it `execution:adds` and `execution:retracts`, and the
[executor](/domain/execution/executor.md) waits at the landing for the
present — readings and their revisions — to hold every addition and none of the retractions, asked
as one pattern over the two graphs. A
fictive action's effect is its own physics: the executor writes the prediction into the state
itself. Nobody sizes an expectation of their own.
