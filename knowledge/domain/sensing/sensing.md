---
type: Service
title: Sensing
term: http://example.org/orexis/sensing#ObservationGraph
description: >-
  The translation row of the agent stack: a transport hands it an instrument's bytes, and it keeps
  the number they hold as the sensor's observation, in a graph per sensor that holds until the next
  reading is due and a grace past it; its rules conclude what that number is an observation of and what quantity it is.
  It says when a sensor has gone silent and when one is stuck on a number - it predicts nothing,
  holds nothing of a subject, and names no transport. `agent/sensing/`.
---

# What it does

**`received`** is the callback a transport calls with a sensor's IRI and the bytes it read. The
pipeline makes a number of them — the codec the sensor is bound to (`sensing:decodedBy`, JSON the
member that ships) and the pointer to its value in the document (`sensing:readingPointer`, a JSON
Pointer). One [observation](/domain/sensing/observation.md) is written into the sensor's graph, an
`sensing:ObservationGraph` beneath `orexis:StateGraph`, classified `orexis:Received` and holding
from its instant until the next is due by the sensor's `ssn-system:Frequency` and the
[observation](/domain/sensing/observation.md)'s grace past it — and all it says is
the number the sensor gave (`sensing:rawResult`), who made it and when, and since when the number has been
that one - the run a sensor is said [stuck](/domain/sensing/stuck.md) from, once it has lasted the agent's
limit of the sensor's cadences (`sensing:stuckAfter`), by `sensing:stuckSince` until a differing number ends it. Where the pointer finds an array of readings,
each with how many seconds before the message it was taken — a sentinel's alarm carries its watcher's
last quiet sample before the reading that broke the window — each is an observation of its own, an
earlier one holding only until the next one's instant: a step in the history, not a slope.

**What the number is, the rules conclude** (`rules.ttl`), from the topology and what the world states
of the sensor: at layer 0 the observation's feature of interest — what the sensor is hosted by, a sample
or the subject — its property — what the sensor observes — and its quantity, the number as it is or
rescaled through the sensor's [scaling](/domain/sensing/scaling.md); at layer 1 its
[reading](/domain/sensing/reading.md), that quantity as it is or corrected through the sensor's
[calibration](/domain/sensing/calibration.md). A payload that
does not decode writes nothing and says so in the log. A sensor reading a SERIES - one stating
`sensing:endsPointer` or `sensing:startsPointer` beside its reading pointer - writes one
[forecast](/domain/sensing/forecast.md) per stretch still ahead instead, and replaces its last.

**`missed`** is what sensing's own `start` asks every minute of the timeline, whether or not anything
arrived ([a-package-starts-itself](/decisions/a-package-starts-itself.md)): which sensors' readings have gone missing,
past their grace with nothing arrived, for the container to ask again, and which have been silent past the agent's limit of
their cadences (`sensing:silentAfter`) — said by `sensing:silentSince` until a reading ends it. Both limits are
[stances](/domain/kernel/stance.md), and a figure in code holds where the agent's self graph states none.

# What it leaves to others

What the rules conclude is a [revision](/domain/belief/revision.md), run by the
[deliberator](/domain/belief/deliberator.md) when the container says a graph changed: layers 0 and 1
what an observation is of and its reading, layer 2 which side of a [region](/domain/sensing/region.md) the
reading is on — `sensing:below`, `sensing:inside` or `sensing:above`. What the agent then holds true
of the observation's subject is no rule of sensing's but a domain's
[transition](/domain/belief/transition.md), triggered by the observation arriving — climate's, for
the soil and the air — which writes a subject belief. That is why an
[observer](/domain/sensing/observer.md) is a deliberator too, and belief's part, first in a pass, hears a
graph written before any other part, so sensing's own `Observed` and the prediction find it concluded. When the reading will change range is the
[prediction](/domain/prediction/prediction.md) package's. How the bytes arrived is the
[transport](/domain/transport/transport.md)'s: sensing imports nothing of one and speaks no word of
one, so the contract points one way.

# Its words

SOSA's and SSN's wherever they have one — a sensor `sosa:observes` a property and
`sosa:isHostedBy` what it is mounted in, and that pair is the key — and its own for what neither
standard says: the observation graph's kind and the forecast's, the silence, the three sides, the
[margin](/domain/sensing/margin.md) a domain's transition holds a state by, the
pipeline's binding and the two pointers a series is read by, the number a sensor gave and the quantity
scaled from it, and the two-point scaling and calibration with their points.
