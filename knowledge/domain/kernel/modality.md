---
type: Domain Concept
title: Modality
description: >-
  What a graph's content asserts — is, will be, would be if, is wanted, is owed, is being done —
  where the subject and the property stay the same. Carried as the graph's KIND on its catalogue
  row, so a reader names the kinds it means and never a graph; one store holds them all.
---

# What it is

A moisture reading, a prediction of it, the same reading in a possible world, a desire that it
stay inside its range and an intention to dose it are five assertions about one subject and one
property. What tells them apart is not the triple but the graph it sits in, and what a graph
asserts is its kind:

| kind | force | owner |
|---|---|---|
| `orexis:BeliefGraph` | what IS, and what a possible world is made of: the world as ratified and as this agent holds it, the vocabulary, the self | the world's documents; belief's transitions write one per arrival, sensing a silence; what a scope can change of it is no kind but the writers' ([changeable](/domain/planning/changeable.md)) |
| `sensing:ObservationGraph` | what a sensor SAID, once — and no belief | sensing, beneath `orexis:Graph` alone; read at the boundary ([observation](/domain/sensing/observation.md)) |
| `orexis:ForecastGraph` | what WILL be, during a window, whoever says so - a belief beneath the first ([forecast](/domain/kernel/forecast.md)) | sensing from a series, the executor for a committed step, speech from a peer's statement; planning lays one where it begins where a text reads it, and the flows read one by its period; the predictor writes none, its foresight being the grounds (#1000) |
| `planning:PossibleGraph` | what WOULD be, if a plan were taken | the planner, in its [imaginarium](/domain/planning/imaginarium.md) |
| `execution:AddsGraph`, `execution:RetractsGraph` | what one [step](/domain/execution/step.md) WOULD make true and false | planning writes, the executor reads |
| `planning:DesireGraph`, `planning:WantGraph` | what is WANTED, standing or once | the world, and the derivation |
| `orexis:RecordGraph` | what is OWED or was done, worth believing for a period | a package's record |
| `execution:IntentionGraph` | what is being DONE | the executor |

What the agent reads to ACT asserts nothing of a subject and is no modality: its actions, flows,
shapes, constraints, derivations and rules are its program, no possible world is made of any of them,
and each is read by its own kind — `orexis:ActionGraph`, `orexis:FlowGraph`, `planning:ShapesGraph`,
`planning:ConstraintGraph`, `planning:DerivationGraph`, `sh:RulesGraph` — beneath `orexis:Graph` alone
([the-state-is-what-a-scope-can-change-and-everything-known-is-belief](/decisions/the-state-is-what-a-scope-can-change-and-everything-known-is-belief.md)).

The catalogue carries every kind a graph's class is beneath, so a reader asks `?g a
planning:WantGraph` or hands `store.graphs_of(BELIEF, PREDICTION)` its kinds and walks no path —
and never names a graph instance.

# The logics these belong to

Not strengths of one thing but different modal logics, in von Wright's grouping: a desire is
**bouletic**, an obligation **deontic**, what a world admits **alethic**, what is known and how
freshly **epistemic**. It earns its keep at one place — an unmet want is a gap and an unpaid debt
is a breach, so a debt is not a stronger desire even where both are searched alike.

# Not its neighbour

**Not arrival.** Asserted, derived, received and recorded say who put a fact there, on the same
catalogue row; a want is a want however it arrived ([who-put-the-fact-there](/decisions/who-put-the-fact-there.md)).
