---
type: Decision
title: A layer is a package in the one tree, and need is what loads it
description: >-
  The placement clause of a-layer-is-a-distribution fell before its first implementation
  merged. The layers do not become root trees beside the assembly — they join the one package
  tree as families, and what loads a layer is not unconditional membership but a hard
  dependency resolved at assembly, so the roster an agent carries derives from its grants the
  way everything else here derives from the world. A required injection is a hard dependency
  and pulls the package that provides it; an optional one is soft and injects only what is
  already there. The layering itself, the contract-only downward imports and the tested
  arrows all stand from the superseded record; what fell is where the trees live and the
  claim that every agent carries all of them.
status: accepted
timestamp: 2026-08-30T18:00:00Z
---

# Context

[a-layer-is-a-distribution](/decisions/a-layer-is-a-distribution.md) decided the split and
placed the layer trees at the root, beside `assembly/`, on the argument that the package tree
is the granted tree and a layer is unconditional — "a grant nobody can lack is not a grant."
The first implementation was built and verified to the letter: the stores extracted to a root
tree, every gate green, the image built, the boundaries measured inside it. It was refused
unmerged, which is the strongest form a refusal takes — not a thought experiment but a working
alternative, closed with the work intact on its branch.

What refused it is the architecture's own author seeing the placement differently, and the
difference is not taste. The root-tree clause quietly carried a second decision nobody had
examined: that every agent carries every layer, with "which layers ship" waved to a seam about
images. That clause is what falls.

# What was decided

**The layers join the one package tree as families.** Execution, progression, deliberation —
each a family whose members are interchangeable implementations, which is what
[capability](/domain/capability.md)'s own test always asked of a package and what the
superseded record sidestepped as "a different rationale." It passes now rather than being
excused: deliberation by bounded search and deliberation by a model are two members of one
family ([llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) already argues the
second); execution against hardware and execution against a stand-in likewise. The mind's
stores become a package the layers depend on. Review needs no move at all —
`packages/orexis-capability-review/` was in the tree from the start, and the other layers now
join it rather than standing apart from it.

**Need is what loads a layer.** Nothing grants one, and nothing loads all of them. A granted
capability hard-depends on the layers it needs — bidding needs the search, sensing needs
execution and the clock — so the load set is the transitive closure of the grants, and the
roster an agent carries is *derived* exactly the way its capabilities, its ACL and its bucket
are. The dumb device the superseded record deferred to a Containerfile variant falls out of
its own grants instead: an agent granted nothing that needs the search never loads it.

**Hard and soft are the two kinds of need, and both already have half a mechanism.** A
required annotation on a module (`beliefs` typed as what it needs) is a hard dependency: at
assembly it pulls the package providing that key into the load set, transitively (#455). An
optional annotation (`… | None`) is soft: it injects what is already there and loads nothing —
metrics is the canonical case, functioning absent, taken when present. `assembly/inject.py`
holds the required/optional split today; what #455 adds is only the pull.

**What stands from the superseded record, untouched:** the three-layer cut itself; a layer
imports only the contract of the layer below; the arrows are `pyproject.toml` dependencies
held to imports in both directions; the graph axis is not enforced by any of this and stays
with shapes and provenance. The generalisation the contract imports need — rule 2's one
written exception, a plug-in importing its family's contract, becoming the ordinary downward
rule between layers — is reconciled into `AGENTS.md` when the first layer package lands, not
before.

# What this refuses

**The root-tree placement, with its implementation already verified.** The measurements stand
and are worth keeping: the extraction was clean, the deps↔imports gate held a fourth root
tree, the image built and answered `import onboarding` with `ModuleNotFoundError`. None of
that was wrong; it enforced the arrows. What it could not do is derive the roster — root
trees are installed for everyone or no one, so "every agent carries all four" was not a
decision inside that placement but a consequence of it, and consequences that arrive
unexamined are how architecture drifts.

**Layers as granted capabilities, still.** The refusal in
[the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md) stands and this record
leans on it harder: a layer is not granted by a premise, it is depended on by a need, and the
tautological grant stays refused. The failure shape that record retired — a store built
unconditionally beside readers that arrive by grant — is answered better than either
predecessor managed: a store now travels in a package that arrives *because something needs
it*, so a modality nobody may write cannot be assembled at all.

# Seams left open

- **The loading pull is unbuilt** — #455 is the mechanism, and until it lands, a layer package
  loaded by the kernel's own declared dependencies is a legitimate intermediate state: the
  placement is right and the roster is temporarily universal, which is where the superseded
  record would have stopped permanently.
- **What remains at the root** is `assembly/` and whatever shell of `agent/` survives #452 —
  the container the author asked for at the start. Whether that shell is a package too, or the
  one thing that is nobody's package because it is what asks, is #452's to discover.
- **Family names are the implementing change's** (#451, #452), under the tree's own convention
  — the family is the second segment of the name, and the loader learns nothing.

The trigger for revisiting is the same as its predecessor's, sharpened: a contract module that
grows logic, or a hard dependency declared to smuggle a load the grants do not imply. The day
either appears, the boundary has moved and this record is due a rereading.
