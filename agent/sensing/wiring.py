"""My sensors, from the world — what the pipeline and the acts need to know of each, and not
one word of how it is reached.

A sensor is what the agent polls; it monitors a subject, observes a property, may sample a
patch of the subject, belongs to a device that keeps the clock, and states how its bytes are
decoded, which value of the document is its own, how the raw value is scaled and in what unit.
The device it belongs to is reached through SSN's own word, `ssn:hasSubSystem`; the 0.1.0
wiring reached it through the stream the two shared, which was the transport's word in
sensing's query, and the one thing this file exists to be without.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.ontology import PUBLIC
from agent.store import Raw, graphs_of, rows

from .ontology import DECODED_BY, QUANTITY_UNIT, SCALED_BY


@dataclass(frozen=True)
class Sensor:
    """A device an agent may read, and what its bytes mean — never where they come from."""

    uri: str
    subject: str            # what it monitors
    observes: str           # the property it reads
    sample: str | None = None      # the patch it sits in, a sosa:Sample of the subject (#98)
    sense_mode: str | None = None  # who holds the clock, the device's word
    decoded_by: str | None = None  # codec:decodedBy
    pointer: str | None = None     # sensing:readingPointer
    scaled_by: str | None = None   # scaling:scaledBy
    unit: str | None = None        # scaling:quantityUnit

    @property
    def feature(self) -> str:
        """What its observations are OF: the patch where it states one, else the subject."""
        return self.sample or self.subject


_SENSORS_Q = """
SELECT ?sensor ?subject ?observes ?sample ?senseMode ?decodedBy ?pointer ?scaledBy ?unit WHERE {
  $me sensing:polls ?sensor .
  ?sensor sensing:monitors ?subject ; sosa:observes ?observes .
  OPTIONAL { ?sensor sensing:samples ?sample }
  OPTIONAL { ?device ssn:hasSubSystem ?sensor ; sensing:senseMode ?senseMode }
  OPTIONAL { ?sensor $decodedBy ?decodedBy }
  OPTIONAL { ?sensor sensing:readingPointer ?pointer }
  OPTIONAL { ?sensor $scaledBy ?scaledBy }
  OPTIONAL { ?sensor $unit ?unit } }
ORDER BY ?sensor"""


def sensors_of(store, me: str) -> tuple[Sensor, ...]:
    """Every sensor `me` polls, with everything the pipeline needs to read it, off public
    knowledge. The two families' predicates are spliced as terms, since their prefixes are
    the codec and scaling packages' and no file of this layer declares them."""
    found = rows(store, _SENSORS_Q, graphs_of(store, PUBLIC), me=me,
                 decodedBy=Raw(f"<{DECODED_BY}>"), scaledBy=Raw(f"<{SCALED_BY}>"), unit=Raw(f"<{QUANTITY_UNIT}>"))
    return tuple(Sensor(uri=r["sensor"], subject=r["subject"], observes=r["observes"],
                        sample=r.get("sample"), sense_mode=r.get("senseMode"),
                        decoded_by=r.get("decodedBy"), pointer=r.get("pointer"),
                        scaled_by=r.get("scaledBy"), unit=r.get("unit")) for r in found)
