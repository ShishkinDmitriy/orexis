---
type: Domain Concept
title: Action
term: http://example.org/orexis#Action
description: >-
  One way of acting, as one node a domain ships in its `actions.ttl`: what it takes, when a world
  admits it (a precondition), what taking it makes true and false (an effect), what goes out
  when a step of it is taken (an implementation), and what it costs and how long it takes to land.
  The search reads the first two, the executor carries out the third, and the world is held to
  the second.
---

# What it is

The STRIPS operator, whole, and the KIND of act: a [step](/domain/execution/step.md) is an action
picked with its parameters filled, a plan is steps, and an intention walks them. Twelve ship across
the domains — `hanoi:Move`, the courier's `Drive`, `Pick` and `Drop`, `actuation:Dosing`,
`climate:Heating`, and the market's six — and each is a node like this; a thirteenth, the
[wait](/domain/planning/wait.md), is the planning package's own and states its cost alone:

```turtle
courier:Pick a orexis:Action ;
    orexis:takes courier:parcel , courier:van ;
    planning:precondition """SELECT ?parcel ?van WHERE { … }""" ;
    planning:effect [ a planning:Effect ;
        sh:rule [ a sh:SPARQLRule ; belief:delete """DELETE { … } WHERE { … }""" ] ,
                [ a sh:SPARQLRule ; sh:construct """CONSTRUCT { … } WHERE { … }""" ] ] ;
    planning:costs """SELECT ?cost WHERE { BIND(1.0 AS ?cost) }""" ;
    execution:implementation [ a execution:Implementation ;
        execution:operation [ a execution:Fictive ] ] .
```

# Its parts, and whose each is

- **What it takes** — `orexis:takes`, one IRI per parameter. The local part is the variable the
  precondition projects, the `$token` the rules read and the predicate a step is written under,
  so one spelling serves all three ([an-action-takes-parameters](/decisions/an-action-takes-parameters.md)).
- **When it is admitted** — the [precondition](/domain/planning/precondition.md), a SELECT whose
  rows in a world are the steps that world admits. Zero rows is ordinary.
- **What it makes true and false** — the [effect](/domain/planning/effect.md), rules run on the
  possible world a step makes: a [transition](/domain/belief/transition.md) the agent causes, its
  delete spoken in belief's word since belief's machine applies it.
- **What goes out** — the [implementation](/domain/execution/implementation.md), operations the
  executor runs when a step is taken: a command, a saying, or fictively the effect itself.
- **Cost and timing** — `planning:costs` and `planning:landsAfter`, selects the search reads to
  rank a plan and place its steps.

The first two and the last are planning's words and the implementation is execution's;
`orexis:Action` and `orexis:takes` are the kernel's because both packages meet at them.

# How it is read

A domain's `actions.ttl` says it is an `orexis:ActionGraph`, as the planning package's `wait.ttl`
does, and the planner reads actions from graphs of that kind alone. `admit` runs each precondition in a world and writes a candidate per
row; `take` forks the world and runs the effect's rules; the executor reads the implementation off
the action a step fills when the step comes due. Adding a way of acting is a node in a domain's
`actions.ttl` and nothing else: no Python, no registry.

An action is a T-Box term, so code may name it; every value it is filled with is an instance, and
code never names one. Which action a world reaches for is the search's answer, ranked by cost.
