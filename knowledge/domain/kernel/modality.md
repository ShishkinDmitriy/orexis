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
| `orexis:StateGraph` | what IS, as this agent holds it | the kernel; sensing's observation graph beneath it |
| `orexis:PredictionGraph` | what WILL be, during a window | prediction writes, planning reads |
| `planning:PossibleGraph` | what WOULD be, if a plan were taken | the planner, in its [imaginarium](/domain/planning/imaginarium.md) |
| `planning:DesireGraph`, `planning:WantGraph` | what is WANTED, standing or once | the world, and the derivation |
| `orexis:RecordGraph` | what is OWED or was done, worth believing for a period | a package's record |
| `execution:IntentionGraph` | what is being DONE | the executor |

The catalogue carries every kind a graph's class is beneath, so a reader asks `?g a
planning:WantGraph` or hands `store.graphs_of(STATE, PREDICTION)` its kinds and walks no path —
and never names a graph instance.

# The logics these belong to

Not strengths of one thing but different modal logics, in von Wright's grouping: a desire is
**bouletic**, an obligation **deontic**, what a world admits **alethic**, what is known and how
freshly **epistemic**. It earns its keep at one place — an unmet want is a gap and an unpaid debt
is a breach, so a debt is not a stronger desire even where both are searched alike.

# Not its neighbour

**Not arrival.** Asserted, derived, received and recorded say who put a fact there, on the same
catalogue row; a want is a want however it arrived ([who-put-the-fact-there](/decisions/who-put-the-fact-there.md)).
