---
type: Domain Concept
title: Event
term: http://example.org/orexis#Event
description: >-
  What happened, at an instant - an instance of a class its package declares, never the cause of
  another event. A policy hearing it may start an activity, whose start and end are events too. Its
  class may name a metric and mark which fields are reported; it may be history, as a point or as
  triples in the package's words. Made only where somebody hears.
---

# An instant, heard by policies

An event has no duration: it is a `prov:InstantaneousEvent`, said once at the instant it happened. It
never triggers another event. A [policy](/domain/kernel/policy.md) hears it and decides whether to start
an [activity](/domain/kernel/activity.md), and an activity's start and end are events in their turn; a
more specific event may be said at the same instant, naming the one it specifies
([packages-meet-by-events-policies-and-activities](/decisions/packages-meet-by-events-policies-and-activities.md)).

# What it is

An event is what a part says to the agent's one watch: a value, `PlanPublished`, `IntentionResolved`,
`Observed`, whose class belongs to the package that says it and lives in its `events.rs`, so what a
package says is read in one module; the runtime's own, a graph written and a pass, are in
`crates/orexis/src/runtime.rs`. Every hearer of the watch hears it at once, on the thread of the part that said it - the journal,
the series and the tracer - and where its class is beneath a part's trigger the runtime hands it to
that part's [policy](/domain/kernel/policy.md), by what it is about: the entities it NAMES, never their
content, which the policy reads from the store, written there before the event was said.

An event costing a read is made only where it is heard: the emitter asks `connected` first.

# What its class may say

- **That it is reported**, by naming its `metric` and marking fields with the metrics' metamodel —
  a `Tag`, a `Value`, a `Flag` or a [level](/domain/kernel/level.md) — which the metrics part tallies
  without knowing the package; an unmarked field is the event's alone
  ([series](/domain/kernel/series.md)).
- **That it is history**, by answering `point()`, the series store's own dict, which the history part
  writes to the [series](/domain/kernel/series.md) — an observation alone does — or `statements(node)`,
  its triples in its package's words, which the history part keeps in the agent's
  [journal](/domain/kernel/journal.md) as an entry named by `node`. Such an event is then a term too: its
  class is declared beneath `orexis:Event` in the package's ontology, its words beside it, and
  `agent/tests/test_journal.py` holds every word an event writes to a declaration.

# What it is not

**A belief.** It is not stored where any plan reads, and no plan branches on it; what it reports of the store was read
from the store and is still there
([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)).
