---
type: Domain Concept
title: Tracer
term: http://example.org/orexis/journal#Tracer
description: >-
  A service the world is connected to that takes an agent's activities as spans, OTLP over HTTP at its url. Stated
  in the world's deployment graph, where what ships the journal's activities finds it as it starts; a world that
  names none is traced by nobody.
---

# What it is

Where an agent's [activities](/domain/kernel/activity.md) go to be drawn as traces: Tempo today. A tracer is a node
of the world's derived [deployment](/domain/onboarding/deployment.md) graph, `a journal:Tracer` with a `schema:url`,
written there by onboarding for a monitored world of an installation that names one.

# Who reads it

`orexis-journal-otlp/`, the housekeeper that ships what the [journal](/domain/kernel/journal.md) holds of the
activities. As it starts it asks the store for a tracer. Where the agent plays a
[recorder](/domain/journal/recorder.md) and the world names one, it joins, takes the journal and posts to
`/v1/traces` beneath the url every ten of the agent's seconds. Where the world names none, its start ends, and the
activities stay in the journal for its window.

Why the world says it and no environment does is
[the-world-says-what-it-is-connected-to](/decisions/the-world-says-what-it-is-connected-to.md).
