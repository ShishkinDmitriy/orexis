"""An extension point is a TERM, and `@contributes` fills one.

The whole mechanism, and it is four lines of state: a decorator that marks a function with the
term it fills, and a resolver that finds the marked function on a class, an instance or a MODULE.

That last is the reason this is not simply the choir. A `Module` instance fills the run-time
points — *how urgent is this?*, *carry this out* — and a package's `__init__.py` fills the
assembly-time ones — *what vocabulary do you bring?*. Same decorator, same term-space, and the
audience decided by WHERE the decorated function lives rather than by anything declared: a
package module has no `@contributes(URGENCY)` and an instance has no `@contributes(VOCABULARY)`.

A point publishes the signature that fills it (`assembly:signature`, beside the term), so a
package can fill a point another package declared without importing whoever declared it — which
is what makes an extension point an extension point rather than a private callback.
"""

from __future__ import annotations

from types import ModuleType


def contributes(term: str):
    """Mark a function as filling one extension point, by TERM.

    Was `@hook`. The term is an `assembly:Extension` some ontology declares — the kernel's for
    the BDI-shaped questions, a package's for its own — and the asker finds the function through
    it. An override by NAME inherits the term: the kernel's defaults carry theirs, so a package
    filling `reports` need not repeat it (a-hook-is-a-term).
    """
    def mark(fn):
        fn.__contributes__ = term
        return fn
    return mark


def extensions_of(subject) -> dict[str, str]:
    """term -> the name of the function filling it, on a class, an instance or a module.

    Read once and cached on the subject where one can be cached. A class is walked in reverse
    MRO so a subclass wins; a module is a flat namespace and needs no walking.
    """
    if isinstance(subject, ModuleType):
        return {term: name for name, fn in vars(subject).items()
                if (term := getattr(fn, "__contributes__", None))}

    cls = subject if isinstance(subject, type) else type(subject)
    found = cls.__dict__.get("_extensions_of")
    if found is None:
        found = {}
        for klass in reversed(cls.__mro__):
            for name, fn in vars(klass).items():
                if term := getattr(fn, "__contributes__", None):
                    found[term] = name
        cls._extensions_of = found
    return found


def answer(subject, term: str):
    """Whatever fills one point on this subject, ready to call — or None if nothing does."""
    name = extensions_of(subject).get(term)
    return getattr(subject, name) if name else None
