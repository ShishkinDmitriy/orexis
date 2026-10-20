---
type: Domain Concept
title: Effect
term: http://example.org/orexis/planning#effect
description: >-
  What taking an action makes true and false of the world it is taken in - a `planning:Effect`
  holding rules grouped by `sh:order`, each a `belief:Transition` whose one `belief:update` takes out
  and adds over one WHERE, applied through belief's machine on the possible world a step makes and
  never on beliefs. The one declaration the search plans on and the world is held to.
---

# What it is

```turtle
planning:effect [ a planning:Effect ;
    sh:rule [ a belief:Transition ; belief:update """PREFIX courier: <…>
        DELETE { $parcel courier:x ?x ; courier:y ?y }
        INSERT { $parcel courier:carriedBy $van }
        WHERE  { $parcel courier:x ?x ; courier:y ?y }""" ] ] .
```

An effect is a [transition](/domain/belief/transition.md) the agent causes, and every rule of it is
typed one: the rules read the step's parameters as `$tokens`, and `take` forks the world the
candidate leaves and hands each rule in turn to the belief package's machine as the engine's own
update — the world with the fork in its place is what it reads, and the fork is both what a delete
template's matches are taken out of and where an insert template's triples go. A fork that comes out
as the world it was copied from is no move, and is dropped (#953). A delete template takes away
what stands where the step changes something nobody could name in advance. SHACL's rules only
construct, so the update is belief's word, beside the machine that applies it. An inference never
deletes; an effect may, because a possible world is where taking something away is the point.

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
