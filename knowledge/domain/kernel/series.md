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
  silent, a revision the budget cut — so a package ships a select over its own rows, and the
  metrics sink runs every such select it finds by kind, each pass; no registry lists them. How
  long a pass took, how large the store is and how long the process has run are the runtime's own.

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

`orexis-influx` mints `secrets/influx-history-<agent>.env` saying the bucket and token under the
purpose, and `orexis-compose` mounts it beside the url and organisation of the installation's one
series store. The history bucket keeps the name the one bucket had, so a history begun before
purposes goes on in it. Metrics are #826; the installation states one store until a second purpose
is written.
