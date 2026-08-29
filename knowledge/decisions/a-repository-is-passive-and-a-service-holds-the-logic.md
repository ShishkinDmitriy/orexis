---
type: Decision
title: A repository is passive and a service holds the logic, and the mind is drawn as one target
description: >-
  The mind had no picture, and the words for its parts were doing two jobs — `Beliefs` was
  called a component beside the deliberator, though one is a scoped handle on a store and the
  other is the search. Decided that there are three layers — a `Store` is raw graph access, a
  repository wraps one and scopes it to this agent, a service holds the logic — and that
  `knowledge/diagrams/agent-structure.puml` draws the TARGET rather than today, because a
  picture of the current state is a registry that rots. Two findings fall out and are recorded
  as evidence, not as a list to maintain.
status: accepted
timestamp: 2026-08-29T00:00:00Z
---

# What was unclear

The bundle had no diagram of any kind, and one word covered two different things. `Beliefs`,
`Desires` and `Intentions` sat in the same sentence as `Deliberator` and `Keeper` — but the
first three are handles on a store, scoped to one agent, and the last two search and decide.
Nothing said which was which, so nothing could say where a new piece of work belongs.

# What is decided

**Three layers, and the code already had them:**

| layer | what it is | examples |
|---|---|---|
| store | raw graph access — `query`, `update`, `put_graph`, `clear_graph`, `optimize` | `agent/store.py::Store` |
| repository | wraps a store, scopes it to THIS agent, exposes `read()` | `Beliefs`, `Desires`, `Intentions`, `Imaginarium` |
| service | holds the logic | the planner, the deliberator, the keeper, `owing`, `revision`, `inference` |

**A repository is built two ways here and both are fine.** `Beliefs`, `Desires` and `Intentions`
WRAP a store and delegate; `Imaginarium` and `_Derivation` EXTEND one. The
[imaginarium](/domain/imaginarium.md) is a full repository — its own domain method is
`reached()`, which mints the graph for a search node — and it is the planner's rather than the
agent's, which is why it does not appear on `Agent`.

**The picture draws the TARGET, not today.** `knowledge/diagrams/agent-structure.puml`, linked
from [agent](/domain/agent.md), draws the six modalities of
[a-store-is-a-modality](/decisions/a-store-is-a-modality.md) with one repository each, and marks
the delta from what runs. Drawing the current state would produce a registry: a list nobody
gates, which the next change makes wrong silently. A target has a reason to be re-read — it is
either reached or amended.

**Source, no rendered image.** `plantuml -tpng knowledge/diagrams/agent-structure.puml` is one
command, and a committed PNG rots while the source stays checkable against the file it describes.

# The evidence, as measured on 2026-08-29

A snapshot, and it is here rather than in a domain page for exactly one reason: nothing gates it.
Left as a live list it would be a registry by imitation — the shape
[a-package-is-its-name](/decisions/a-package-is-its-name.md)'s follow-up removed from
`pyproject.toml`, where twenty inert entries invited a twenty-first. Read it as what was true
when the layering was settled.

| service | process | in | out |
|---|---|---|---|
| planner | planning — the search | menu templates; world, sensed, own beliefs; desires | imaginarium: one graph per search node; returns a plan |
| deliberator | deliberation — the *whether* | menu rows; desires | `graph/deliberation`; returns the plan |
| menu build | menu derivation | `graph/actions`; world, sensed, own beliefs; desires | **nothing** — rows are never stored |
| desires build | desire derivation | own beliefs, obligations, asserted wants | `graph/desire/derived` |
| execution | plan, commit, take | `ag:takenBy` | **nothing** — calls `adopt`, then `take` |
| keeper | commitment keeping; the verification arc | intentions; desires | `graph/intentions/{agent}` |
| owing | debt keeping | claims issued to me | `graph/obligations/{agent}` |
| revision | belief revision | marks | **nothing** — wakes deliberation |
| inference | entailment materialisation | ontology, world | the entailed graphs |
| upkeep | compaction | — | the store on disk |

**Three services store nothing, and each has a stated reason** — the menu build by principle
([affordance](/domain/affordance.md)), execution because it only orchestrates, revision because
it only marks. A service that writes no data is usually a smell; these three are the exceptions
that say why.

# What this found

- **`Desires.rebuild()` is a service inside a repository.** `_Derivation(Store)` runs every
  package's `desires.ru` from within the repository that
  [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) says the runtime may only read.
  The intent holds; it is kept true by hiding the writer inside rather than by the layering.
- **Two graphs sit in a store that is not their modality.** `graph/actions` is menu-modality and
  `graph/deliberation` is possible-modality, and both live in the beliefs store — while the
  imaginarium, also possible-modality, is a store of its own. That is the one rule
  a-store-is-a-modality exists to state, unmet in two places.

# Seams left open

- **Where `graph/deliberation` belongs is undecided.** Possible-modality by its class, so the
  imaginarium — but it must SURVIVE the pass, because the health series read it, and the
  imaginarium is dropped. History is the likely home and
  [#311](https://github.com/ShishkinDmitriy/orexis/issues/311) does not name it.
- **Nothing gates the diagram.** It is checked by being re-read, like the prose around it. A
  test that a drawn graph name exists in the vocabulary would catch the cheapest kind of rot and
  is not written.
