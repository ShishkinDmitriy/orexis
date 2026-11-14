---
type: Role
title: Meter
term: http://example.org/orexis/metrics#Meter
description: >-
  An agent that measures how it is doing, for whoever administers it - the role whose package is `orexis-metrics/`.
  Where the self graph declares it, what the agent's packages' events report is tallied in a window and written
  once a window to the series store the role names; where it declares none, nothing is tallied.
---

# Who plays it

An agent is a **meter** where its self graph says it [plays](/domain/kernel/role.md) a `metrics:Meter`, and
`orexis-metrics/` joins the agent for that and for nothing else. The terrace's agent and the greenhouse's grower
play it. Until 2026-11-14 the package joined every agent and a statement of the world's deployment said which
worlds were written; it was the one package loaded for no role.

```turtle
:grower orexis:plays [ a metrics:Meter ; metrics:writtenTo :series ] .
```

# What it does

It hears every [event](/domain/kernel/event.md) the agent's packages say and tallies the ones that report, in a
window of real time, then writes the window to the metrics [series](/domain/kernel/series.md). It reads an event
only through its marks, so it knows no package's words, and no agent believes a metric.

# What the role says

`metrics:writtenTo` names the series store. The author names a node and no address; the world's derived
[deployment](/domain/onboarding/deployment.md) says where it answers and that it serves `orexis:Metrics`. A meter naming no store is refused at onboarding.

`metrics:windowS` says how many seconds of real time a window covers, sixty where the role states none. Until
2026-11-14 the installation stated it for every world at once.

# What follows from it at onboarding

A world is monitored where an agent of it plays a meter. Onboarding then mints each agent a metrics bucket with a
token of its own, mounts that credential into the meter's container, and draws the world's health dashboards.
