---
type: Decision
title: The mind is not a package, and the kernel is not discovered
description: >-
  Three capability packages held the mind — desire, intention, deliberation — while the STORES
  they read were built for every agent unconditionally, three lines above the modules in
  `Agent.__init__`. A modality nobody may write is not a modality. All three dissolve into
  `agent/`, the base vocabulary comes back with them (a family of exactly one is not a family),
  and the kernel stops being discovered: it is what discovers. What this buys is a sentence that
  was said long before it was true — every package is optional — as a contract `lint-imports`
  keeps and a test proves against an empty tree.
status: accepted
timestamp: 2026-08-23T00:00:00Z
---

# Context

[the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) drew this line once and stopped
halfway. It ruled that **what a mind CONTAINS is the kernel's and HOW a mind reaches them is the
packages'**, moved the mental-state TERMS into `ag:`, and left the CODE where it was. That was a
defensible place to stop, and it did not survive contact with what the code already did.

`Agent.__init__` built `Desires` and `Intentions` for every agent, unconditionally, before any
capability was consulted. Then it built the modules that read them from a registry keyed on
grants. So an agent could hold a desire store and no way to want, an intention store and nothing
that writes it. **A modality nobody may write is not a modality**, and nobody had put the two
facts on the same page.

# What was decided

**The mind is the kernel's — the states, the stores, and the code over them.** Three packages
dissolve:

| was | is | granted by |
|---|---|---|
| `desire:Deducing` | `agent/deducer.py`, `agent/regions.py` | nothing |
| `desire:Owing` | `agent/owing.py` | nothing |
| `intention:Keeping` | `agent/keeper.py` | nothing |
| `deliberation:Reflex`, `deliberation:Planning` | `agent/deliberator.py` — ONE class | nothing |

And the base vocabulary comes home: `packages/core/orexis/` was a family with exactly one member,
forever, that every other package layers on and nothing can remove. That is not a package, it is
the base. AGENTS.md already states the test, about OKF types — *a type that falls to one member is
a type to fold back*.

## The family that did not survive its own evidence

`deliberation` is the sharpest case, because it looked most like a real family: two members, both
shipping. `PlanningModule` **subclassed** `ReflexModule`, called `super().propose()` first, and
added one clause asking `_my_shop_needs` — which answers only for a property that is the agent's
own vessel's stock, and returns None for every other agent.

A member that CONTAINS the other, whose extra branch is inert everywhere else, is not an
interchangeable implementation. [capability](/domain/capability.md)'s test is whether the HOW
could differ; here it differed by a condition on the data, which is a branch. They are one class,
and no shipped behaviour moved.

The merge had one sharp edge worth recording because it nearly landed: the reflex's early returns
— no reading, no desire module, **no aim** — meant *the gap says nothing*, not *stop*, because
`super().propose()` returning None fell through to the shop. Inlining them would have left a
dealer with no aim quietly refusing to refill.

Both clauses have since been deleted whole. The merge left one class asking two questions, and
the second — does taking this lever leave me better off — subsumed the first; see
[a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md), including
what the shop clause took with it. This record's claim is untouched by that: a family whose
members contain one another was never a family, and it is now not even two clauses.

## Consulting is re-seated, not deleted

`desire:Consulting`, `deliberation:Consulting` and the unwritten open-minded keeper were the real
alternatives, and they remain real. But **which** deliberator answers is a CHOICE, and this
project puts choices in beliefs rather than in grants — so each becomes a pick an agent's review
may move inside its mandate, not something its world derives once at genesis. Everything
[llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) fixes about the model seat stands.

## Absence follows the fact, not the grant

The rule that made the dissolution safe, and it recurs three times.

[capability-packages](/decisions/capability-packages.md) gave modules a reporting hook whose
docstring says *the ABSENCE of its lines is itself a reading — it says this agent was never
granted that ability, rather than that it has had nothing to say*. A kernel deliberator running
in every agent would have turned that into a row of zeros on every stakeless dashboard.

So: no wants, no rows (`Deliberator.series`). No stake, no patience read (`Keeper.beliefs`, lazy
— an unconditional keeper reading a required pick at construction killed `world/sensing`'s agent
and 25 fixtures). No ranges, no regions. The reading survives and says something truer than it
did: what is the case for this agent now, rather than what its world provisioned for it once.

