---
type: Repository
title: Archive
description: >-
  Where a recorder's journal puts what it keeps for good - a triplestore on the agent's own volume, written on a
  timer by `orexis-journal-oxigraph/` and read by everyone who asks what happened. The journal in memory is the hot
  record and the archive the cold one.
---

# What it is

A [recorder](/domain/journal/recorder.md)'s **archive** is a triplestore on a volume of the agent's own (`--journal`),
holding what its [journal](/domain/kernel/journal.md) kept for good: each event, and each log record and activity an
incident kept. An entry is the same named graph in both, so one text reads either.

The journal is in memory, and is where a thing is written as it is said. `orexis-journal-oxigraph/` takes what lasts
out of it into the archive, and has the journal forget what was taken:

- **when**: every two of the agent's seconds where anything was written (`JOURNAL_ARCHIVE_INTERVAL_S` says
  otherwise), at once when an incident is kept, and a last time as the run ends;
- **an event** is forgotten by the journal as soon as the archive has it;
- **a log record or an activity an incident kept** stays in the journal too until the window has passed it, since a
  later incident keeps it again and `orexis-journal-otlp/` reads the activities there; one that changes after it was
  taken is taken again, whole;
- **a log record or an activity no incident kept** never reaches the archive: the journal sweeps it.

# What it costs

An agent killed outright loses what it said since the archive last took anything, two seconds at most. One that
stops loses nothing. A reader of the archive is as far behind the journal.

# Who reads it

Whoever asks about the past: the endpoint's `/sparql`, a chat's journal tool, and `orexis-history` and
`orexis-explain` opening a stopped agent's volume. The journal itself answers at `/live/sparql`, for the log and the
activities of the window. An agent told no `--journal` has no archive: what lasts stays in its journal, and both
paths answer from there.

An archive opened over what an earlier journal wrote straight to the volume is tidied first of the log and the
activities no incident kept.
