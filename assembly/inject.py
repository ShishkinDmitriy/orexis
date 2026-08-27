"""What a package OFFERS, and what it needs — one way in, declared at both ends.

The choir is fan-out: `agent.ask(POINT)` collects from everyone with an opinion. This is
fan-in: one thing, offered by one package, looked up by its TERM.

    # offering, in a package's __init__.py
    @provides
    def history(agent) -> HistoryRing:       # the key IS what it says it returns
        from .ring import Ring               # the implementation, lazily
        return Ring(agent)

    # needing, on a module — an annotation with no value beside it
    class Recorder(Module):
        beliefs: Beliefs                     # required
        history_ring: HistoryRing | None     # optional: None where nothing offers it

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

**Declared eagerly, resolved lazily.** The annotations are read at assembly so a gate can say
*"ReviewModule requires Desires and nothing offers it"* before an agent boots. What is injected
is a handle: the object is built on first touch, which keeps construction order out of it and
keeps imports following grants (#216).
"""

from __future__ import annotations

import re
import types

from .contribute import contributions_of


def _returned(fn):
    """The class a provider says it returns — its key, read off the annotation.

    Not off the returned OBJECT, which would be the obvious other place to look and cannot
    work: finding out what it returns means calling it, and the whole point is that a provider
    runs only when an agent asks. The annotation says the same thing without building anything,
    and a type checker holds the provider to it.
    """
    from typing import get_type_hints

    hint = get_type_hints(fn).get("return")
    if hint is None:
        raise RuntimeError(
            f"{fn.__module__}.{fn.__name__} is decorated `@provides` with nothing to go on: "
            "annotate what it returns, or name the key as `@provides(Key)`."
        )
    return hint


def provides(key=None):
    """Offer one service. One key, one provider.

        @provides                       # the key is the return annotation
        def history(agent) -> HistoryRing: ...

        @provides(SOME_TERM)            # or named, for a contract that is not a class
        def sink(agent): ...

    Bare is the better form: the key is written once, where it is already needed for the type
    checker to be any use, so the declaration and the thing declared cannot drift.
    """
    if isinstance(key, types.FunctionType):      # bare `@provides`, key from the annotation
        key.__provides__ = _returned(key)
        return key

    def mark(fn):
        fn.__provides__ = key
        return fn
    return mark


_MISSING = object()


def injections_of(cls) -> dict:
    """attribute name -> (key, optional), read off the class's own annotations.

    **A value-less annotation is a service.** The same convention `dataclasses` uses: a field is
    an annotation with no value beside it, and one WITH a value is an ordinary class attribute
    (`CAPABILITY: str = ""` is not injected, and cannot be mistaken for it).

        class Recorder(Module):
            beliefs: Beliefs                   # required — a missing one is a broken build
            history_ring: HistoryRing | None   # optional — None where nothing offers it

    This replaced `@requires` and `@uses`. Two reasons, and the second is the one that decided
    it. A decorator that makes attributes appear is invisible to every tool a Python developer
    brings — no autocomplete, no go-to-definition, and a type checker calling `self.beliefs` an
    error — where an annotation is seen by all of them. And `| None` says optional in the
    language's own vocabulary, so a second decorator stopped being needed at all.
    """
    from typing import get_args, get_origin, get_type_hints

    hints = get_type_hints(cls)
    out: dict = {}
    for klass in reversed(cls.__mro__):
        for name in getattr(klass, "__annotations__", {}):
            hint = hints.get(name)
            existing = getattr(cls, name, _MISSING)
            if existing is not _MISSING:
                #  A value beside it makes it an ordinary attribute — unless what it collides
                #  with is INHERITED, which means the annotation is trying to inject over
                #  something that already exists. `desires: Desires` did exactly that: the base
                #  `Module.desires()` is a choir extension point, the injection was silently
                #  skipped, and the module went on calling a bound method as if it were a store.
                #  Silence is the wrong failure for a name that is spelled twice.
                if hint is not None and name not in vars(klass):
                    raise RuntimeError(
                        f"{cls.__name__} annotates `{name}` for injection, but {name} is "
                        f"already {existing!r} on a base class. Choose another field name — "
                        "an injected attribute may not shadow one that exists."
                    )
                continue
            if hint is None:
                continue
            args = [a for a in get_args(hint) if a is not type(None)]
            optional = get_origin(hint) is not None and len(args) < len(get_args(hint))
            out[name] = (args[0] if optional and args else hint, optional)
    return out


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
