---
type: Domain Concept
title: Tracer
term: http://example.org/orexis/journal#Tracer
description: >-
  A service the world is connected to that takes an agent's activities as spans, OTLP over HTTP at its url. A
  recorder's role names it, the world's deployment graph says where it answers, and what ships the journal's
  activities finds it there as it starts; a recorder whose role names none is traced by nobody.
---

# What it is

Where an agent's [activities](/domain/kernel/activity.md) go to be drawn as traces: Tempo today. A tracer is a node
of the world's derived [deployment](/domain/onboarding/deployment.md) graph, `a journal:Tracer` with a `schema:url`,
written there by onboarding for each tracer a recorder's role names.

# Who is traced

A recorder whose role says so in the agent's self graph, `journal:tracedBy` naming the tracer. The author names the
node and no address; onboarding gives it the url of the installation's tracer, and refuses a world that names one
where the installation names none.

```turtle
:grower orexis:plays [ a journal:Recorder ; journal:tracedBy :tracer ] .
```

# Who reads it

`orexis-journal-otlp/`, the housekeeper that ships what the [journal](/domain/kernel/journal.md) holds of the
activities. As it starts it asks the store for the tracer its role names. Where the agent plays a
[recorder](/domain/journal/recorder.md) whose role names one and the world says where it answers, it joins, takes
the journal and posts to `/v1/traces` beneath the url every ten of the agent's seconds. Where the role names none,
its start ends, and the activities stay in the journal for its window.

Why the world says it and no environment does is
[the-world-says-what-it-is-connected-to](/decisions/the-world-says-what-it-is-connected-to.md).
