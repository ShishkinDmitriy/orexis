# orexis-metrics

The admins' instrumentation: every event tallied in memory and written to the metrics bucket once a window.
Code, not model: no agent believes a metric.

- **Loaded for:** `metrics:Meter`. It makes its own sink from the store the role names (`metrics:writtenTo`), as
  the world's deployment states it, and the agent's metrics credential, where the agent is deployed.
- **Words:** `ontology.ttl` (`metrics:`). **Dictionary:** `knowledge/domain/metrics/meter.md`.
- It reads an event only through its marks (`orexis::events`), so it knows no package's words.

## What starts it

| Woken by | Does |
|---|---|
| any event said | adds it to the window's tally for its measurement and tags: a count, each value's sum, mean and max, each flag's count; a level is kept as it last stood |
| the clock: real time, every window the world states of `orexis:Metrics` (60 s where it states none) | writes the tallies and the levels, each point tagged with the world and the agent |
| the task stopping | writes the window |

It starts no activity.
