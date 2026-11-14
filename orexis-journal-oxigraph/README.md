# orexis-journal-oxigraph

The journal's archive: a housekeeper of `orexis-journal/`. It takes what the journal keeps for good into a
triplestore on the agent's volume, and has the journal forget what it took.

- **Loaded for:** `journal:Recorder`, where the role names an archive (`journal:archivedIn`): it asks the world's
  deployment graph where that `journal:Archive` is as it starts, and ends its start where the role names none.
- **Words:** none. **Dictionary:** `knowledge/domain/journal/archive.md`.

## What starts it

| Woken by | Does |
|---|---|
| the clock, every `JOURNAL_ARCHIVE_INTERVAL_S` of the agent's time (2 s), where anything was written | takes every event, and every log record and activity an incident kept |
| an incident kept by the journal | takes at once |
| the run ending | takes once more, then flushes |

It hears no event and starts no activity. An agent killed outright loses two seconds at most.

## Asking it

`/sparql` on the agent's journal port; a chat's journal tool reads it too; a stopped agent's archive is opened
read-only.
