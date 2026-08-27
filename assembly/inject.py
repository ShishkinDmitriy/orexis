"""What a package OFFERS, and what it needs — one way in, declared at both ends.

The choir is fan-out: `agent.ask(POINT)` collects from everyone with an opinion. This is
fan-in: one thing, offered by one package, looked up by its TERM.

    # offering, in a package's __init__.py
    @provides(HistoryRing)                   # the CONTRACT type, imported cheaply
    def history(agent):
        from .ring import Ring               # the implementation, lazily
        return Ring(agent)

    # needing, on a module
    @requires(HistoryRing)
    class Recorder(Module):
        def start(self):
            self.history_ring.append(...)    # injected, resolved on first touch

**A key is a TYPE where one can be imported, and a TERM where one cannot.** A type is the
better key and the default: you import the thing you want and ask for it, the type checker
follows you, and there is no parallel naming system to keep in step. `packages -> agent` is an
allowed import, so every service the kernel offers is keyed by its class.

A term is the fallback, for a service whose contract is not an importable class. It was once
the only key here, on the reasoning that `lint-imports` forbids capability packages importing
each other — true of an IMPLEMENTATION and not of a contract, which is the one import that
rule has always allowed (`packages/codec/json/` imports sensing's `Codec`). Terms belong to
extension points, where a point IS a declared thing in the graph; a service is a Python object
and its type says what it is.

**Declared eagerly, resolved lazily.** `@requires` is read at assembly so the gate can say
*"fern requires series:sink and nothing fern composes provides it"* before an agent boots.
What is injected is a handle: the object is built on first touch, which keeps construction
order out of it and keeps imports following grants (#216).
"""

from __future__ import annotations

import re

from .contribute import contributions_of


def provides(key):
    """Offer one service, by its contract TYPE or by a term. One key, one provider."""
    def mark(fn):
        fn.__provides__ = key
        return fn
    return mark


def requires(*keys):
    """Declare the services this class needs. Each arrives as an attribute named for its key.

    `@requires(Beliefs)` gives `self.beliefs`; `@requires(HISTORY)` gives the term's local part
    in snake_case. Either way the name is DERIVED, so the declaration and the use cannot drift:
    there is no second place to spell it.
    """
    def mark(cls):
        cls.__requires__ = tuple(keys) + tuple(getattr(cls, "__requires__", ()))
        return cls
    return mark


def offers_of(subject) -> dict:
    """key -> the name of the function offering it, on a module."""
    return {term: name for name, fn in vars(subject).items()
            if (term := getattr(fn, "__provides__", None))}


def needs_of(cls) -> tuple:
    """Every service key this class and its bases declared."""
    seen: list = []
    for klass in reversed(cls.__mro__):
        for key in klass.__dict__.get("__requires__", ()):
            if key not in seen:
                seen.append(key)
    return tuple(seen)


def attribute_for(key) -> str:
    """`Beliefs` -> `beliefs`; `…#seriesSink` -> `series_sink`. One rule, both kinds of key, so
    a name is never spelled twice."""
    local = key.__name__ if isinstance(key, type) else re.split(r"[#/:]", key)[-1]
    out = []
    for i, ch in enumerate(local):
        if ch.isupper() and i:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


class Handle:
    """A service, resolved on first touch and then remembered.

    Lazy is not an optimisation. Resolving at construction would mean a module needing another
    module's service could be built before it exists, which is the ordering problem this
    runtime does not have — every module is built with the agent alone and looks things up in
    `start()`. It would also import providers before knowing what was granted.
    """

    __slots__ = ("_resolve", "_term", "_value", "_done")

    def __init__(self, key, resolve):
        self._term, self._resolve, self._value, self._done = key, resolve, None, False

    def get(self):
        if not self._done:
            self._value, self._done = self._resolve(self._term), True
        return self._value

    def __getattr__(self, name):
        return getattr(self.get(), name)

    def __repr__(self) -> str:
        state = "resolved" if self._done else "unresolved"
        return f"<service {attribute_for(self._term)} ({state})>"
