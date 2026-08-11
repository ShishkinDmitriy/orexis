"""How bytes become a document — the first stage, and a family.

    bytes ─[codec]→ document ─[pointer]→ raw value ─[scaling]→ quantity

A codec knows one wire format and nothing else: not which channel the bytes arrived on, not
which value in the document is anyone's, not what the number means. It codes both ways, which
is why it is a codec and not a parser — a cadence published to a board is encoded by the same
package that decodes what the board sends back.

**The same mechanism as a capability; a different bearer.** Rule 2 defines a capability as a
named ability with interchangeable implementations and says nothing about who bears it, so this
is one — it is simply not something an AGENT has. A capability is derived onto an agent as
`ag:hasCapability`; a codec is derived onto a SENSOR as `codec:decodedBy`. Same discipline
either way: the world states a premise, genesis writes the conclusion into the derived graph,
and the runtime looks it up.

**Which is why nothing here searches.** An earlier draft of this file asked each class whether
it `claims()` a sensor — re-deciding at every boot what genesis already knew, from facts that
were already in the graph, and then not writing the answer down. That cost three things this
project normally refuses: a world could name a codec no build implements and still validate;
nothing could inspect a sensor's pipeline, because it existed only as the outcome of a Python
loop; and which member won depended on `PROVIDES` iteration order, which guarantees nothing.
`codecs/json/rules.ru` decides it now, and a shape checks there is exactly one answer.

See knowledge/decisions/bytes-become-a-quantity-in-stages.md.
"""

from __future__ import annotations

from . import loader


class CodecError(ValueError):
    """Bytes that are not a document of this codec's format."""


class Codec:
    """One wire format.

    `TERM` is the T-Box term this class implements — the same contract a capability module's
    `CAPABILITY` has, and how `agent.loader` maps a derived fact back to the code that serves
    it. There is no `DEFAULT` here: what a sensor gets when its world states nothing is decided
    by this package's `rules.ru`, which is where a default belongs, because a default computed
    in Python is a fact nothing can read.
    """

    TERM: str = ""

    def decode(self, payload: bytes):
        """The document these bytes hold. Raises `CodecError` if they are not one."""
        raise NotImplementedError

    def encode(self, document) -> bytes:
        """The bytes that document is, on the wire.

        The other direction, and it is not decoration — but it is not yet reached either.
        `agent/runtime.py` serialises every outbound message with `json.dumps`, so a cadence
        published to a board does not pass through here. A society speaking a binary format to
        its sensors would have to route that path through a codec first; until then this is
        implemented and tested against `decode`, and nothing in production calls it.
        """
        raise NotImplementedError


def codec_for(sensor) -> Codec | None:
    """Whichever codec genesis decided serves this sensor, or None if this build lacks it.

    A lookup of the derived `codec:decodedBy`, exactly as `agent.provider(family)` looks up a
    capability — never a search, and never a default applied here.

    None is a legitimate answer and is reported, not raised: a world may name a member that is
    declared in the vocabulary and implemented by nobody, which is the position `perception:Polling` and
    `review:Consulting` already hold. The honest cost is one unread sensor and a warning, not a
    society that cannot start.
    """
    cls = loader.codecs().get(sensor.decoded_by)
    return cls() if cls else None
