---
type: Service
title: Sensing
term: http://example.org/orexis/sensing#ObservationGraph
description: >-
  The translation row of the agent stack: an instrument's bytes reach it through a transport, and it keeps
  the number they hold as an observation per reading - a percept, in a graph of its own, linked to
  the one before it, the latest holding until the next reading is due and a grace past it - and a
  sensor's last few, as deep as its rules read. Its rules conclude what a reading is of, its quantity
  and whether its sensor is stuck. It says when a sensor has gone silent - it predicts nothing, holds
  nothing of a subject, and names no transport. `orexis-sensing/`.
---

# What it does

**`received`** is handed a sensor's IRI and the bytes it read. A sensor a member of the agent's answers when asked
(`orexis_transport::Exchange::Requested`, the web's) sensing ASKS, on the sensor's `ssn-system:Frequency` or once
where it states none, and hands the answer to `received` itself: polling is a request in a loop, and the loop is
sensing's, since the cadence is
([the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop](/decisions/the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop.md));
asking keeps the agent running. A sensor whose readings arrive of their own accord, one on a topic
(`Exchange::Listened`), sensing LISTENS to through the member that reaches it, and hands each message to `received`
the same way, every sensor of one message in one turn. The
pipeline makes a number of them — the codec the sensor is bound to (`sensing:decodedBy`, JSON the
member that ships) and the pointer to its value in the document (`sensing:readingPointer`, a JSON
Pointer). Each reading is one [observation](/domain/sensing/observation.md), named for its sensor and
its instant, written into a `sensing:ObservationGraph` of its own — a [percept](/domain/sensing/observation.md),
classified `orexis:Received` — and all it says is the number the sensor gave (`sensing:rawResult`), who
made it, when, and the observation its sensor made before it (`sensing:previous`). The latest holds
from its instant until the next is due by the sensor's `ssn-system:Frequency` and the observation's
grace past it, and a new one ends the one before at its own instant. Where the pointer finds an array
of readings, each with how many seconds before the message it was taken — a sentinel's alarm carries
its watcher's last quiet sample before the reading that broke the window — each is an observation of
its own in the chain, oldest first, an earlier one holding only until the next one's instant: a step
in the history, not a slope. `received` keeps a sensor's last `sensing:stuckAfter` in the kind its rules read and files the
oldest past them as [past](/domain/sensing/observation.md); it counts nothing and carries nothing onto the present.

**What the number is, the rules conclude** (`rules.ttl`), from the topology and what the world states
of the sensor: at layer 0 the observation's feature of interest — what the sensor is hosted by, a sample
or the subject — its property — what the sensor observes — and its quantity, the number as it is or
rescaled through the sensor's [scaling](/domain/sensing/scaling.md); at layer 1 its
[reading](/domain/sensing/reading.md), that quantity as it is or corrected through the sensor's
[calibration](/domain/sensing/calibration.md). And at layer 0, from the percepts kept, whether the
sensor is [stuck](/domain/sensing/stuck.md) on one number. A payload that
does not decode writes nothing and says so in the log. A sensor reading a SERIES - one stating
`sensing:endsPointer` or `sensing:startsPointer` beside its reading pointer - writes one
[forecast](/domain/kernel/forecast.md) per stretch still ahead instead, and replaces its last.

**`missed`** is what sensing's own `start` asks every minute of the timeline, whether or not anything
arrived ([a-package-starts-itself](/decisions/a-package-starts-itself.md)): which sensors have been silent past their
limit of cadences (`sensing:silentAfter`) since their latest observation's period ended, until a reading ends
it. A silence is computed at each ask, and the first ask that finds one keeps it as a
[silence](/domain/sensing/silence.md), which a reading ends. Sensing says it in the log and the series. Both limits are the [observer](/domain/sensing/observer.md)
role's that reads the sensor, and the observer shape's default holds where it states none.

# What it does for as long as it runs

Of each sensor it attends, one [activity](/domain/kernel/activity.md) inside its running: a
**listening** (`sensing:Listening`) where the sensor's readings arrive of their own accord, an
**asking** (`sensing:Asking`) where a member answers when asked and sensing asks on the sensor's
cadence. Each names its sensor (`prov:used`). Taking in one message is a **perceiving**
(`sensing:Perceiving`), part of the listening or the asking of the sensor the message is of, and the
percepts written are what it generated; `sensing:Perceived` is said once for the messages one turn
took in, within the last one's perceiving, so the revision that follows is traced through it to the sensor and from there to the
agent's start.

# What it leaves to others

What the rules conclude is a [revision](/domain/belief/revision.md), a percept as its source is, run by
the [deliberator](/domain/belief/deliberator.md) when the container says a graph was written. What
the agent then holds true of the observation's subject is no rule of sensing's but a domain's
[transition](/domain/belief/transition.md), triggered by the observation arriving — climate's, for
the soil and the air — which writes a subject belief. That is why an
[observer](/domain/sensing/observer.md) is a deliberator too: sensing says the percepts one message wrote
perceived together, belief revises them together and says so once, and sensing's own `Observed` and the
prediction, hearing that, find the whole message concluded. When the reading will change range is the
[prediction](/domain/prediction/prediction.md) package's. How the bytes arrived is the
[transport](/domain/transport/transport.md)'s: sensing imports nothing of one and speaks no word of
one, so the contract points one way.

# Its words

SOSA's and SSN's wherever they have one — a sensor `sosa:observes` a property and `sosa:isHostedBy`
what it is mounted in, and that pair is what its readings are of — and its own for what neither
standard says: the observation graph's kind, the link from an observation to the
one before it, the limits a sensor is doubted past and the number a stuck sensor keeps giving, the
[margin](/domain/sensing/margin.md) a domain's transition holds a state by, the pipeline's binding and
the two pointers a series is read by, the number a sensor gave and the quantity scaled from it, and
the two-point scaling and calibration with their points.
