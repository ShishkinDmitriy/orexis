---
type: Domain Concept
title: Event
description: >-
  What a signal carries - an instance of a class the package declares in its events.py, saying
  whole what happened, so a handler asks nobody. Its class may name a metric and mark which fields
  are reported; it may answer a point, which is history. Made only where somebody hears.
---

# What it is

An event is what one [signal](/domain/kernel/signal.md) emission hands every handler: a frozen
dataclass instance, `PlanPublished(plan, want, desire, …)`, `IntentionResolved(intention, want,
outcome)`, `Observed(property, value, at, …)`. Its class belongs to the package that says it and
lives in `agent/<package>/events.py`, beside nothing else, so what a package says is read in one
module; the runtime's own two, a graph written and a pass, are in `agent/runtime.py`. It carries
every fact a handler needs, read by the emitter where it already stands, so the executor adopts
from a `PlanPublished` without asking the Planner anything.

An event costing a read is made only where the signal is heard: the emitter asks `connected` first.

# What its class may say

- **That it is reported**, by naming its `metric` and marking fields with the metrics' metamodel —
  a `Tag`, a `Value`, a `Flag` or a [level](/domain/kernel/level.md) — which the metrics part tallies
  without knowing the package; an unmarked field is the event's alone
  ([series](/domain/kernel/series.md)).
- **That it is history**, by answering `point()`, the series store's own dict, which the history
  part writes as it is heard.

# What it is not

**A belief.** It is not stored, and no plan branches on it; what it reports of the store was read
from the store and is still there
([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)).
