# orexis-journal

The agent's journal: what happened, kept in memory as it is said. Every event that states triples is one entry in
its package's words, and every activity is one entry as it ends, in PROV's words, with what started it and what
it generated.

- **Loaded for:** `journal:Recorder`. An agent that plays none says what happens and nobody writes it down.
- **Words:** `ontology.ttl` (`journal:`). **Dictionary:** `knowledge/domain/kernel/journal.md`,
  `knowledge/domain/journal/`.
- **Its housekeepers:** `orexis-journal-oxigraph/` takes what lasts to the archive on disk;
  `orexis-journal-otlp/` ships the activities as spans.

## What starts it

It has no task and no trigger. It watches the events: **every** event any package says and every activity any
package ends is written as it is said. It knows no package's words.

## What it keeps, and how long

| Entry | Kept |
|---|---|
| an event | until the archive takes it; for good there |
| a log record, an activity | for the journal's window, then swept |
| a log record or an activity an incident kept (`orexis:keptBy`) | until the archive takes it; for good there |

An incident is an event of a class beneath `orexis:Incident`. Kept, it wakes the archive at once.

## Asking it

`/live/sparql` on the agent's journal port, loopback only. What caused what is a query: an activity started by
what another generated (`prov:wasGeneratedBy`) was caused by it.
