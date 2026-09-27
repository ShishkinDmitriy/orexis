---
type: Repository
title: Series
description: >-
  What a person watches of an agent and the agent never reads - its history, what happened, and
  its metrics, how it is doing - each written by a sink that knows nothing of what it writes, to
  a store the agent is told of by purpose.
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
- **Metrics** — how the agent is doing, figure by figure, each pass. Most of these are rows a
  package already writes — a search the budget cut short, an intention that failed, a sensor gone
  silent, a revision the budget cut — so a package ships a select over its own rows, and every
  such select is found by its graph's kind and run at the end of each pass; no registry lists
  them. How long a pass took, how large the store is and how long the process has run are the
  runtime's own.

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

Metrics, as selects each package ships (#826). A package's `metrics.ttl` is a graph of kind
`orexis:MetricGraph`, beneath `orexis:Graph` alone — neither public nor a belief, so no rule reads it
and no possible world is filled with it — and it is read where the package is loaded, so an agent
without sensing counts no silence. Each `orexis:Metric` in it is an `sh:select` and says the
repository it is run `orexis:over`: the belief base, the [imaginarium](/domain/planning/imaginarium.md)
or the intentions store. `agent/metrics.py` finds every metric by the kind, runs each over the
stores the runtime hands it for that repository, sums each column across them, and writes a point
measured under the metric's local name; the runtime adds its own, `pass`. What ships:

| package | metric | over | fields |
|---|---|---|---|
| planning | `plans` | imaginaria | `satisfied`, `exhausted`, `noCandidate` — the plans held, by outcome |
| planning | `cone` | imaginaria | `worlds`, `weighings`, `open`, `met` — the kept [cone](/domain/planning/cone.md) |
| execution | `intentions` | intentions store | `standing`, `done`, `failed`, `superseded`, `abandoned` |
| execution | `acts` | intentions store | `taken`, `notTaken` |
| sensing | `silence` | belief base | `silent` — sensors said silent now |
| belief | `revisions` | belief base | `revisions`, `unsettled` — cut short by the budget |
| the runtime | `pass` | — | `duration_s` and `uptime_s` in real seconds, `quads` in the belief base |

A figure is a count, since only a count sums across the imaginaria, and a figure is what the stores
HOLD after the pass rather than what the pass added: a kept cone is counted again, and the
intentions store is made at the process's start. A metric saying no repository is not defaulted to
the belief base — the imaginaria copy its readings, so a select run everywhere counts one silence per
scope.

`orexis-influx` mints `secrets/influx-<purpose>-<agent>.env` for each purpose, saying the bucket and
token under it, and `orexis-compose` mounts both beside the url and organisation of the store the
installation says `onboarding:serves` the purpose ([deployment](/domain/onboarding/deployment.md)).
The history bucket keeps the name the one bucket had, so a history begun before purposes goes on
in it; the metrics bucket is `<world>-<agent>-metrics`, written to and never read by the agent,
and kept as many days as the installation's `onboarding:retentionDays` says. `orexis-dashboards`
draws a health dashboard per world from it, a panel per metric the agent's own boot declares.
