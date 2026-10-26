---
type: Repository
title: Journal
description: >-
  What happened to one agent, in RDF, in a triplestore of its own beside its beliefs and apart from them - every event
  its packages say, in their words, kept for good, and its log, kept for a window unless an incident keeps the minutes
  before it - served read-only over the SPARQL protocol on the host's loopback. Watched and never believed.
---

# What it is

An agent's **journal** is a pyoxigraph store of its own (`agent/journal.py`), on a volume beside the belief base's
(`--journal`), or in memory where the process is told none. It holds two kinds of entry, each a named graph holding
one node, named by a UUID's URN:

- an **event** a package says, of a class beneath `orexis:Event` in that package's ontology, at its `prov:atTime`,
  with what the agent held of what it is about — kept for good. This is the agent's history, beside the observations
  its [series](/domain/kernel/series.md) keeps.
- a **log record**, `orexis:LogRecord`, what the code said in the log — its `orexis:logger`, `orexis:level` and
  `orexis:message` — kept for the **window**, ten minutes where `JOURNAL_WINDOW_S` says nothing, and swept after.

An **incident**, `orexis:Incident`, keeps the window before it: every log record of it is kept for good beside the
incident (`orexis:keptBy`). An event is an incident where its package types it one — a step that did not land, an
intention failed, a want nothing reaches — and a log record is one at WARNING or above. So what led up to a failure
is there to read, and what led up to nothing goes.

# How it is read

The agent serves it at `http://127.0.0.1:<port>/sparql`, the SPARQL protocol's query alone: an update is refused. The
port is the installation's to allocate and the container's to be told, `JOURNAL_PORT`. Every entry is the default
graph of a query asked there, and a pattern over a node several entries copy — a step, an act — is asked within one
entry, `GRAPH ?e { … }`, or each copy answers it once more. `orexis-history` and `orexis-explain` are its readers; a
stopped agent's journal is opened read-only off its volume, which nothing then writes.

It is the agent's own word about what it did, as the series is, so no reader of the mind is handed it and nothing in
it reaches a plan ([the-journal-is-the-agents-flight-recorder](/decisions/the-journal-is-the-agents-flight-recorder.md)).
