"""How bytes become a number — the three stages, and the family among them.

    bytes ─[codec]→ document ─[pointer]→ number

Ported from the 0.1.0 sensing package, where the codec was a contract a plug-in package
implemented and the pointer was the one function after it (RFC 6901 works over any tree, so
nothing about it varies with the codec that made the document). What changes here is where
`parse` lives: it was the transport's driver that ran the codec and the pointer, fusing how a
device is reached with what its bytes mean; bytes to number is sensing's, and a transport hands
bytes.

**A NUMBER IS NOT YET A QUANTITY.** What the number is an observation of, and what quantity it is,
are concluded by this layer's rules from the topology and the calibration the agent believes of
the sensor (rules.ttl) — a probe's count is a moisture there, and a thermometer's degrees are
already one. The scaling that stood here as a third stage and a family of code members went with
that: arithmetic over beliefs is a rule, and a rule is revised when the belief is.

**THE CONCEPT IS THIS LAYER'S, IN ITS ONTOLOGY.** A codec is a family in rule 2's sense,
`sensing:Codec`; which member serves a sensor is a fact the world derives onto it
(`sensing:decodedBy`) and this module looks up; the member that ships, JSON, is declared beside the
family and held here by its term, and a sensor whose world states none gets it. A member from a
package declares its own term as an instance of the family and implements the contract below;
until genesis loads such members the table holds this layer's one, and a member the world names
that the table lacks is one unread sensor and a warning, never a dead agent.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from agent.ontology import PUBLIC
from agent.store import graphs_of, rows

from .ontology import JSON_CODEC

log = logging.getLogger("pipeline")

#  What a sensor's value is called when nothing says otherwise: every single-property device
#  here publishes `{"value": ...}`.
DEFAULT_POINTER = "/value"


class CodecError(ValueError):
    """Bytes that are not a document of this codec's format."""


class PointerError(ValueError):
    """A pointer that does not resolve to a number in this document."""


class Codec:
    """One wire format, both ways — a member of `sensing:Codec`. `TERM` is the term the class
    implements, an instance of the family declared by this layer or by the member's package."""

    TERM: str = ""

    def decode(self, payload: bytes):
        """The document these bytes hold. Raises `CodecError` if they are not one."""
        raise NotImplementedError

    def encode(self, document) -> bytes:
        """The bytes that document is, on the wire."""
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


CODECS: dict[str, type[Codec]] = {JsonCodec.TERM: JsonCodec}


def resolve(pointer: str, doc):
    """The one RAW VALUE a JSON Pointer identifies — RFC 6901. Number-only by our decision
    (#101): a whole sub-document handed on would fail far from its cause."""
    node = _walk(pointer, doc)
    if isinstance(node, bool) or not isinstance(node, (int, float)):
        raise PointerError(f"{pointer!r}: what is there is not a number")
    return node


def _walk(pointer: str, doc):
    """Whatever a JSON Pointer identifies in `doc`, RFC 6901."""
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
    return node


#  THE BINDING: what the world derives onto a sensor about its bytes, every part optional.
_BINDING_Q = """
SELECT ?codec ?pointer ?starts ?ends WHERE {
  OPTIONAL { $sensor sensing:decodedBy ?codec }
  OPTIONAL { $sensor sensing:readingPointer ?pointer }
  OPTIONAL { $sensor sensing:startsPointer ?starts }
  OPTIONAL { $sensor sensing:endsPointer ?ends } }"""


def _binding(store, sensor: str) -> dict:
    return next(iter(rows(store, _BINDING_Q, graphs_of(store, PUBLIC), sensor=sensor)), {})


def _codec(sensor: str, binding: dict) -> Codec | None:
    """The codec the binding names, or None where it is one nothing here implements — said in the log."""
    codec_cls = CODECS.get(binding.get("codec") or JsonCodec.TERM)
    if codec_cls is None:
        log.warning("%s names a codec nothing here implements: %s", sensor, binding["codec"])
        return None
    return codec_cls()


def decode(store, sensor: str, payload: bytes) -> float | None:
    """The number `sensor`'s share of `payload` holds, by the binding public knowledge states for
    it, or None where any stage refuses — said in the log, since a pointer that misses is not a
    measurement and nothing is written."""
    binding = _binding(store, sensor)
    codec = _codec(sensor, binding)
    if codec is None:
        return None
    try:
        return float(resolve(binding.get("pointer") or DEFAULT_POINTER, codec.decode(payload)))
    except (CodecError, PointerError) as exc:
        log.warning("%s: unread — %s", sensor, exc)
        return None


def reads_series(store, sensor: str) -> bool:
    """Whether `sensor` reads a SERIES: it states where the instants its values are for are kept,
    `sensing:startsPointer` or `sensing:endsPointer`."""
    binding = _binding(store, sensor)
    return bool(binding.get("starts") or binding.get("ends"))


def decode_series(store, sensor: str, payload: bytes) -> list[tuple[datetime, datetime, float]] | None:
    """The stretches `sensor`'s series in `payload` holds — (start, end, value), first first —
    by its binding, or None where any stage refuses, said in the log.

    The reading pointer finds the array of values and the starts or ends pointer the array of
    instants beside it; each value holds from its instant to the next (starts) or from the one
    before to its own (ends), and the stretch at the open end is as long as its neighbour. An
    instant is ISO 8601 or seconds since the epoch, and one without an offset is UTC, as a
    service asked in GMT answers. A value that is not a number — a null where the service has
    nothing — is no stretch."""
    binding = _binding(store, sensor)
    codec = _codec(sensor, binding)
    if codec is None:
        return None
    ends = not binding.get("starts")
    try:
        document = codec.decode(payload)
        values = _walk(binding.get("pointer") or DEFAULT_POINTER, document)
        instants = _walk(binding.get("ends") if ends else binding.get("starts"), document)
        if not isinstance(values, list) or not isinstance(instants, list) or len(values) != len(instants):
            raise PointerError("the values and the instants are not two arrays of one length")
        times = [_instant(i) for i in instants]
    except (CodecError, PointerError, ValueError, TypeError) as exc:
        log.warning("%s: unread series — %s", sensor, exc)
        return None
    if len(times) < 2:
        log.warning("%s: a series of %d instant(s) says no stretch", sensor, len(times))
        return None
    out = []
    for n, (when, value) in enumerate(zip(times, values)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if ends:
            start = times[n - 1] if n > 0 else when - (times[1] - times[0])
            end = when
        else:
            start = when
            end = times[n + 1] if n + 1 < len(times) else when + (times[-1] - times[-2])
        out.append((start, end, float(value)))
    return out


def _instant(value) -> datetime:
    """An instant a series gives: ISO 8601, UTC where it states no offset, or seconds since the
    epoch."""
    if isinstance(value, bool):
        raise ValueError(f"{value!r} is not an instant")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    when = datetime.fromisoformat(str(value))
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)
