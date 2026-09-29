---
type: Repository
title: Series
description: >-
  What a person watches of an agent and the agent never reads - its history, what happened, and
  its metrics, the admins' instrumentation of how it is doing - each written by a sink that knows
  nothing of what it writes, to a store the agent is told of by purpose. Both are what the packages'
  events say, written by a part that hears every signal; metrics are optional at every level and
  aggregated to one point a minute.
---

# What it is

A **series** is time-stamped points in an InfluxDB bucket of the agent's own, for a person to
draw. It is watched and never believed: nothing written there reaches a plan. It has two
purposes, and the agent is told of a store for each apart, in environment keyed by the purpose —
two purposes may name one instance, by coincidence and not by design:

- **History** — what happened. Every observation, one point per property under that property's
  own name, and every step taken and how it ended, landed or failed, with its action, its want
  and its values. Each is an [event](/domain/kernel/event.md) of the package that decides it, which
  answers its point: sensing's observation, execution's act recorded and the world's answer.
- **Metrics** — how the agent is doing, for whoever administers it: code watching code, not a
  description of anything, so it lives in code and nowhere in the model. An event says what
  happened and how long it took, which no row may hold, since no plan branches on it, and a
  [level](/domain/kernel/level.md) on an event says what a store holds now — a search the budget cut
  short, a sensor gone silent, a revision the budget cut. Every event of a window is aggregated in
  memory to one point per measurement and tag set, beside each level as it last stood, and written
  at the window's end.

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

History, told by purpose (#825), written by the history part (`agent/history/`). The sink is
`agent/series.py`: it imports nothing of the agent, and a sink per purpose is loaded where
`INFLUX_HISTORY_URL`, `_ORG`, `_BUCKET` and `_TOKEN` are all set — none set is no sink, some set is
none too, said in the log. Where one is loaded the runtime creates the history part with the
others; linked, it hears every signal and writes the point each event answers, so no package asks
for a sink and none imports `agent.series`
([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)).

- **Sensing's** point, an `Observed` its part says as it hears an observation graph written:
  measured under the local name of the property observed, field `value`, tagged with the subject's
  and the sensor's `orexis:localId`, at the reading's `sosa:resultTime`. The dashboards ask sensing
  for the name (`measurement_of`), so a panel draws what is written. The subject's tag is still
  called `plant`, a domain word #834 renames. Points 0.1.0 wrote as `soil_moisture` stay under that
  name.
- **Execution's** points, measured `Step`: field `taken` on the `StepTaken` said when the executor
  records the [act](/domain/execution/act.md), and field `landed` on the `StepAnswered` said at the
  verdict — true where the present came to hold what the step predicted, false where the patience
  ran out or the want it was kept below as ended undone. A step predicting nothing has no verdict,
  nor has one not taken. Tagged `action`, `want` and one tag per parameter the action takes, all
  read off the step, so the executor spells no domain word. No panel draws steps yet.

Metrics, written by the metrics part (`agent/metrics/`), created where a metrics sink is loaded and
linked to every signal. Its metamodel is the one thing a package imports of it: an event's class
names its `metric` and marks its fields `Tag`, `Value`, `Flag` or `Level`. Where no metrics sink is
loaded, no metrics part hears anything, and an event only it would hear is never made.

| who | what is reported: values; flags; levels; tags beyond world and agent |
|---|---|
| the runtime | `pass`, each pass: `duration_s` and each part's seconds; levels `quads`, `uptime_s` |
| planning | `planner`, each pass: each part's seconds and the wants searched; `search`, each want each pass: `duration_s`, `budget`, `weighed`; `desire`, `scope`, `outcome`; `published`, a plan published: `passes`, `weighed`, `wall_s`, `estimate`, `cost`; `replan`; `desire`, `scope`; `reroot`, each scope each pass: `kept`, `dropped`; `scope`, `present`; `imaginarium`, each scope each pass: levels `worlds`, `weighings`, `open`, `met`, `satisfied`, `exhausted`, `no_candidate`; `scope`; `unreachable`, a want nothing reaches: `desire` |
| execution | `intention`, one ended: `outcome`, `desire`; `act`, a step taken: `taken`; `action`, `desire`; `landing`, a verdict on a step: `late_s`; `landed`, `timed_out`; `action`, `desire`; `intentions`, each walk: level `standing` |
| sensing | `received`, an observation written: `interval_s`, `cadence_s`; `sensor`; `silence`, each ask: level `silent` |
| belief | `revise`, a revision pass: `sources`, `executions`, `cut`, `duration_s`; `revisions`, after one: levels `revisions`, `unsettled` |

**A level is read where its owner looks.** The imaginaria copy the belief base's readings and its
catalogue, so a read run over every store would count one silent probe once per scope; a level is
read by the one object that holds its store — the Planner its imaginaria, the executor and the
deliberator the belief base — when it says the event.

**An event is tallied, and a window is one point.** Per measurement and tag set: `count`; for each
value `<value>_sum`, `_mean` and `_max`, always floats so no window changes a field's type; for
each flag how many raised it, nought where none did; each level as it last stood. **A want's name
is on no point**: it would be a tag of unbounded values, which breaks the store's index, and it
cannot be aggregated; the log names the want, and history carries it on a step. `world` and
`agent` are on every point — the agent's id is what the process is told, and the world's name is
the name of the directory it is handed, which the buckets, the compose project and the dashboards
already go by — and an event about a want is tagged with the `desire` it was derived under, so a
desire reads across worlds and agents.

**A window is real time, never the agent's.** The agent's clock may run fast in a simulation and
advances per read in a test, so a duration is `time.perf_counter`, the window is kept by a monotonic
clock, a flush is stamped by the wall, and nothing reads `agent.clock`. The window is sixty seconds
where the environment's `METRICS_INTERVAL_S` says nothing, and is written at the end of the first
pass by which it has run its length, so it holds whole passes; a test drives it without sleeping.
The last window is written as the metrics part stops — a `SIGTERM` is made an exit, so `podman stop` does
not lose it.

**Optional at every level.** An agent with no metrics sink computes nothing. A world is monitored
only where its own deployment graph says `onboarding:monitored`
([deployment](/domain/onboarding/deployment.md)): only then does `orexis-influx` mint each agent a
metrics bucket, `<world>-<agent>-metrics`, written to and never read by the agent and kept as many
days as the installation's `onboarding:retentionDays` says; only then does `orexis-compose` tell it
the store and the window; and only then does `orexis-dashboards` draw health, a dashboard per
package that reports and the runtime's own, linked to one another. They are learnt from the
packages' event classes themselves: a row per measurement, each panel described by its event's own
docstring, and the agent a variable choosing whose bucket every panel reads, carried from one
dashboard to the next; an event's levels are a panel per unit, its count and flags another and each
value one more. A dashboard no package reports for any more is removed. The history bucket keeps
the name the one bucket had, so a history begun before purposes goes on in it.
