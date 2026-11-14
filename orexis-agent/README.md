# orexis-agent: the binary

One agent's process. It boots the world into a store, where each package the binary holds decides in its own
start whether the agent runs it, starts the task of each that joined, and runs until nothing holds the agent.

- **Each package is a Cargo feature**, so an agent's image holds only what it runs: the code and the documents
  of the packages built in, and of no other.
- **Start order:** `journal`, `journal-oxigraph`, `journal-otlp`, `metrics`, `sensing-influxdb`, then the rest.
- **It names no package's word.** It makes the series stores a deployment's environment describes and hands them
  to the tasks, says the agent is deployed, and hands the process's log to whichever package keeps it. It makes no
  journal and no archive: those packages make their own.

## Triggering events and activities

None. It hears no event and starts no activity.

## Tests

`tests/` boots whole agents on Tokio's paused time: `greenhouse.rs`, `layby.rs`, `lane.rs` and the rest are the
worlds' walks, and `tests/common/trace.rs` traces a walk being looked into.
