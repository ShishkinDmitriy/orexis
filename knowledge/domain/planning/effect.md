---
type: Domain Concept
title: Effect
term: http://example.org/orexis/planning#effect
description: >-
  What taking an action makes true and false of the world it is taken in - a `planning:Effect`
  holding SHACL rules grouped by `sh:order`, a construct for what is added and a
  `belief:delete` for what is taken out, applied through belief's machine on the possible world a
  step makes and never on beliefs. The one declaration the search plans on and the world is held to.
---

# What it is

```turtle
planning:effect [ a planning:Effect ;
    sh:rule [ a sh:SPARQLRule ; sh:order 0 ; belief:delete """PREFIX courier: <…>
        DELETE { $parcel courier:at ?cell } WHERE { $parcel courier:at ?cell }""" ] ,
            [ a sh:SPARQLRule ; sh:order 1 ; sh:construct """PREFIX courier: <…>
        CONSTRUCT { $parcel courier:carriedBy $van } WHERE { }""" ] ] .
```

An effect is a [transition](/domain/belief/transition.md) the agent causes, and the rules have its
shape: they read the step's parameters as `$tokens`, and `take` hands them, order by order, to the
belief package's machine — the world the candidate leaves is what they read, and the world the step
makes, forked at the first order that changes something, is both what a delete's matches are taken
out of and where a construct's triples go. A delete takes away what stands where the step changes
something nobody could name in advance. SHACL has only `sh:construct`, so the delete is belief's
word, beside the machine that applies it. An inference never deletes; an effect may, because a
possible world is where taking something away is the point.

# What it speaks

The state the agent believes its [subject](/domain/actuation/subject.md) in, in the domain's words,
not a reading and not a number. A dose deletes the bed's `climate:soil climate:Dry` and inserts
`climate:Moist` — what climate's soil transition would make of the next reading — and does not
predict a moisture value: the step is sized from the present when it is taken, by its command, the
one reader of the subject's latest observation on this side (#944).

# What it is held to

The effect's own change, in the world it was applied to, is what the step predicts, held in
the two graphs it `execution:adds` and `execution:retracts`, and the
[executor](/domain/execution/executor.md) waits at the landing for the
present — readings and their revisions — to hold every addition and none of the retractions, asked
as one pattern over the two graphs. A
fictive action's effect is its own physics: the executor writes the prediction into the state
itself. Nobody sizes an expectation of their own.
