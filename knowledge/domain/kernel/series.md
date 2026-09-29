---
type: Repository
title: Series
description: >-
  What a person watches of an agent and the agent never reads - its history, what happened, and
  its metrics, the admins' instrumentation of how it is doing - each written by a sink that knows
  nothing of what it writes, to a store the agent is told of by purpose. Metrics are code in each
  package, optional at every level, and aggregated to one point a minute.
---

# What it is

A **series** is time-stamped points in an InfluxDB bucket of the agent's own, for a person to
draw. It is watched and never believed: nothing written there reaches a plan. It has two
purposes, and the agent is told of a store for each apart, in environment keyed by the purpose —
two purposes may name one instance, by coincidence and not by design:

- **History** — what happened. Every observation, one point per property under that property's
  own name, and every step taken and how it ended, landed or failed, with its action, its want
  and its values. Each is contributed by the package that decides it: sensing when it writes the
  observation, execution when it records the act and when the world answers.
- **Metrics** — how the agent is doing, for whoever administers it: code watching code, not a
  description of anything, so it lives in code and nowhere in the model. In two shapes. A
  **gauge** says what a store holds — a search the budget cut short, an intention that failed, a
  sensor gone silent, a revision the budget cut — sampled once a window over the store its package
  names. An **event** says what happened and how long it took, which no gauge can answer and no
  row may hold, since no plan branches on it: the package that does the work tallies it as it
  happens. Every event of a window is aggregated in memory to one point per measurement and tag
  set, and written with the gauges at the window's end.

The **sink** sits beneath every contributor and knows nothing of what it writes. A store that
refuses a point is said in the log and costs the agent nothing.

# Why it is told by purpose

A series store has one writer and nobody to agree with, so it is a deployment fact and not a
world's ([deployment](/domain/onboarding/deployment.md)); its purposes, though, are concepts the
code may name. So the environment is keyed by purpose, never by instance, and the credential for
each is minted per purpose into the agent's own secrets.

**A series read back is no longer a series.** The day an agent reads its history — to learn a
drift, say — that history is a source, and it arrives through sensing and a transport like any
other testimony.

# What is built

History, told by purpose and contributed (#825). The sink is `agent/series.py`: it imports nothing
of the agent, and a sink per purpose is loaded where `INFLUX_HISTORY_URL`, `_ORG`, `_BUCKET` and
`_TOKEN` are all set — none set is no sink, some set is none too, said in the log. The runtime's
`main` loads it and hands it no point. A contributor asks `sink(HISTORY)` and builds nothing where
the answer is None, the way a module logs without knowing where its log goes; handing a sink down
instead would have sent it through the transport, which calls sensing and has no business with
history.

- **Sensing's** point (`agent/sensing/history.py`), written by `received`: measured under the local
  name of the property observed, field `value`, tagged with the subject's and the sensor's
  `orexis:localId`, at the reading's `sosa:resultTime`. The dashboards ask sensing for the name
  (`measurement_of`), so a panel draws what is written. The subject's tag is still called `plant`,
  a domain word #834 renames. Points 0.1.0 wrote as `soil_moisture` stay under that name.
- **Execution's** points (`agent/execution/history.py`), measured `Step`: field `taken` when the
  executor records the [act](/domain/execution/act.md), and field `landed` at the verdict — true
  where the present came to hold what the step predicted, false where the patience ran out or the
  want it was kept below as ended undone. A step predicting nothing has no verdict, nor has one not
  taken. Tagged `action`, `want` and one tag per parameter the action takes, all read off the step,
  so the executor spells no domain word. No panel draws steps yet.

Metrics, as code each package owns (#826, amended). The kernel of it is `agent/metrics.py`; what
is reported is each package's `metrics.py` — planning's, execution's, sensing's, belief's — and the
runtime's own in `agent/runtime.py`, and adding a metric is editing that one module. A package's
module is imported only where the package is loaded (#824), so an agent that senses nothing
reports no silence. Where no metrics sink is loaded nothing is tallied, timed or read.

| package | gauge, over | event, when: values; flags; tags beyond world and agent |
|---|---|---|
| the runtime | `store` (`quads`) and `process` (`uptime_s`) | `pass`, each pass: `duration_s` and each part's seconds; `unreachable`, a want nothing reaches: `desire` |
| planning | `plans` (by outcome) and `cone` (worlds, weighings, open, met), over the [imaginaria](/domain/planning/imaginarium.md) | `planner`, each pass: each part's seconds and the wants searched; `search`, each want each pass: `duration_s`, `budget`, `weighed`; `desire`, `scope`, `outcome`; `adopted`, a plan committed: `passes`, `weighed`, `wall_s`, `estimate`, `cost`; `replan`; `desire`, `scope`; `reroot`, each scope each pass: `kept`, `dropped`; `present` |
| execution | `intentions` (standing and by outcome) and `acts` (taken, not taken), over the intentions | `landing`, a verdict on a step: `late_s`; `timed_out`; `action`, `desire` |
| sensing | `silence` (`silent`), over the belief base | `received`, a reading replacing one: `interval_s`, `cadence_s`; `sensor` |
| belief | `revisions` (`revisions`, `unsettled`), over the belief base | `revise`, a revision pass: `sources`, `executions`, `cut`, `duration_s` |

**A gauge says which store it reads.** The imaginaria copy the belief base's readings and its
catalogue, so a select run over every store counts one silent probe once per scope; each package's
`gauges` takes the store it reads, and the runtime, which holds them all, hands each over. A
select-gauge's figures are summed across the stores it is handed, so they are counts, and they are
what the stores HOLD at the flush, not what a window added.

**An event is tallied, and a window is one point.** Per measurement and tag set: `count`; for each
value `<value>_sum`, `_mean` and `_max`, always floats so no window changes a field's type; for
each flag how many raised it, nought where none did. A field or tag the event does not declare is
left out and said in the log once. **A want's name is on no point**: it would be a tag of
unbounded values, which breaks the store's index, and it cannot be aggregated; the log names the
want, and history carries it on a step. `world` and `agent` are on every point — the agent's id is
what the process is told, and the world's name is the name of the directory it is handed, which
the buckets, the compose project and the dashboards already go by — and an event about a want is
tagged with the `desire` it was derived under, so a desire reads across worlds and agents.

**A window is real time, never the agent's.** The agent's clock may run fast in a simulation and
advances per read in a test, so a duration is `time.perf_counter`, the window is kept by a monotonic
clock, a flush is stamped by the wall, and nothing reads `agent.clock`. The window is sixty seconds
where the environment's `METRICS_INTERVAL_S` says nothing; a test drives it without sleeping. The
last window is written as the process stops — a `SIGTERM` is made an exit, so `podman stop` does
not lose it.

**Optional at every level.** An agent with no metrics sink computes nothing. A world is monitored
only where its own deployment graph says `onboarding:monitored`
([deployment](/domain/onboarding/deployment.md)): only then does `orexis-influx` mint each agent a
metrics bucket, `<world>-<agent>-metrics`, written to and never read by the agent and kept as many
days as the installation's `onboarding:retentionDays` says; only then does `orexis-compose` tell it
the store and the window; and only then does `orexis-dashboards` draw a health dashboard. That
dashboard is learnt from the packages' `metrics.py` themselves: a row per package that reports,
the runtime's first, and the agent a variable choosing whose bucket every panel reads; a gauge is
one panel, an event one panel of its count and flags and one per value. The history bucket keeps
the name the one bucket had, so a history begun before purposes goes on in it.
