---
type: Decision
title: One tree and one mechanic, and the family is the directory above
description: >-
  There were two package systems that looked alike and lived apart — vocabulary/ at the root
  and capability trees under agent/ — split by who loads the Python, which is invisible in a
  listing. They are one tree now, packages/<family>/<name>/, and the family is the parent
  directory, so Package.kind distinguishes a plant from a part instead of saying "vocabulary"
  eleven times. The cost is that the layout no longer shows which Python a runtime loads, so
  the import contracts and the Containerfile carry that boundary alone. The move also cost 143
  tests silently, which is the sharpest argument yet for issue #106.
status: accepted
timestamp: 2026-08-12T00:00:00Z
---

> **Current statement: [package](/domain/package.md).** This record is how the model got
> there and why; the domain concept is what it is now. Four records amend each other on
> this subject, so read the concept first unless you want the argument.

# Context

Two package systems, identical in shape and apart in the tree:

```
vocabulary/<name>/          ontology.ttl  shapes.ttl  rules.ru
agent/capabilities/<name>/  ontology.ttl  shapes.ttl  rules.ru  review.rq  Python
agent/transports/<name>/    …and the same for codecs and scalings
```

Same discovery, same files, same namespace mechanism — and `loader.prefixes()` picked up a new
one without a registry edit either way. The split was by **who loads the Python**, which is a
real distinction and an invisible one: nothing in a listing shows it, and the two halves were
drifting into parallel conventions for no reason a reader could see.

It also made `Package.kind` nearly useless. Eleven packages answered `"vocabulary"` — a plant, a
part, a protocol and an export target, indistinguishable — while a capability answered
`"capabilities"` only because its Python needed somewhere to live.

# What was decided

**One tree, `packages/<family>/<name>/`, and the family is the parent directory.**

```
packages/core/agora            packages/capability/market
packages/bus/onewire           packages/transport/mqtt
packages/part/dht11            packages/codec/json
packages/plant/zamioculcas     packages/scaling/identity
packages/tool/wokwi
```

A package holds whichever of `ontology.ttl`, `shapes.ttl`, `rules.ru`, `review.rq` and Python it
wants. Every one optional, **and an omission is a statement**: `packages/part/esp32/` is an
ontology and nothing else because a board has no behaviour a runtime could load, and
`packages/capability/market/` has all of it. Neither is more of a package than the other.

`__init__.py` is what marks a family or a package as carrying Python, which is the rule that
already governed one: *a package with no `__init__.py` is knowledge only, and that is a
legitimate kind of package.* `core`, `bus`, `part`, `plant` and `tool` have none.

**The family is read off the path and declared nowhere.** `packages()` finds whatever
directories exist; `KINDS` fixes only the order they merge in, so a family invented tomorrow is
found and merely sorts after the known ones. That is what a registry could not give.

# What was NOT done, and why

**Grouping by subject was rejected** — `parts/` and `plants/` as separate ideas — because it
would file apart the two packages most worth reading together. `packages/part/dht11/` and
`packages/plant/zamioculcas/` are structurally identical: a model described once whose units a
world names, reaching them by `owl:hasValue`. They sit in different families and the same tree,
which is the honest arrangement.

**Flat prefixed names** (`part_dht11`, `agent_capability_market`) were the other candidate and
lose three things hierarchy keeps: `kind` as real data, import paths that read
(`packages.capability.market`), and a contract that can name a family in one line. Capabilities
also could not take the hyphenated form at all — a hyphen is illegal in a Python module path.

**`agent/capabilities/market` already spelled it.** Java writes a package with dots and a
filesystem with slashes; the grouping was there and only the vocabulary half was missing it.

# The cost, stated plainly

**The layout no longer shows which Python a runtime loads.** `packages/capability/market/` and
`packages/part/dht11/` look identical, and the reason the old split existed was exactly that
visibility. What carries the boundary now:

- `lint-imports`: `packages` may not import `onboarding`. Four listed trees collapsed to one line.
- the `Containerfile`: it names `agent/` and `packages/` and not `onboarding/`, and
  `tests/test_layout.py` fails if that changes.

Both were always the real enforcement — the directory was a reminder. The reminder is gone, so
those two files say so in their own comments rather than relying on someone remembering this
record.

# It cost 143 tests, silently, and half the guards caught it

Worth recording because it is the third instance of the same failure this month.

`test_every_source_group_is_still_found` fired immediately on two globs that went empty — exactly
what it exists for. But a third glob, `agent/**/*.py`, still matched plenty of files after
capability Python left that tree, so it stayed green while **every capability's SPARQL dropped
out of the prefix scans in three separate test files**. 851 tests became 708 and the suite was
green at both numbers.

**Non-empty is not the same as complete.** The non-emptiness guard was written after a move
emptied a glob twice; this time the glob did not empty, it merely stopped covering what it was
named for. Found by diffing collected test ids against the pre-move tree — 861 before, 869 after,
nothing missing — which is a check nothing performs automatically. See
[#106](https://github.com/ShishkinDmitriy/agora/issues/106).

# Seams left open

- **The loader enforces exactly two levels.** "A directory is a package, and a directory inside
  one is another package" is the model, but `packages()` walks a fixed depth, so
  `plant/aroid/zamioculcas/` would not be found. Making it recursive is small — a directory is a
  package if it directly holds one of the four files or Python beyond `__init__.py` — and
  nothing needs a third level yet.
- **Tests did not move here; they did in the record that follows.** See
  [a-package-may-test-itself](/decisions/a-package-may-test-itself.md), which also corrects the
  count stated here — it was 17, not 29. The reporting half was misclassified: eleven of its
  twelve take a fixture built by `conftest.build_agent`, which is *"a real Agent — real world,
  real beliefs, real modules"*, and the marker list used to measure it did not name that helper.
- **The image has not been rebuilt** since the move. The `Containerfile` and `.containerignore`
  are updated and the layout tests pass on both, but only a `podman build` proves it.
