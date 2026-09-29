---
type: Domain Concept
title: Level
description: >-
  A reported field of an event that is the state now - worlds an imaginarium keeps, intentions
  standing, sensors silent, the store's size - read off the store where its owner already looks,
  and written as it last stood in a metrics window, never carried into one that did not say it.
---

# What it is

A level is the fourth mark of the metrics' metamodel (`agent.metrics.Level`), beside a tag, a value
and a flag: where a value is aggregated over a window and a flag counted, a level is replaced, and
the window writes the last one said, per measurement and tag set. It rides on an [event](/domain/kernel/event.md)
its owner says anyway — the Planner's `Imagined` per scope after a pass, the executor's `Walked`,
the deliberator's `RevisionsHeld`, sensing's `Silence`, the runtime's pass — and is read off the
store that owner holds, so it cannot drift from what the store holds. An event whose marks beyond
its tags are levels is a report of state and is not counted.

A window in which nobody said a level writes none of it: a level nobody says is a level nobody knows,
and an imaginarium dropped with its want must not report its last cone for ever.

It is what a gauge was — a select sampled once a window — moved onto the owner's own events, so the
metrics part holds no store and runs no select
([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)).
