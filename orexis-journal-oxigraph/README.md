# orexis-journal-oxigraph

The journal's archive: a housekeeper of `orexis-journal/`. It takes what the journal keeps for good into a
triplestore on the agent's volume, and has the journal forget what it took.

- **Loaded for:** `journal:Recorder`, where the role names an archive (`journal:archivedIn`): it asks the world's
  deployment graph where that `journal:Archive` is as it starts, and ends its start where the role names none.
- **It opens its own archive** at the path the world states, where the agent is deployed, and takes once more after
  every task has ended. A test hands it one instead.
- **Words:** none. **Dictionary:** `knowledge/domain/journal/archive.md`.

## What starts it

| Woken by | Does |
|---|---|
| the clock, as often as the recorder's role says (`journal:archivedEveryS`), every 2 s of the agent's time where it says nothing, where anything was written | takes every event, and every line logged and activity an incident kept |
| an incident kept by the journal | takes at once |
| the run ending | takes once more, then flushes |

It hears no event and starts no activity. An agent killed outright loses two seconds at most.

## Asking it

`/sparql` on the agent's journal port; a chat's journal tool reads it too; a stopped agent's archive is opened
read-only.
