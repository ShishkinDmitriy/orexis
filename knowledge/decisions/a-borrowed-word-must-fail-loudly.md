---
type: Decision
title: The kernel may borrow a package's word where losing it is loud
description: >-
  `agent/shapes.ttl` argued that scoping a shape by a lever would make the kernel depend on three
  packages, and the same file already targets one package predicate and joins through two more.
  The argument is too strong. What separates a legitimate borrowing from a defect is not the file
  kind and not "a dangling IRI merely matches nothing" — it is the DIRECTION the reference fails
  in. Measured on pySHACL over all nine occurrences of the kernel's RDF, five make the kernel say
  more when the package goes and are permitted, three are prefix lines no triple uses, and one —
  the freshness want's horizon — makes a want read as met forever. The keeper shape's accepted
  cost survives on a better argument than the one it gives.
status: accepted
timestamp: 2026-08-24T00:00:00Z
---

# Context — a file that contradicts itself

[The ratchet](https://github.com/ShishkinDmitriy/orexis/issues/334) counts the package-namespace
IRIs the kernel spells out. It found nine in the kernel's **RDF** that none of its three kinds
described, and parked them as `UNCLASSIFIED`, because deciding their fate was not a guard's
business. [#337](https://github.com/ShishkinDmitriy/orexis/issues/337) is that decision.

`ag:KeeperShape` says, in its own `rdfs:comment`, that it cannot be scoped by a lever because

> the kernel would then name `market:bidsIn`, `actuation:hasActuator` and `sensing:polls` — three
> packages the kernel would then depend on, which is the layering this whole arrangement exists to
> keep one-way

and accepts a stated cost to avoid it. Sixty-five lines above, the same file targets
`actuation:actuates`; two hundred lines below, it joins through `sensing:polls` and
`sensing:monitors`. `agent/desires.ru` takes three package prefixes and spells a fourth term out
inside a string. So the file's argument and the file's contents disagree, and one of them is
wrong.

The rule the kernel/package boundary actually holds is [package](/domain/package.md)'s, and it is
about Python. `lint-imports` refuses `agent` importing `packages`; nothing refuses `agent`
*saying* `sensing:polls`, and this record is what should have been refusing it.

# The rule

**A word the kernel borrows must fail loudly.** The kernel may name a term another package
declares exactly where the package's absence, or that term's disappearance, makes the kernel
say **more** — refuse more, warn more, target more. It may never name one where the loss makes
the kernel say **less**, because less is indistinguishable from well.

That is deliberately not a rule about file kinds, and the tempting one — *a dangling RDF
reference merely matches nothing, whereas a missing import crashes* — is **rejected**. Matching
nothing is not a mild failure here; it is the failure this repo has been bitten by four separate
times, catalogued as six of the seven naming forms in
[every-term-in-its-own-house](every-term-in-its-own-house.md) and as a trap in AGENTS.md. "It
degrades gracefully" and "it degrades silently" are the same sentence about different things, and
which one you have depends on the **position** the term sits in, not on whether the file is
Turtle.

Five positions, and the third column is the whole rule:

| position | what the term does | its loss |
|---|---|---|
| **selector** — a shape's target, a rule's `WHERE` premise | picks the population | empties a population the package's own presence created. **Permitted** |
| **excuse** — inside `FILTER NOT EXISTS` | suppresses a report | the report fires. **Permitted**, and noisier |
| **widener** — inside `OPTIONAL`, feeding a `COALESCE` | relaxes a bound | the bound tightens. **Permitted** |
| **judge** — a required pattern whose rows *are* the violation | decides pass or fail | no rows, so it passes. **Forbidden** |
| **spelling** — a `@prefix`/`PREFIX` line no triple uses | nothing | nothing. **Forbidden** as dead text, not as a dependency |

The selector row carries the load, so it is worth saying twice: a selector's loss is safe not
because the check stops running but because **what it was checking stopped existing**. `sh:targetSubjectsOf
actuation:actuates` goes vacuous exactly when there are no actuators to be vacuous about. That
is a coincidence of ownership, not a general property of targets, and a kernel shape targeting
one package's predicate to check a *different* package's obligation would fail this test even
though it is also a selector.

# What was measured

pySHACL 0.40.1, kernel `agent/shapes.ttl` alone against a five-triple fixture, run twice: once
with the sensing predicates, once with them renamed into a namespace nothing declares — which is
what a removed or renamed package looks like to a shape.

| | with sensing | without |
|---|---|---|
| a model's initial value of `45.0`, legal only through the subject it monitors | conforms | **Violation** — "an initial value must lie inside the range this model states" |
| a region in a property, with a sensor for it | conforms | **Warning** — "a desire in a property this agent polls no sensor for" |

Both go the loud way, and the first is the one worth noticing: the kernel's DeviceModel check gets
*stricter* without sensing, because the `OPTIONAL` that was raising the ceiling to the subject's
maximum stops binding and `COALESCE` falls back to `1.0`.

The freshness want goes the other way, and it is the only one that does. `agent/desires.ru`
builds the met-test as a string, naming the horizon in a required triple pattern. Two runs of that
query against one stale observation:

```
horizon term agrees      conforms=False  -> the want reads UNMET (violation)
sensing renamed it       conforms=True   -> the want reads MET (no violation)
```

An agent whose sensing package renamed `staleAfterS` would believe every reading current, for
ever, with no error anywhere. That is the defect, and it is not hypothetical arithmetic: the same
term is read a second time from `agent/readings.rq`, prefixed, where the ratchet cannot see it at
all.

Also measured: every one of the ten *named* package IRIs the kernel spells out today is genuinely
declared by that package's `ontology.ttl`. Nothing is broken right now, which is the right moment
to add the check that keeps it that way.

# The nine, ruled on

Eight allowlist keys, nine occurrences, as `tests/test_kernel_namespaces.py` counts them. Note
what the count is actually seeing in three of these: the ratchet scans **spelled-out** IRIs, so
for `agent/shapes.ttl` it sees the `@prefix actuation:` declaration and not the
`actuation:actuates` on line 78 that is the real reference. The count and the dependency are
different objects.

| occurrence | position | verdict |
|---|---|---|
| `shapes.ttl` `actuation#` ×1 — the prefix, serving `sh:targetSubjectsOf actuation:actuates` | selector | **permitted** |
| `shapes.ttl` `sensing#monitors` ×1 (l.108) — the `OPTIONAL` reaching the monitored subject's max | widener | **permitted** |
| `shapes.ttl` `sensing#monitors` ×1 (l.376) and `sensing#polls` ×1 (l.375) — the `FILTER NOT EXISTS` behind "a desire in a property this agent polls no sensor for" | excuse | **permitted** |
| `desires.ru` `sensing#` ×1 — the `PREFIX`, serving the freshness want's premise and the region intersection | selector | **permitted** |
| `desires.ru` `market#` ×1 and `actuation#` ×1 — `PREFIX` lines, used by no pattern in the file | spelling | **debt**: delete them |
| `ontology.ttl` `sensing#` ×1 — the `@prefix`; `sensing:` appears only in a `#` comment and inside an `rdfs:comment` string | spelling | **debt**: delete it |
| `desires.ru` `sensing#staleAfterS` ×1 — the required pattern in the built met-test | judge | **debt, and the real one**: the want reads met when it cannot be evaluated |

Five permitted, four debt, and three of the four are dead text rather than a dependency. The
kernel's real borrowings from its packages' vocabulary are fewer than the count suggests, and the
one that matters was not visible as a number at all.

# `ag:KeeperShape` — the cost survives, its reason does not

The comment's first argument fails. `market:bidsIn`, `actuation:hasActuator` and `sensing:polls`
in `sh:targetSubjectsOf` are selectors: remove market and the agents that bid in one are gone
with it, so the target set and the population it should cover empty together. SHACL unions
repeated targets, so the three-way scoping is expressible in one shape. The dependency the
comment refuses to incur is one the file incurs sixty-five lines earlier, on the same terms,
correctly.

Its second argument survives untouched and is [lever](/domain/lever.md)'s: a lever is an
instance, so no shape can target one.

But the reason to keep the shape as it is has been a third argument all along, and neither half of
the comment makes it. **Targeting the three predicates would be enumerating an open set.** Every
package that grants a lever would have to be added to a kernel shape by hand, and a package added
without that edit would silently take its agents *out* of the patience requirement — a selector
whose loss removes an obligation rather than a population, which is the forbidden direction of
this record's own rule, arriving by growth instead of by deletion. It is the registry smell
[capability-packages](capability-packages.md) refuses, wearing a shape.

So the accepted cost stands: an agent with a stake and no lever states a patience it never spends.
It is cheaper than it reads, because the runtime backstop already exists — `agent/keeper.py`
reads `KEEPING_PICKS` lazily, so an agent with nothing to commit about never asks for the number,
and one that somehow reaches a commitment without it raises and names the term. What the shape
buys over that backstop is the moment: `orexis-validate` refuses the world, rather than an agent
raising at its first commitment in production.

# What argued the other way

Recorded because the losing arguments are the ones a later reader will re-derive.

**"This makes the vocabulary boundary softer than the Python one, and packages are supposed to be
optional."** It does, and the softness is real: `lint-imports` gives a verdict at lint time and
a rule about failure direction gives one only to a reader. The answer is that the two boundaries
are not the same boundary. Python is *executed by* the kernel, so an import is a hard dependency
by construction. RDF is *read together with* the packages' RDF into one union graph — the kernel's
shapes and a package's shapes are the same document to pySHACL — so a kernel shape naming a
package predicate is closer to two packages agreeing on a word than to one calling the other.
`test_the_kernel_stands_alone_with_no_packages_at_all` is the claim that is actually load-bearing,
and none of the five permitted occurrences threatens it: measured above, the kernel alone gets
noisier, not quieter.

**The strict reading plus a real fix — have the kernel target a term of its own and let packages'
shapes narrow it.** Attractive, and it does not survive contact with the one case where it could
be tried. `ag:SimulatedActuatorShape` could target `sosa:Actuator` instead of subjects of
`actuation:actuates`, spelling the dependency in a standardised namespace. But a world types its
valve as `actuation:Valve`, and `sosa:Actuator` reaches it only through the `rdfs:subClassOf` that
the actuation package's own ontology declares and
[one-graph-both-engines-read](one-graph-both-engines-read.md) materialises. The dependency is
identical and the spelling hides it. A rule that rewards hiding a dependency in someone else's
namespace is worse than the dependency.

**Let the count be the rule — every occurrence is debt, ratchet to zero.** This is what
[#334](https://github.com/ShishkinDmitriy/orexis/issues/334)'s last bullet plans, and it is
tidy. It is also how the one real defect stays hidden: `sensing#staleAfterS` and
`@prefix sensing:` are one occurrence each and are not remotely the same size of problem, while
`agent/readings.rq`'s prefixed read of the same term is zero occurrences and is the same problem
again. A count ranks by form; this rule ranks by consequence.

# Consequences

- `ag:KeeperShape`'s comment is rewritten to the surviving argument. No target and no constraint
  moved — the shape's behaviour on every shipped world is unchanged.
- [the-mind-is-not-a-package](the-mind-is-not-a-package.md) makes the same claim in its "What the
  shapes cost" section and carries an amendment pointing here.
- The ratchet's `UNCLASSIFIED` block is reclassified in place: each entry now says permitted-and-why
  or debt-and-what-removes-it. What the test *enforces* is untouched.
- [package](/domain/package.md)'s count was three occurrences stale — twenty-one when the ratchet
  landed, nineteen since #339 retired the reflex. Corrected, and the ratchet named as the count
  of record so the number is not restated in two places again.

# Seams left open

- **Nothing enforces this rule.** It is a rule a reviewer applies, because the position a term
  sits in is not something a scan can classify — `OPTIONAL` versus a bare pattern is parseable,
  but whether a pattern's absence removes an obligation is not. What *is* mechanisable is the
  narrower thing filed as [#344](https://github.com/ShishkinDmitriy/orexis/issues/344): that a
  borrowed term still exists.
- **The rule says nothing about a package borrowing another package's word.** Packages already do
  — `market/effects.ttl` names `actuation:hasActuator` — and the failure-direction question
  applies there identically. It is out of scope here because the kernel/package direction is the
  one with a contract behind it, and a package-to-package rule wants the
  [premise trap](one-graph-both-engines-read.md) argued alongside it.
- **The count and the dependency stay different objects.** The ratchet will go on counting a
  `@prefix` line as one reference and a prefixed use as none. That is the right instrument for
  what it does — hold the number down while #334's remaining work lands — and the wrong
  instrument for this rule, so the two coexist rather than one absorbing the other.
