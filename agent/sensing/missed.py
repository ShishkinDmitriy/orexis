"""`missed`: which sensors have gone silent at an instant — asked every minute of the timeline by
sensing's own `start`, which the runtime waits for.

**A READING IS MISSING WHEN THE LATEST PERCEPT'S PERIOD HAS ENDED.** The percept `received` writes
holds from its instant until the next is due by the sensor's `ssn-system:Frequency` and a grace past
it (`received.GRACE`), or until the next arrives, so the period of the LATEST — the percept no percept
names as its previous — ending IS the reading going missing — later than due, since a reading a little
late is not missing (#870): a reader asking at a later instant is handed no percept of the sensor,
which is what unmeasured is, and no belief a transition made of it either, which holds over the
percept's period. An older percept's period ended when its successor arrived, and says nothing missed
(#944). Which sensors are in that state is `cadence.lapsed`, the one read of it, which the MQTT member
asks too, to nudge a board.

**A SENSOR SILENT PAST THE LIMIT IS ANSWERED, AND NOTHING IS WRITTEN.** One whose reading has been
missing for `sensing:silentAfter` cadences and more — the limit the observer role reading it states,
the observer shape's default where it states none (`cadence.limit_of`) — is silent since the instant
its latest percept ended. Every premise of that is stored — the percept's period, the sensor's
cadence, the role's limit — so the silence is computed, never asserted: kept, it was a second record
of what the period's end already says, a graph the next reading had to find and take back, and a fact
nothing in the mind reads, since the belief made of the percept ended with it. The container says a
silence in the log and the series (`create`); SOSA and SSN say how often a sensor reports and nothing
about one that has stopped, so silent is one of sensing's own words, and a word for eyes.

**A SENSOR THAT HAS NEVER REPORTED IS NOT HERE.** Its absence is, in the store, the same as
a sensor not yet due; that fault is the container's to count from boot, and is the seam this
leaves open — as is the sweep: this reads the ended percept's row off the catalogue, so an upkeep
that dropped ended graphs would have to leave a sensor's latest percept standing. None does: a
percept is forgotten by `received` alone, past the depth sensing keeps, and never the latest.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .cadence import cadence_of, lapsed, limit_of
from .ontology import SILENT_AFTER_TERM


def missed(store, now: datetime, *, memo=None) -> list[tuple[str, datetime]]:
    """The sensors silent at `now` — the latest percept ended (`cadence.lapsed`) and the limit of
    cadences the observer role reading it allows gone since — each with the instant it fell silent,
    the latest percept's end, earliest first. A sensor stating no frequency is never silent: the world
    made no promise its absence could break. Writes nothing."""
    out: list[tuple[str, datetime]] = []
    for sensor, since in lapsed(store, now, memo):
        if any(sensor == s for s, _ in out):
            continue
        cadence = cadence_of(store, sensor, memo)
        limit = limit_of(store, sensor, SILENT_AFTER_TERM, memo)
        if cadence is not None and now >= since + timedelta(seconds=limit * cadence):
            out.append((sensor, since))
    return out