**The same move runs through the tests.** Four were rewritten from grant to fact rather than
deleted — the dealer's clause asked directly instead of `provider()` returning a planner, the
city's empty regions and the fern's empty honoured rows instead of `OWING`/`DEDUCING` set
membership. A test that asserts a grant is a test that dies with the grant; a test that asserts
the fact underneath outlives it.

## What the shapes cost

A capability scoped its shapes; with no capability, `ag:KeeperShape` and the desire shapes target
the **stake alone** — `ag:actsFor` a subject that states what it needs.

The old premises were a stake AND a lever, and **the lever half could not follow**.

**AMENDED — the conclusion holds and this paragraph's reason for it was wrong.** It said that
saying the lever half would make the kernel name `market:bidsIn`, `actuation:hasActuator` and
`sensing:polls`, three packages it must not depend on. `agent/shapes.ttl` already targets an
actuation predicate and joins through two sensing ones, and that is legitimate: a package term
in a shape's target is a selector, and removing the package empties the target set and the
population it was checking together. What actually forbids the lever half is that the three
predicates are an OPEN set — a fourth lever package added without an edit here would silently
drop its agents out of the requirement, which is an obligation removed rather than a population.
See [a-borrowed-word-must-fail-loudly](a-borrowed-word-must-fail-loudly.md), which measures all
nine of the kernel's RDF borrowings. A [lever](/domain/lever.md) is an instance besides: the
`via` of a menu row derived from each package's own `affordances.rq`, with no term to target on.

Cost, stated: an agent with a stake and no lever would now state a patience it never spends. No
world has one.

# What it buys, and it is checkable

**`lint-imports` gained the contract this series was for**: *the kernel loads packages and never
reaches into one*. It could not be stated before, and the violations were not theoretical —
`agent/desire.py` and `agent/genesis.py` imported `packages.capability.desire.graphs`, a module
whose entire content was re-exporting `agent.ontology.obligations_graph`. The kernel imported a
package to get its own function handed back. Its docstring even explained the layering problem it
was recreating.

**`test_the_kernel_stands_alone_with_no_packages_at_all`** proves the sentence: with `packages/`
absent the build is the kernel alone, and it is a working one. Narrower than it sounds and
deliberately so — every shipped world names `water:`, `mqtt:` and `part:` terms and would not
validate. The claim is that the thing which LOADS packages does not need one.

**And the loader stopped guarding an ordering it no longer has.** The base used to be sorted to
the front with a comment warning that it *"happens to sort before `plant/water`, and that is not
a thing to rely on"*. A thing outside the tree cannot be sorted wrong.

# A guard that greps cannot see a declaration

Found by writing the bug. Five terms were inserted into the middle of `ag:Intention`'s
`rdfs:comment` — the anchor took the first blank line after the class, and that line falls inside
the literal. Turtle nested in a literal parses fine and adds nothing: 23 triples were prose.

Three guards were positioned to catch it. `tests/test_intention.py` went green, because a SHACL
`sh:path` matches data whether or not the term is declared.
`test_no_source_names_a_moved_term_in_the_kernel_namespace` went green, because it read the
vocabulary by REGEX and lines inside a literal begin at column zero. `onboarding/linker.py` caught
it — and only because it had been widened to read `agent/*.py` an hour earlier, in this same work.

`_kernel_terms()` parses now, and `test_the_vocabulary_declares_what_it_appears_to_declare` names
the shape: **anything the text offers as a declaration must survive parsing, or it is
documentation wearing a declaration's clothes.** This is the objection AGENTS.md already records
against the vendored OKF check — *it greps rather than parses* — turned on our own ontology guard.

# Five guards were scoped to a tree, and a tree is a layout

The pattern behind every defect above, stated once because it is the transferable part.

`one-tree-and-one-mechanic` records this failure twice and calls it *"non-empty is not the same as
complete"*. This series hit it five more times, all in the same direction — a guard globbing
`packages/**` that silently stopped covering what it was named for as the kernel grew:

| guard | stopped seeing |
|---|---|
| `test_inference` rule scan | `agent/rules.ru` — one case, under a comment asserting every `.ru` belongs to a package |
| `test_knowledge._declared` | the kernel's ontology, then its shapes |
| `test_knowledge`'s dictionary census | a second hand-maintained copy of the same list |
| `test_layout` doc-term census | shape names the entry documents cite |
| `onboarding/linker` | every IRI in `agent/*.py` |

