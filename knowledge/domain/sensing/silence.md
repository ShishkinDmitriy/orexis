---
type: Domain Concept
title: Silence
term: http://example.org/orexis/sensing#SilenceGraph
description: >-
  A time a sensor sent nothing past the limit its observer role allows, kept by sensing from the first
  minute it is found until the sensor reads again, and then for good - what sensing knows of a sensor's
  outages, since the percepts a silence is computed from do not stay. No reader of the mind is handed one.
---

# What it is

```trig
# sensing's, written the first ask that finds the probe silent, and ended by its next reading
<…/graph/silence/terrace_agent/moisture_sensor_terrace_20261016T091841Z> {
    :moisture_sensor_terrace sensing:silentSince "2026-10-16T09:18:41Z"^^xsd:dateTime ;
                             sensing:silentUntil "2026-11-05T10:02:00Z"^^xsd:dateTime . }
```

A sensor is **silent** when its latest reading has stopped being the present - its period over, the next
due and a grace past it - and no reading has come for the `sensing:silentAfter` cadences its
[observer](/domain/sensing/observer.md) role allows. `missed` answers that each minute from what is stored:
the period of the latest [observation](/domain/sensing/observation.md), the sensor's frequency, the role's
limit.

The first ask that finds a sensor silent keeps it: one `sensing:SilenceGraph`, owned by the agent, saying
`silentSince` the instant the reading stopped being the present, its period starting there. The sensor's next
reading says `silentUntil` and ends the period, and the graph is kept. So a silence is in the log once, a
restart finding it already kept, and a sensor's outages are there to ask after once the percepts between them
are gone, kept only as deep as the stuck rule reads.

# Who reads it

Nobody in the mind. The graph is beneath `orexis:Graph` alone, so neither revision nor planning is handed one:
what the mind holds of a silent sensor is that the belief made of its last reading has ended, so it holds
nothing current of the subject. A [chat](/domain/speech/chat.md) reading `orexis:Graph` reads it, and so does
whoever asks the agent which sensors have gone quiet, and since when
([a-silence-is-kept-as-what-sensing-knows-of-its-sensor](/decisions/a-silence-is-kept-as-what-sensing-knows-of-its-sensor.md)).
