---
type: Domain Concept
title: Endpoint
term: http://example.org/orexis/journal#Endpoint
description: >-
  Where a recorder's journal answers SPARQL read-only, on the host's loopback. The recorder's role names it, the
  installation allocates its port, and the journal package serves there as it starts; a role naming none is
  served nowhere.
---

# What it is

The address a running agent's [journal](/domain/kernel/journal.md) is asked at: `/sparql` for the past and
`/live/sparql` for the journal itself, queries alone. An endpoint is a node of the world's derived
[deployment](/domain/onboarding/deployment.md) graph, `a journal:Endpoint` with a `schema:url` on the loopback.

# Who is served

The agent whose recorder role names one, `journal:servedAt`. The port is unique across the host, so the
installation allocates it per agent and no author states it; onboarding copies the allocated url onto the node the
role names.

```turtle
:grower orexis:plays [ a journal:Recorder ; journal:servedAt :grower_endpoint ] .
```

# Who reads it

`orexis-journal/`, as it makes its journal in a deployed agent: it listens on the url's port. `orexis-history` and
`orexis-explain` ask the same url, which they read off the installation's allocation.
