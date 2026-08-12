"""Every package there is, one mechanic, found by looking.

`packages/<family>/<name>/`, and a package is whichever of these it chose to have:

    ontology.ttl   the terms it introduces, and its own namespace if it wants one
    shapes.ttl     what it refuses
    rules.ru       what it derives
    review.rq      how an agent may re-pick a belief this package owns
    Python         a module the RUNTIME loads, registered through PROVIDES

**All optional, and an omission is a statement.** `packages/part/esp32/` is an ontology and
nothing else, because a board has no behaviour a runtime could load — the BOARD does the work and
nothing here speaks its protocols. `packages/capability/market/` has all of it. Neither is more of
a package than the other.

**The family is the parent directory and nothing else says it.** `loader.Package.kind` reads it
off the path, so a plant is distinguishable from a part without a registry, a suffix convention,
or a triple anyone has to remember to write. Adding a family is `mkdir`; moving a package between
two is `git mv`.

**`__init__.py` is what marks a family as carrying Python**, which is the same rule that already
governed a package: one with no `__init__.py` is knowledge only, and that is a legitimate kind.
`core`, `bus`, `part`, `plant` and `tool` have none, and that is the honest shape of them.

The boundary this replaced was a directory: capability Python used to live under `agent/` so that
the tree showed which of it a runtime loads. It does not show that any more, so the CONTRACTS have
to — `lint-imports` holds `packages` away from `onboarding`, and the Containerfile decides what
reaches an image. Both were always the real enforcement; the layout was a reminder.
"""
