"""How bytes become a quantity — the three stages, and the two families among them.

    bytes ─[codec]→ document ─[pointer]→ raw value ─[scaling]→ quantity

Ported from the 0.1.0 sensing package, where the codec and the scaling were contracts a
plug-in package implemented and the pointer was the one function between them (RFC 6901 works
over any tree, so nothing about it varies with the codec that made the document). What changes
here is where `parse` lives: it was the transport's driver that ran the codec and the pointer,
fusing how a device is reached with what its bytes mean; bytes to number is sensing's, and a
transport hands bytes.

**THE MEMBERS ARE A TABLE UNTIL GENESIS 0.2.0 LOADS THEM.** Which codec and which scaling serve
a sensor are facts the world derives onto it (`codec:decodedBy`, `scaling:scaledBy`) and the
runtime looks up; the two members that ship, JSON and identity, are held here by their IRIs,
and a sensor whose world states neither gets them, which is what every board here speaks and
does. A member the world names and this table lacks is one unread sensor and a warning, never
a dead agent.
"""

from __future__ import annotations

import json
import logging

from agent.ontology import PUBLIC
from agent.store import Raw, graphs_of, rows

from .ontology import DECODED_BY, IDENTITY_SCALING, JSON_CODEC, SCALED_BY

log = logging.getLogger("pipeline")

#  What a sensor's value is called when nothing says otherwise: every single-property device
#  here publishes `{"value": ...}`.
DEFAULT_POINTER = "/value"


class CodecError(ValueError):
    """Bytes that are not a document of this codec's format."""


class PointerError(ValueError):
    """A pointer that does not resolve to a number in this document."""


class Codec:
    """One wire format, both ways. `TERM` is the T-Box term the class implements."""

    TERM: str = ""

    def decode(self, payload: bytes):
        """The document these bytes hold. Raises `CodecError` if they are not one."""
        raise NotImplementedError

    def encode(self, document) -> bytes:
        """The bytes that document is, on the wire."""
        raise NotImplementedError


class Scaling:
    """One way of turning a raw value into a quantity, in the unit the sensor declares."""

    TERM: str = ""

    def apply(self, sensor: str, raw: float) -> float:
        """The quantity `raw` is for the sensor named — its IRI, for a scaling that must ask
        the world about it."""
        raise NotImplementedError


class JsonCodec(Codec):
    """Bytes to a document and back, by the format every board here already speaks."""

    TERM = JSON_CODEC

    def decode(self, payload: bytes):
        try:
            return json.loads(payload)
        except (ValueError, UnicodeDecodeError) as exc:
            raise CodecError(f"not a JSON document: {exc}") from exc

    def encode(self, document) -> bytes:
        try:
            return json.dumps(document).encode()
        except (TypeError, ValueError) as exc:
            raise CodecError(f"not encodable as JSON: {exc}") from exc


class IdentityScaling(Scaling):
    """The raw value, as it stands: the firmware scaled before it published."""

    TERM = IDENTITY_SCALING

    def apply(self, sensor: str, raw: float) -> float:
        return raw


CODECS: dict[str, type[Codec]] = {JsonCodec.TERM: JsonCodec}
SCALINGS: dict[str, type[Scaling]] = {IdentityScaling.TERM: IdentityScaling}


def resolve(pointer: str, doc):
    """The one RAW VALUE a JSON Pointer identifies — RFC 6901. Number-only by our decision
    (#101): a whole sub-document handed on would fail far from its cause."""
    if not pointer.startswith("/"):
        raise PointerError(f"{pointer!r} is not a JSON Pointer — it must start with '/'")
    node = doc
    for token in pointer.split("/")[1:]:
        key = token.replace("~1", "/").replace("~0", "~")      # ~1 first, then ~0
        if isinstance(node, list):
            if not key.isdigit():
                raise PointerError(f"{pointer!r}: {key!r} is not an array index")
            index = int(key)
            if index >= len(node):
                raise PointerError(f"{pointer!r}: index {index} is past the end")
            node = node[index]
        elif isinstance(node, dict):
            if key not in node:
                raise PointerError(f"{pointer!r}: no {key!r} here")
            node = node[key]
        else:
            raise PointerError(f"{pointer!r}: {key!r} has nothing to select from")
    if isinstance(node, bool) or not isinstance(node, (int, float)):
        raise PointerError(f"{pointer!r}: what is there is not a number")
    return node


#  THE BINDING: what the world derives onto a sensor about its bytes, every part optional.
_BINDING_Q = """
SELECT ?codec ?pointer ?scaling WHERE {
  OPTIONAL { $sensor $decodedBy ?codec }
  OPTIONAL { $sensor sensing:readingPointer ?pointer }
  OPTIONAL { $sensor $scaledBy ?scaling } }"""


def decode(store, sensor: str, payload: bytes) -> float | None:
    """The quantity `sensor`'s share of `payload` holds, by the binding public knowledge states
    for it, or None where any stage refuses — said in the log, since a pointer that misses is not
    a measurement and nothing is written."""
    binding = next(iter(rows(store, _BINDING_Q, graphs_of(store, PUBLIC), sensor=sensor,
                             decodedBy=Raw(f"<{DECODED_BY}>"), scaledBy=Raw(f"<{SCALED_BY}>"))), {})
    codec_cls = CODECS.get(binding.get("codec") or JsonCodec.TERM)
    if codec_cls is None:
        log.warning("%s names a codec nothing here implements: %s", sensor, binding["codec"])
        return None
    scaling_cls = SCALINGS.get(binding.get("scaling") or IdentityScaling.TERM)
    if scaling_cls is None:
        log.warning("%s names a scaling nothing here implements: %s", sensor, binding["scaling"])
        return None
    try:
        document = codec_cls().decode(payload)
        raw = resolve(binding.get("pointer") or DEFAULT_POINTER, document)
        return float(scaling_cls().apply(sensor, float(raw)))
    except (CodecError, PointerError) as exc:
        log.warning("%s: unread — %s", sensor, exc)
        return None