**None of them failed. They narrowed**, which is invisible: a guard can check that its glob still
matches SOMETHING, and four of these had exactly that assertion sitting beside them, passing.

Two things found only because a widened guard could finally see: `ag:amountL`, written by the
ledger and read by three of the market's effect rules and declared by no ontology for months; and
five terms of this very change sitting inside an `rdfs:comment` as prose. And one found only by
diffing collected test ids — six tests of the region arithmetic that went into the bin with the
desire package while the suite stayed green at 1302. They are `tests/test_regions.py` now.

**The fix each time was the same: ask the loader what to scan, rather than globbing a tree.**
Nothing enforces that, and it is the obvious next guard — a guard on the guards, which is a thing
this repo already has three of and could use a fourth.

# Two scans that went quiet rather than red

Both widened here, and both found something the moment they could see:

- `test_only_the_keeper_writes_the_intentions_graph` scanned `packages/` while
  `agent/intentions.py` and `agent/genesis.py` had named the ledger graph the whole time. The
  guard could not see the second pen because it looked only at the tree the pen was not in.
- `onboarding/linker.py` had never read `agent/*.py`. Widening it also produced six false
  positives from `agent/vocabulary.py` — the migration map, whose every left-hand side is by
  definition an IRI nothing declares — which would have broken `tests/test_linker.py`. Exempt by
  name with a reason, never by a pattern something could meet by accident.

# The five survivors were checked, and the family earns its keep

Asked once the mind was out: if three capabilities were really the kernel, is `capability` a
container for one idea? No — and the test that separates them is worth having written down,
because it is not the one that looks obvious.

It is **not** "is it universal". `reporting` is granted to every agent by a rule whose WHERE
clause is `?agent a ag:Agent` — a premise that asks nothing — and it is still a capability.
[telemetry-is-a-mandatory-capability](telemetry-is-a-mandatory-capability.md) settled that
exact question and its argument holds: mandatory and uniform are different, counting stays in
the kernel because counting could not differ, and `reporting:Announcing` is a second member with
an independent failure mode — a bucket that has gone and a bus that has gone fail separately,
and a member reporting over the bus cannot report having lost the bus.

The test that actually separates them is **whether the kernel already assumed the thing**:

| | granted by | does the kernel assume it? |
|---|---|---|
| `sensing`, `actuation`, `market` | equipment, a market position | no — an agent without an actuator cannot actuate, and nothing in the kernel pretends otherwise |
| `review` | a mandate whose ends differ | no — an agent given no room holds no revisable pick |
| `reporting` | nothing; every agent | the COUNTING, yes — and that half is already kernel, deliberately. The shipping is not |
| ~~`desire`, `intention`, `deliberation`~~ | a stake, a stake and a lever | **YES**, and that was the defect: the stores were built for every agent before any grant was read |

The mind failed because its stores were unconditional while its readers were granted, so an
agent could hold a modality nobody could write. No survivor has that shape. `reporting` comes
closest and is the one that already made the split on purpose, in the right place.

`actuation` is a family of one and stays one: what makes it a capability is not a second member
but that its premise is genuinely absent for most agents. A family of one whose premise is a
tautology would be the thing to fold — and `reporting` is not that either, because its second
member is argued rather than imagined.

# Seams left open

- **`agent/` is large**, and that was accepted rather than overlooked: cohesion was the point,
  and the boundaries that enforce anything (`lint-imports`, the `Containerfile` COPY list) got
  sharper. The tree never distinguished a 200-line file from a 600-line one.
- **The kernel's shapes name `mqtt:` and `actuation:`** — two prefixes declared in
  `agent/shapes.ttl` before any of this. The layering inversion this record refuses for the mind
  already exists in miniature there, and was left alone rather than widened.
- **Which deliberator, as a pick, is unbuilt.** `ag:deliberatesBy` is not declared, because a
  reserved term nobody has an argument about is speculation. The argument exists
  ([llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md)); the term arrives with the
  implementation.
- **A ledger row's IRI changed prefix**, from `intention:intent_…` to `ag:intent_…`. Opaque
  identifiers read by pattern, so a pre-split volume's rows stay readable; nothing migrates them.
