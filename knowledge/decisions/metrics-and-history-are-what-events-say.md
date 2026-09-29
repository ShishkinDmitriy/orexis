---
type: Decision
title: Metrics and history are what events say, and no package imports either
status: accepted
timestamp: 2026-09-29T20:00:00Z
description: >-
  The sovereign's ruling of 2026-09-29, after the parts learnt to signal each other. Every signal
  carries one event, a class its package declares; the class marks which fields are reported - a
  tag, a value, a flag, or a level, a figure that is the state now - and an event that is history
  answers its point. A metrics part and a history part, created where a store is named, hear every
  signal and know no package's words. Refused - each package calling its metrics and writing its
  history, gauges pulled once a window, deltas totalled by metrics, and the metrics package mapping
  each event.
---

# What was true (on main at f05a205d)

Every package that reported kept a `metrics.py`: gauges, each a select over a store it owned,
sampled by the runtime once a window, and events, called from its acts —
`SEARCH({...}, desire=…, scope=…)` from the Planner, `REVISE(...)` from the deliberator,
`LANDING(...)` from the executor — each behind `metrics.recording()`, with helpers reading the store
for a tag (`desire_of`, `derived_from`). Sensing's `received` and the executor wrote history
themselves, asking `sink(HISTORY)`. So every package imported the metrics and computed figures for
them in its acts: the coupling the parts had just shed between planning and execution, pointed at
instrumentation instead.

The same change had made every signal the object's own. The sovereign: *combine metrics with these
events — plan found, for what want, what plan, how long the search took. These events should all
be classes, as they are not from the triple store, and a metrics package just accumulates them for
a period and sends them.*

# The claim

**A signal carries one [event](/domain/kernel/event.md), an instance of a class its package declares**
in `agent/<package>/events.py`, said whole so a handler asks nobody. An emitter asks the signal
whether anything is connected before making an event that costs a read, so where nobody hears,
nothing is read or timed — which is what `metrics.recording()` guarded, now said by the one thing
that knows.

**The class says what is reported, in the metrics' metamodel and nothing else.** `agent/metrics/`
declares four marks — `Tag`, `Value`, `Flag`, and `Level` ([level](/domain/kernel/level.md)) — and a
class naming its `metric` marks its fields with them; an unmarked field, a want or a plan, is the
event's and never the metric's. A package imports the marks and nothing more of metrics.

**An event that is history answers `point()`**, the series store's own dict, shaped by the package
that decides the thing: sensing's observation, execution's step taken and the verdict on it.

**Two parts watch every part.** Where the environment names a store, the runtime creates
`agent/metrics/` or `agent/history/` like any package's part; linked, each connects to every signal
of every part and of the runtime, one tallying and writing the window at the end of a pass, the
other writing each point as it is heard. Neither imports a package, and no package imports
`agent.series`.

**What a store holds is a level on an event its owner already says**, read where the owner looks:
the Planner's `imagined` per scope after each pass, the executor's `walked`, the deliberator's
`revisions_held`, sensing's `silence` after each ask, the runtime's pass carrying the store's size
and the uptime. Counts that were gauges — intentions by outcome, acts taken — are events counted by
a tag or a flag, since each was a thing that happened.

# What was refused

- **Each package calling its metrics and writing its history** — what was true: an import of
  instrumentation in every act, and a figure computed for a reader the package should not know of.
- **Gauges declared and pulled once a window.** A second mechanism beside events, and the metrics
  part handed every package's stores to run them over — the imaginaria are the Planner's alone.
- **Deltas totalled by metrics** — `WorldMade`, `WorldsDropped`, a running sum. The store is the
  truth and a sum is a copy of it: worlds are forked, dropped by the re-root, forgotten by
  `withdraw` and swept by a refresh, in acts that emit nothing, so one missed site drifts for ever;
  and a restart begins the sum at nought beside a volume that still holds its intentions.
- **The metrics package holding a table per event class** of what is a tag and what is summed. The
  worry that raised this whole question: metrics knowing every package's words again, and every new
  event an edit there.
- **A level carried forward across windows.** An imaginarium dropped with its want would report its
  last cone for ever; a level nobody says in a window is written in none.

# What it costs

A level is read per event rather than per window. Measured on the greenhouse grower, each read in
isolation: an imaginarium's cone and plans 0.45 ms, the revisions 0.19 ms, the store's size 0.04 ms.
A whole pass with a sink writing nowhere against none, alternated within one session, three
sessions: the fastest idle pass +1 to +4 ms; the medians, idle and dosing, moved by −30 to +72 ms and
changed sign between sessions, which is the bench's noise and not a figure.

# What it amends

[a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md), in part: its
two metric amendments of 2026-09-27 stand for what they argued — metrics are code and not model,
optional at every level, one point a minute of real time, world, agent and desire the tags and a
want's name on no point — and are superseded where they place a metric in each package's
`metrics.py`, make a gauge a select sampled once a window, or have a package write its history
itself. [a-package-starts-itself](/decisions/a-package-starts-itself.md) loses `gauge` from what a
package is offered.

# Seams left open

- **A level is only as fresh as its owner's last event.** An idle planner reports the cone as it
  was; a package with no event to carry a level cannot report one.
- **An interval is remembered by sensing's part from its own start**, so the first reading after a
  restart has none; the reading replaced is gone by the time the graph written is heard.
- **The measurement names changed where the event did** — `adopted` is `published`, the plans and
  the cone are `imaginarium`, the intentions' outcomes are `intention` — and points written under
  the old names stay under them.
