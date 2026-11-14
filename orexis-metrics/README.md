# orexis-metrics

The admins' instrumentation: every event tallied in memory and written to the metrics bucket once a window.
Code, not model: no agent believes a metric.

- **Loaded for:** no role. It has a task only where the deployment hands it a metrics sink.
- **Words:** none. It reads an event only through its marks (`orexis::events`).

## What starts it

| Woken by | Does |
|---|---|
| any event said | adds it to the window's tally for its measurement and tags: a count, each value's sum, mean and max, each flag's count; a level is kept as it last stood |
| the clock: real time, every `METRICS_INTERVAL_S` (60 s) | writes the tallies and the levels, each point tagged with the world and the agent |
| the task stopping | writes the window |

It starts no activity.
