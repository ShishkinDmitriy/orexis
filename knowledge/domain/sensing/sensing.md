---
type: Service
title: Sensing
term: http://example.org/orexis/sensing#ObservationGraph
description: >-
  The translation row of the agent stack: a transport hands it an instrument's bytes, and it keeps
  the number they hold as an observation per reading - a percept, in a graph of its own, linked to
  the one before it, the latest holding until the next reading is due and a grace past it - and a
  sensor's last few, as deep as its rules read. Its rules conclude what a reading is of, its quantity
  and whether its sensor is stuck. It says when a sensor has gone silent - it predicts nothing, holds
  nothing of a subject, and names no transport. `agent/sensing/`.
---

# What it does

**`received`** is the callback a transport calls with a sensor's IRI and the bytes it read. The
pipeline makes a number of them — the codec the sensor is bound to (`sensing:decodedBy`, JSON the
member that ships) and the pointer to its value in the document (`sensing:readingPointer`, a JSON
Pointer). Each reading is one [observation](/domain/sensing/observation.md), named for its sensor and
its instant, written into a `sensing:ObservationGraph` of its own — a [percept](/domain/kernel/percept.md),
classified `orexis:Received` — and all it says is the number the sensor gave (`sensing:rawResult`), who
made it, when, and the observation its sensor made before it (`sensing:previous`). The latest holds
from its instant until the next is due by the sensor's `ssn-system:Frequency` and the observation's
grace past it, and a new one ends the one before at its own instant. Where the pointer finds an array
of readings, each with how many seconds before the message it was taken — a sentinel's alarm carries
its watcher's last quiet sample before the reading that broke the window — each is an observation of
its own in the chain, oldest first, an earlier one holding only until the next one's instant: a step
in the history, not a slope. `received` keeps a sensor's last `sensing:stuckAfter` and forgets the
oldest past them; it counts nothing and carries nothing onto the present.

**What the number is, the rules conclude** (`rules.ttl`), from the topology and what the world states
of the sensor: at layer 0 the observation's feature of interest — what the sensor is hosted by, a sample
or the subject — its property — what the sensor observes — and its quantity, the number as it is or
rescaled through the sensor's [scaling](/domain/sensing/scaling.md); at layer 1 its
[reading](/domain/sensing/reading.md), that quantity as it is or corrected through the sensor's
[calibration](/domain/sensing/calibration.md). And at layer 0, from the percepts kept, whether the
sensor is [stuck](/domain/sensing/stuck.md) on one number. A payload that
does not decode writes nothing and says so in the log. A sensor reading a SERIES - one stating
`sensing:endsPointer` or `sensing:startsPointer` beside its reading pointer - writes one
[forecast](/domain/sensing/forecast.md) per stretch still ahead instead, and replaces its last.

**`missed`** is what sensing's own `start` asks every minute of the timeline, whether or not anything
arrived ([a-package-starts-itself](/decisions/a-package-starts-itself.md)): which sensors' readings have gone missing,
their latest observation past its grace with nothing arrived, for the container to ask again, and which have been silent past the agent's limit of
their cadences (`sensing:silentAfter`) — said by `sensing:silentSince` until a reading ends it. Both limits are
[stances](/domain/kernel/stance.md), and a figure in code holds where the agent's self graph states none.

# What it leaves to others

What the rules conclude is a [revision](/domain/belief/revision.md), a percept as its source is, run by
the [deliberator](/domain/belief/deliberator.md) when the container says a graph was written. What
the agent then holds true of the observation's subject is no rule of sensing's but a domain's
[transition](/domain/belief/transition.md), triggered by the observation arriving — climate's, for
the soil and the air — which writes a subject belief. That is why an
[observer](/domain/sensing/observer.md) is a deliberator too, and belief's part, first in a pass, hears a
graph written before any other part, so sensing's own `Observed` and the prediction find it concluded. When the reading will change range is the
[prediction](/domain/prediction/prediction.md) package's. How the bytes arrived is the
[transport](/domain/transport/transport.md)'s: sensing imports nothing of one and speaks no word of
one, so the contract points one way.

# Its words

SOSA's and SSN's wherever they have one — a sensor `sosa:observes` a property and `sosa:isHostedBy`
what it is mounted in, and that pair is what its readings are of — and its own for what neither
standard says: the observation graph's kind and the forecast's, the link from an observation to the
one before it, the silence and the number a stuck sensor keeps giving, the
[margin](/domain/sensing/margin.md) a domain's transition holds a state by, the pipeline's binding and
the two pointers a series is read by, the number a sensor gave and the quantity scaled from it, and
the two-point scaling and calibration with their points.
