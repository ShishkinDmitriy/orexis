"""JSON on the wire, both ways.

The only codec this project has ever had, which is exactly why it was invisible: `json.loads`
sat inside the MQTT driver, fusing two independent facts — how a device is reached, and what its
bytes mean. A society could speak MQTT and send CBOR, or speak Modbus and send JSON.
"""

from __future__ import annotations

import json

from agent.codec import Codec, CodecError

from .terms import JSON


class JsonCodec(Codec):
    """Bytes to a document and back, by the format every board here already speaks."""

    TERM = JSON

    # What a binding that names no encoding gets. Every shipped world states none, so this is
    # what keeps them reading exactly as they did before this package existed. Exactly one
    # member may claim it — `agent.loader` refuses a build where two do, because "the default"
    # resolving to whichever class was yielded first is the quietest kind of wrong.
    DEFAULT = True

    def decode(self, payload: bytes):
        """The document these bytes hold.

        Every failure mode of `json.loads` becomes one `CodecError`: bad UTF-8, a truncated
        object, a bare number where an object was expected. The caller does not care which — a
        payload that is not a document is a payload with no reading in it, and the sensor is
        reported unread either way.
        """
        try:
            return json.loads(payload)
        except (ValueError, UnicodeDecodeError) as exc:
            raise CodecError(f"not a JSON document: {exc}") from exc

    def encode(self, document) -> bytes:
        try:
            return json.dumps(document).encode()
        except (TypeError, ValueError) as exc:
            raise CodecError(f"not encodable as JSON: {exc}") from exc
