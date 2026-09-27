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

History's observations alone: the runtime hands the sink each observation graph sensing wrote
(`agent/series.py`), and each point is measured under the local name of the property it observes,
field `value`, tagged with the subject's and the sensor's `orexis:localId`. The dashboards ask the
sink for the name (`measurement_of`) rather than spelling one, so a panel draws what is written.
Points 0.1.0's shape wrote, every property as `soil_moisture`, stay under that name in a bucket
that had them. The purposes, the contributions and the metrics are decided in
[a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md) and not
yet built (#825, #826).
