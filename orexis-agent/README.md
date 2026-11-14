# orexis-agent: the binary

One agent's process. It boots the world into a store, reads the roles the self graph says the agent plays,
starts the task of each package those roles load, and runs until nothing holds the agent.

- **Each package is a Cargo feature**, so an agent's image holds only what it runs: the code and the documents
  of the packages built in, and of no other.
- **Start order:** `journal`, `journal-oxigraph`, `journal-otlp`, `metrics`, `sensing-influxdb`, then the rest.
- **It names no package's word.** It makes the connectors a deployment's environment describes (a broker session,
  a series store, the journal's archive, the model's client) and hands them to the tasks.

## Triggering events and activities

None. It hears no event and starts no activity. It serves the journal read-only on the host's loopback:
`/sparql` answers from the archive and `/live/sparql` from the journal.

## Tests

`tests/` boots whole agents on Tokio's paused time: `greenhouse.rs`, `layby.rs`, `lane.rs` and the rest are the
worlds' walks, and `tests/common/trace.rs` traces a walk being looked into.
