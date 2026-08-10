"""How bytes become a document — the first stage, and a family.

    bytes ─[codec]→ document ─[pointer]→ raw value ─[calibration]→ quantity

A codec knows one wire format and nothing else: not which channel the bytes arrived on, not
which value in the document is anyone's, not what the number means. It codes both ways, which
is why it is a codec and not a parser — a cadence published to a board is encoded by the same
package that decodes what the board sends back.

**The same plug-in mechanism as a capability; a different bearer.** Rule 2 defines a capability
as a named ability with interchangeable implementations, and says nothing about who bears it —
so this is one, by that definition. What differs is what it is attached to, and the selection
follows from that:

    capabilities/                      borne by an AGENT   selected at genesis, derived into
                                                           the graph as `ag:hasCapability`
    transports/ codecs/ calibrations/  borne by a BINDING  selected at runtime, by `claims()`
                                                           from what the sensor declares

That is not a convention, it follows from the bearer. An agent's capability is about what it
IS, which is a fact the world should hold and validate. A binding's is about what a device
SPEAKS, which only the device can say and which no world should have to restate. So this tree
ships no `rules.ru` and grants nothing — not because it is lesser, but because there is nothing
about an agent to derive.

Adding a codec is adding a directory under `codecs/`: no capability, no derivation, no edit
here. See knowledge/decisions/bytes-become-a-quantity-in-stages.md.
"""

from __future__ import annotations

from . import loader


class CodecError(ValueError):
    """Bytes that are not a document of this codec's format."""


class Codec:
    """One wire format.

    Two class attributes decide selection, and between them they make *explicit beats default*
    structural rather than a matter of who is asked first:

    `TERM`      the T-Box term a binding names to ask for this codec by name.
    `DEFAULT`   whether a binding that names NO codec gets this one.

    Exactly one member may be the default and no two may share a term; `agent.loader` refuses
    a build that breaks either, because both would otherwise resolve silently to whichever
    class the filesystem happened to yield first.
    """

    TERM: str = ""
    DEFAULT: bool = False

    @classmethod
    def claims(cls, sensor) -> bool:
        """Whether this codec is the one that binding asked for.

        A stated encoding is answered ONLY by the codec whose term it is — so a default can
        never shadow an explicit choice, however the classes are ordered. Silence is answered
        only by the default. The two branches are disjoint by construction, which is the whole
        reason this is not a `for` loop over claims that happen to be written carefully.
        """
        stated = getattr(sensor, "encoding", None)
        return stated == cls.TERM if stated else cls.DEFAULT

    def decode(self, payload: bytes):
        """The document these bytes hold. Raises `CodecError` if they are not one."""
        raise NotImplementedError

    def encode(self, document) -> bytes:
        """The bytes that document is, on the wire.

        The other direction, and it is not decoration: an agent instructs its boards as well as
        listening to them, and a society speaking a binary format to its sensors would have to
        speak it back when it sets a cadence.
        """
        raise NotImplementedError


def codec_for(sensor) -> Codec | None:
    """The codec this binding selects, or None if this build carries no such format.

    None is a legitimate answer and is reported, not raised — the same shape of fact as a
    transport that cannot speak to a device or a capability no package implements. A world may
    legitimately name a format a leaner build does not carry, and the honest failure is one
    sensor going unread with a warning, not an agent that will not start.
    """
    for cls in loader.codecs():
        if cls.claims(sensor):
            return cls()
    return None
