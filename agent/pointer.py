"""Which value in a document is this sensor's — the middle stage, and the one that is a function.

A reading arrives as bytes and becomes a quantity in three steps:

    bytes ─[codec]→ document ─[pointer]→ raw value ─[scaling]→ quantity

The outer two are families: `packages/codec/` and `packages/scaling/`, each a tree of packages
whose members are interchangeable. This one is not, and that is a claim worth defending rather
than an omission. **RFC 6901 works over any tree**, so a pointer written against JSON keeps
meaning the same thing over CBOR, over MessagePack, and over a struct a binary parser produced —
nothing about it varies with the codec that made the document or the scaling that consumes
the value. By rule 2, where nothing could differ you have a function.

That indifference is also why deferring the other two cost nothing: a pointer stated today
survives whichever members arrive later.

It lives in the kernel rather than in a transport because it is nothing to do with how bytes
arrived. It moved here from `transports/mqtt/driver.py`, where it was born with the only codec
this project has ever had — see knowledge/decisions/bytes-become-a-quantity-in-stages.md.
"""

from __future__ import annotations

# What a sensor's value is called when nothing says otherwise. Every single-property device
# here already publishes `{"value": ...}`, so the default is what the fleet does — and a world
# that never states a pointer reads exactly as it did before this existed.
DEFAULT_POINTER = "/value"


class PointerError(ValueError):
    """A pointer that does not resolve to a number in this payload."""


def resolve(pointer: str, doc):
    """The one RAW VALUE a JSON Pointer identifies — RFC 6901, April 2013, Standards Track.

    A pointer, not a query: RFC 6901 identifies exactly ONE value, which is exactly what a
    device reports per property. RFC 9535's JSONPath returns a nodelist, and taking "the first"
    of one would be a collapse rule we invented and then had to defend.

    What comes out is **raw** — what the device put on the wire. Turning it into an observed
    quantity is the scaling's job, and this function is indifferent to it exactly as it is
    indifferent to whichever codec produced `doc`.

    The empty pointer is legal in the RFC and means the whole document. It is refused here
    rather than supported, because a whole document is not a number and letting it through
    would turn a mis-stated world into a parse failure much further away.
    """
    if not pointer.startswith("/"):
        raise PointerError(f"{pointer!r} is not a JSON Pointer — it must start with '/'")

    node = doc
    for token in pointer.split("/")[1:]:
        # Order matters and is the classic bug: `~1` becomes `/` FIRST, then `~0` becomes `~`.
        # Reversed, a literal `~1` written as `~01` would decode to `/` instead of `~1`.
        key = token.replace("~1", "/").replace("~0", "~")
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
