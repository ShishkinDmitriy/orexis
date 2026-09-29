---
type: Service
title: Sensing
term: http://example.org/orexis/sensing#ObservationGraph
description: >-
  The translation row of the agent stack: a transport hands it an instrument's bytes, and it makes
  one `sosa:Observation` of them, in a graph per key that holds until the next reading is due. It
  says when a sensor has gone silent, and nothing more - it predicts nothing, concludes nothing
  and names no transport. `agent/sensing/`.
---

# What it does

**`received`** is the callback a transport calls with a sensor's IRI and the bytes it read. The
pipeline makes a number of them — the codec the sensor is bound to (`sensing:decodedBy`, JSON the
member that ships), the pointer to its value in the document (`sensing:readingPointer`, a JSON
Pointer), and the scaling (`sensing:scaledBy`, identity where nothing says otherwise). One
[observation](/domain/sensing/observation.md) is written into the graph of that key, an
`sensing:ObservationGraph` beneath `orexis:StateGraph`, classified `orexis:Received` and holding
from its instant until the next is due by the sensor's `ssn-system:Frequency`. A payload that
does not decode writes nothing and says so in the log. A sensor reading a SERIES - one stating
`sensing:endsPointer` or `sensing:startsPointer` beside its reading pointer - writes one
[forecast](/domain/sensing/forecast.md) per stretch still ahead instead, and replaces its last.

**`missed`** is what sensing's own `start` asks every minute of the timeline, whether or not anything
arrived ([a-package-starts-itself](/decisions/a-package-starts-itself.md)): which sensors' readings have fallen due with
nothing arrived, for the container to ask again, and which have been silent past a limit of their
cadences — said by `sensing:silentSince` until a reading ends it.

# What it leaves to others

Which side of a [region](/domain/sensing/region.md) a reading is on is a
[revision](/domain/belief/revision.md): the three rules sensing ships in `rules.ttl` conclude
`sensing:below`, `sensing:inside` or `sensing:above`, and the [deliberator](/domain/belief/deliberator.md)
runs them when the container says a graph changed. When the reading will change range is the
[prediction](/domain/prediction/prediction.md) package's. How the bytes arrived is the
[transport](/domain/transport/transport.md)'s: sensing imports nothing of one and speaks no word of
one, so the contract points one way.

# Its words

SOSA's and SSN's wherever they have one — a sensor `sosa:observes` a property and
`sosa:isHostedBy` what it is mounted in, and that pair is the key — and its own for what neither
standard says: the observation graph's kind and the forecast's, the silence, the three sides, the
pipeline's binding and the two pointers a series is read by.
