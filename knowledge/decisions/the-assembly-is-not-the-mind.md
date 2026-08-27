---
type: Decision
title: The assembly is not the mind — one extension mechanism, in a root package of its own
description: >-
  A package contributed to a build in two unrelated ways: six filenames the kernel globbed, and
  a runtime choir of `ag:Hook` terms. The first meant a new kind of contribution was a kernel
  edit; the second was already open to any package but published no contract, so an answerer
  with the wrong parameters was logged and skipped. Decided that both become ONE mechanism —
  a named extension point, filled with `@contributes` — that it lives in `assembly/` beside
  `agent/` rather than inside a BDI engine, and that a point publishes the signature that fills
  it.
status: accepted
timestamp: 2026-08-27T12:00:00Z
---

# What was true before

**Two mechanisms, and only one of them was open.**

A package contributed *knowledge* by naming files the way the kernel expected —
`ontology.ttl`, `shapes.ttl`, `rules.ru`, `desires.ru`, `actions.ttl`, `review.rq`, six literals
in the loader reached through seven call sites. A package contributed *behaviour* through
the [choir](/domain/choir.md): `ag:Hook` terms, `@hook(term)` on a method,
`Agent.ask`/`Agent.tell`.

The consequences were asymmetric and both wrong:

- **A new kind of knowledge contribution was a kernel edit.** Sensing wanted `measures.ttl` and
  read it itself, privately, because the alternative was a constant and a reader function in the
  loader. So a package could not offer other packages a place to contribute knowledge — only the
  kernel could.
- **A hook published no contract.** The signature lived in the base method's docstring for a
  kernel hook and in the asking package's `choir.py` for a package's. An answerer whose
  parameters did not match raised `TypeError`, which `ask` caught, logged as *could not answer*,
  and stepped over — a module silently not participating. Measured across every multi-answerer
  hook, all fourteen agreed, which is discipline holding a line nothing checked.

And all of it sat in `agent/`, which is meant to be a BDI engine: belief, desire, intention, act,
plan. How a build is assembled from packages is not one of those.

# What is decided

**One mechanism.** An **extension point** is a term — `assembly:Extension` — declared by whoever
owns the question, and filled by `@contributes(TERM)` on a function. The verb is the one this
project was already using for the act — *the fifth thing a package contributes* — and not
`extends`, which means inheritance in every language a reader arrives from. Load-time and run-time are the
same idea at two moments: the loader asks package modules (**push**, at assembly), the agent asks
`Module` instances (**pull**, at runtime). Same decorator, same term-space, different audience —
and the audience is decided by *where the decorated function lives*, so nothing declares it.

**`assembly/`, beside `agent/` and `onboarding/`.** It owns finding packages, the choir
mechanism, and the extension vocabulary in its own namespace. `agent/` keeps the BDI extension
points it owns — `ag:desires`, `ag:take`, `ag:size` — and stops owning the machinery.
`lint-imports` gains the direction: **assembly ← agent ← onboarding**.

**A point publishes its signature.** `assembly:signature` on the term, checked strictly against
every filler's parameter names. It passes today everywhere; what changes is that a mismatch
becomes a gate failure instead of a logged absence. This is what makes a foreign extension point
usable: a package answering `metrics:register` reads the contract from the term, without
importing whoever declared it.

**A contribution is handed its own directory and returns paths** — `(package) -> list[Path]`.
That argument is the whole of the phase discipline. It is not handed a world, because the T-Box
is merged before any world is chosen; it is not handed a store, because `refresh_public` runs
before the belief base is open. **A contribution cannot reach for what does not exist, because
the argument is not there** — which is why no point declares a phase and none needs to, and why
`ag:row` stays exactly what it was: whether ANSWERING may block or search, a fact about the
cognitive layering that means nothing at assembly.

**Content is the wider signature this record first promised, and it is NOT built.** A string of
Turtle — fetched or generated — would let a package bring vocabulary from anywhere. Roughly
fifty consumers read these as files: `.read_text()`, `.parent.name`, `file_iri(p)`. No package
needs it. The way in when one does is to materialise content to a path at assembly, not to
widen fifty call sites for a capability with no customer.

**`PROVIDES` becomes `provides()`.** Assembly imports every package's `__init__`, so a top-level
`from .module import …` would drag every optional extra into every agent and undo #216. The
heavy import moves behind a call; `__init__.py` imports stdlib and the term modules, nothing else.

# What this costs, and it is a real cost

**Fourteen packages gain Python they do not have.** `part/`, `plant/`, `bus/`, `sim/` and `tool/`
are pure data today, and that was a stated property — *"`packages/orexis-part-esp32/` is an ontology and
nothing else, because a board has no behaviour a runtime could load."* Each gains a short
`__init__.py` that fills the vocabulary point.

The alternative considered was a `package.ttl` manifest, which keeps those packages data-only.
It was refused for two reasons: a manifest can disagree with the disk, so a renamed file goes
silently unread — the failure class this project keeps finding — and it would have been a second
extension mechanism beside the choir rather than the same one.

# What is guarded

- **`test_a_package_manifest_imports_nothing_expensive`** — a manifest may import stdlib, its
  own `.terms`, and `assembly`. Nothing else, at the top level. Proved by adding `import rdflib`
  to a manifest and watching it fail.
- **`test_every_point_publishes_the_signature_that_fills_it`** and
  **`test_what_fills_a_point_matches_the_signature_it_publishes`** — the contract travels with
  the term, strictly, on parameter names.
- **`test_every_run_time_point_declares_which_row_answering_it_belongs_to`** — and its mirror:
  no assembly-time point carries one.

# What the six filenames became

Three, and they belong to the two ROOTS rather than to any package. `assembly/` and `agent/` are
not packages — they are what packages are assembled onto — and neither may be imported to be
asked, since `assembly` importing `agent` is the one direction `lint-imports` forbids outright.
So the loader knows their layout by name, which is honest, because their layout is the loader's
own. Every other package says what it brings.

# Seams left open

- **A vocabulary fetched per boot breaks two things.** `orexis-validate` and the running agent
  could see different T-Boxes, which is what
  [one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md) exists to prevent, and
  [a-volume-can-be-older-than-the-vocabulary](/decisions/a-volume-can-be-older-than-the-vocabulary.md)
  loses the commit it migrates against. The mechanism allows it; the sane shape is to fetch at
  genesis and pin, which a package can do inside its own filler. Nothing enforces that.
- **`vocabulary` cannot read beliefs**, and no other point has that problem. `refresh_public`
  runs before the belief base is open, so a package generating vocabulary FROM beliefs is asking
  for a store that does not exist. Shapes, wants and actions generated from beliefs are fine.
- **The signature guard checks names, not types.** Two fillers agreeing on `(subject_uri,
  observed_property, value)` while disagreeing on what `value` may be is not caught, and a
  declared signature is a string rather than a structure.
- **Nothing yet refuses an extension point nobody fills.** `ag:notices` is declared, has a base
  method and a sensing filler, and is asked by nobody
  ([#413](https://github.com/ShishkinDmitriy/orexis/issues/413)) — the guard that would have said
  so cannot land until that is settled.
