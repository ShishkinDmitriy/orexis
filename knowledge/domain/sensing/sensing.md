---
type: Service
title: Sensing
term: http://example.org/orexis/sensing#ObservationGraph
description: >-
  The translation row of the agent stack: a transport hands it an instrument's bytes, and it keeps
  the number they hold as the sensor's observation, in a graph per sensor that holds until the next
  reading is due; its rules conclude what that number is an observation of and what quantity it is.
  It says when a sensor has gone silent - it predicts nothing and names no transport. `agent/sensing/`.
---

# What it does

**`received`** is the callback a transport calls with a sensor's IRI and the bytes it read. The
pipeline makes a number of them — the codec the sensor is bound to (`sensing:decodedBy`, JSON the
member that ships) and the pointer to its value in the document (`sensing:readingPointer`, a JSON
Pointer). One [observation](/domain/sensing/observation.md) is written into the sensor's graph, an
`sensing:ObservationGraph` beneath `orexis:StateGraph`, classified `orexis:Received` and holding
from its instant until the next is due by the sensor's `ssn-system:Frequency` — and all it says is
the number the sensor gave (`sensing:rawResult`), who made it and when.

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
arrived ([a-package-starts-itself](/decisions/a-package-starts-itself.md)): which sensors' readings have fallen due with
nothing arrived, for the container to ask again, and which have been silent past a limit of their
cadences — said by `sensing:silentSince` until a reading ends it.

# What it leaves to others

What the rules conclude is a [revision](/domain/belief/revision.md), run by the
[deliberator](/domain/belief/deliberator.md) when the container says a graph changed: layers 0 and 1
what an observation is of and its reading, layer 2 which side of a [region](/domain/sensing/region.md) the
reading is on — `sensing:below`, `sensing:inside` or `sensing:above`. Belief's part hears a graph written before
any package beyond the mind, so sensing's own `Observed` and the prediction find it concluded. When the reading will change range is the
[prediction](/domain/prediction/prediction.md) package's. How the bytes arrived is the
[transport](/domain/transport/transport.md)'s: sensing imports nothing of one and speaks no word of
one, so the contract points one way.

# Its words

SOSA's and SSN's wherever they have one — a sensor `sosa:observes` a property and
`sosa:isHostedBy` what it is mounted in, and that pair is the key — and its own for what neither
standard says: the observation graph's kind and the forecast's, the silence, the three sides, the
pipeline's binding and the two pointers a series is read by, the number a sensor gave and the quantity
scaled from it, and the two-point scaling and calibration with their points.
