---
type: Decision
title: The kernel names no package's word, and the ratchet is how it gets there
description: >-
  `agent/shapes.ttl` argued that scoping a shape by a lever would make the kernel depend on three
  packages, and the same file already targets one package predicate and joins through two more.
  The first ruling here permitted the borrowings whose absence fails LOUDLY, and the sovereign
  overruled it: packages are optional and the core depends on none of them, in RDF as in Python,
  and a claim the whole architecture rests on cannot carry a carve-out. So all nine occurrences in
  the kernel's RDF are debt. The loudness analysis survives with its authority demoted — it
  licenses nothing and ORDERS the debt, measured: one occurrence makes a want read as met for
  ever, and the rest only make validation noisier.
status: accepted
timestamp: 2026-08-24T00:00:00Z
---

# Context — a file that contradicts itself

[The ratchet](https://github.com/ShishkinDmitriy/orexis/issues/334) counts the package-namespace
IRIs the kernel spells out. It found nine in the kernel's **RDF** that none of its three kinds
described, and parked them as `UNCLASSIFIED`, because deciding their fate was not a guard's
business. [#337](https://github.com/ShishkinDmitriy/orexis/issues/337) is that decision.

`orexis:KeeperShape` says, in its own `rdfs:comment`, that it cannot be scoped by a lever because

> the kernel would then name `market:bidsIn`, `actuation:hasActuator` and `sensing:polls` — three
> packages the kernel would then depend on, which is the layering this whole arrangement exists to
> keep one-way

and accepts a stated cost to avoid it. Sixty-five lines above, the same file targets
`actuation:actuates`; two hundred lines below, it joins through `sensing:polls` and
`sensing:monitors`. `agent/desires.ru` took three package prefixes and spelled a fourth term out
inside a string (it takes none now — see the freshness section below). So the file's argument and
the file's contents disagreed, and #337 asked which of them was wrong.

**The contents were.** The comment states the rule; the rest of the file is behind on it.

# The rule

**The kernel names no package's word.** Not in Python, where `lint-imports` has held it since the
mind came home, and not in RDF, where nothing has held it at all. A package is optional and the
core depends on none of them — that is [package](/domain/package.md)'s claim, and it does not
survive being true of imports and negotiable for vocabulary.

There is no exception clause, and its absence is the point rather than an oversight. The exception
this record originally proposed, and why it was refused, is below.

**The relaxation is the allowlist, and that is already the right instrument.**
`tests/test_kernel_namespaces.py` tolerates today's occurrences one at a time, each carrying what
removes it, failing on a new one and failing again when an entry stops occurring. That is what
"strict, but not this afternoon" looks like when it is written down instead of remembered: the
list shrinks to zero and the ratchet becomes the prohibition, which is
[#334](https://github.com/ShishkinDmitriy/orexis/issues/334)'s last bullet, unchanged.

# What was ruled first, and why it was overruled

This record first ruled that a borrowing is legitimate where losing the package makes the kernel
say **more** — refuse more, warn more, target more — and illegitimate only where the loss makes it
say less. Five of the nine passed that test and were to be permitted permanently.

The sovereign refused it, in their own terms: the decision should be that the code does not use
anything from packages, because **packages are optional and the core does not depend on them**.
Relax for now; be strict at the end.

The argument that beats the loudness rule is not that the measurements were wrong — they were not,
and they are below — but that **optionality is the claim the whole architecture rests on**, and a
claim with a carve-out cannot carry that weight.
`test_the_kernel_stands_alone_with_no_packages_at_all` would have gone on passing under either
rule, which is exactly the problem: it proves the kernel BUILDS without packages, and the loose
rule would have quietly restated the promise as "the kernel does not depend on a package in ways
that go quiet". That sentence is true and is not what anyone was told. Every later reader would
have had to run a five-way position analysis to know whether a line was allowed, and a rule that
takes a page to apply is a rule that gets applied wrong.

A smaller reason, which also holds: **the permitted set was not stable.** An `OPTIONAL` is one
edit away from a bare pattern, and a widener that becomes a judge changes category without changing
a word of the argument around it. The exception would have needed a reviewer to re-derive the whole
taxonomy at every touch — a maintenance burden shaped exactly like the registry
[capability-packages](capability-packages.md) exists to refuse.

# The loudness analysis survives as triage

Demoted, not withdrawn. It licenses nothing; it **orders the debt**, which is the question the
strict rule leaves open and does not answer: everything must go, so what goes first?

Five positions a borrowed term can occupy, and the last column now reads as urgency rather than
permission:

| position | what the term does | its loss | when |
|---|---|---|---|
| **judge** — a required pattern whose rows *are* the violation | decides pass or fail | no rows, so it passes | **first**: a check that stops checking and says nothing |
| **spelling** — a `@prefix`/`PREFIX` line no triple uses | nothing | nothing | next, because it is free: delete the line and nothing moves |
| **selector** — a shape's target, a rule's `WHERE` premise | picks the population | empties a population the package's presence created | later; wrong, and it fails in the safe direction |
| **excuse** — inside `FILTER NOT EXISTS` | suppresses a report | the report fires | later, and noisily |
| **widener** — inside `OPTIONAL` feeding a `COALESCE` | relaxes a bound | the bound tightens | later, and noisily |

The distinction #337 floats — *a dangling RDF reference merely matches nothing, whereas a missing
import crashes* — is rejected in both readings. As a permission it is what the sovereign overruled.
As a **reassurance** it was never true: matching nothing is the failure this repo has been bitten by
four separate times, catalogued as six of the seven naming forms in
[every-term-in-its-own-house](every-term-in-its-own-house.md) and as a trap in AGENTS.md. "It
degrades gracefully" and "it degrades silently" are the same sentence about different things.

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

The freshness want goes the other way, and it is the only one that does. `agent/desires.ru` builds
the met-test as a string, naming the horizon in a required triple pattern. Two runs of that query
against one stale observation:

```
horizon term agrees      conforms=False  -> the want reads UNMET (violation)
sensing renamed it       conforms=True   -> the want reads MET (no violation)
```

An agent whose sensing package renamed `staleAfterS` would believe every reading current, for
ever, with no error anywhere. That is why it is first in the queue, and it is not hypothetical
arithmetic: the same term is read a second time from `agent/readings.rq`, prefixed, where the
ratchet cannot see it at all.

**PAID, and by a change that was not about this** ([#331](https://github.com/ShishkinDmitriy/orexis/issues/331),
[a-lever-an-agent-cannot-pull-is-not-a-lever](/decisions/a-lever-an-agent-cannot-pull-is-not-a-lever.md)):
the freshness want is derived by `packages/orexis-capability-sensing/desires.ru` now, because its premise
is an instrument and that is sensing's fact, so the horizon term is spelled where it is owned and
`desires.ru`'s three prefix lines went with the rule that had left them behind. The judge position
is DISSOLVED rather than moved into the package. The met-test says what the agent wants — a
reading of this exists, made by this instrument, taken within the horizon — so a term that stops
resolving takes the inner pattern with it, the NOT EXISTS holds, and the want reports UNMET. That
is the direction this record asks for, reached by stating the goal positively instead of by
guarding the borrowing, and it is the general lesson worth taking from the row: a shape that hunts
for what would disappoint you is satisfied by having nothing at all, which is what makes its
borrowed terms judges in the first place.

Also measured: every one of the ten *named* package IRIs the kernel spells out today is genuinely
declared by that package's `ontology.ttl`. Nothing is broken right now, which is the right moment
to add the check that keeps it that way while the debt is worked off.

# The nine, in the order they should go

> **Rows 1 and 2 are paid, and row 3 is not.** #331 moved the freshness want into sensing, which
> took `desires.ru`'s four occurrences — the judge and two of the three spellings — with it.
> `agent/ontology.ttl`'s `sensing:` prefix is untouched and still #343's. Five occurrences remain
> and the order below is unchanged for them; the table is left whole because the ORDERING is this
> record's argument and a row struck out still teaches what its position means.

All nine are debt. Eight allowlist keys, nine occurrences, as `tests/test_kernel_namespaces.py`
counted them on the day this was written. Note what the count is actually seeing in three of these: the ratchet scans
**spelled-out** IRIs, so for `agent/shapes.ttl` it sees the `@prefix actuation:` declaration and
not the `actuation:actuates` on line 78 that is the real reference. The count and the dependency
are different objects, which is one reason the count alone could never have ordered this list.

| # | occurrence | position | why it sits here |
|---|---|---|---|
| ~~1~~ | ~~`desires.ru` `sensing#staleAfterS` ×1 — the required pattern in the built met-test~~ | judge | **PAID (#331)**: the want moved to sensing and the met-test was turned positive, so the term is owned and its absence is loud. [#342](https://github.com/ShishkinDmitriy/orexis/issues/342) |
| ~~2~~ | ~~`desires.ru` `market#` ×1 and `actuation#` ×1 — `PREFIX` lines used by no pattern in the file~~ | spelling | **PAID (#331)**, with `sensing:` beside them, which #337 filed separately as a selector. [#343](https://github.com/ShishkinDmitriy/orexis/issues/343) |
| 3 | `ontology.ttl` `sensing#` ×1 — the `@prefix`; `sensing:` appears only in a `#` comment and inside an `rdfs:comment` string | spelling | the same, and the same issue |
| 4 | `shapes.ttl` `sensing#monitors` ×1 (l.108) — the `OPTIONAL` reaching the monitored subject's max | widener | wants a kernel-owned way to say "the range this thing is measured against"; loud meanwhile |
| 5 | `shapes.ttl` `sensing#monitors` ×1 (l.376) and `sensing#polls` ×1 (l.375) — the `FILTER NOT EXISTS` behind the no-sensor warning | excuse | the warning is arguably sensing's to raise rather than the kernel's; loud meanwhile |
| 6 | `shapes.ttl` `actuation#` ×1 — the prefix, serving `sh:targetSubjectsOf actuation:actuates` | selector | wants the simulation package [every-term-in-its-own-house](every-term-in-its-own-house.md) says does not exist yet; loud meanwhile |

Two of the six rows are cheap deletions, one is a real bug, and the last three are each waiting on
somewhere for the knowledge to live — which is the honest reason they are last, rather than a claim
that they are fine where they are.

# `orexis:KeeperShape` — the comment was right, and it now has a better reason

Under the strict rule the comment's original claim needs no defending: it says the kernel must not
name `market:bidsIn`, `actuation:hasActuator` and `sensing:polls`, and that is the rule. The shape
is not the file's problem — the six rows above are.

Its second argument stands too, and was the retired `lever.md`'s: a lever is an instance, so no
shape can target one.

There is a third argument that neither half of the comment makes, and it is the strongest, because
it forbids the lever half **even for someone who rejected the rule entirely**. Targeting the three
predicates would enumerate an **open set**. Every package that grants a lever would have to be
added to a kernel shape by hand, and one added without that edit would silently take its agents
*out* of the patience requirement — an obligation removed rather than a population, with no engine
anywhere to say so. It is the registry smell [capability-packages](capability-packages.md)
refuses, wearing a shape.

So the accepted cost stands: an agent with a region want and no lever states a patience it never spends.
It is cheaper than it reads, because the runtime backstop already exists — `packages/orexis-agent-progression/keeper.py` reads
`KEEPING_PICKS` lazily, so an agent with nothing to commit about never asks for the number, and one
that somehow reaches a commitment without it raises and names the term. What the shape buys over
that backstop is the moment: `orexis-validate` refuses the world, rather than an agent raising at
its first commitment in production.

# What argued the other way

Recorded because the losing arguments are the ones a later reader will re-derive — including this
record's own first ruling, above.

**"The strict rule plus a real fix — have the kernel target a term of its own and let packages'
shapes narrow it."** Attractive, and it does not survive contact with the one case where it could
be tried. `ag:SimulatedActuatorShape` could target `sosa:Actuator` instead of subjects of
`actuation:actuates`, spelling the dependency in a standardised namespace. But a world types its
valve as `actuation:Valve`, and `sosa:Actuator` reaches it only through the `rdfs:subClassOf` that
the actuation package's own ontology declares and
[one-graph-both-engines-read](one-graph-both-engines-read.md) materialises. The dependency is
identical and the spelling hides it. **This is the trap for whoever pays row 6 down**: moving to a
standard namespace turns the ratchet green while changing nothing, and the honest fix is for the
knowledge to move rather than the spelling.

**"The vocabulary boundary is not the same kind of thing as the Python one."** True, and the best
case the loose ruling had. RDF is *read together with* the packages' RDF into one union graph — the
kernel's shapes and a package's shapes are the same document to pySHACL — so a kernel shape naming
a package predicate is closer to two packages agreeing on a word than to one calling the other. It
loses anyway: what an agent validates against is the union, but what the repository promises is
that `agent/` stands alone, and a promise that holds only when everything happens to be loaded is
not the promise that was made.

**"Let the count be the rule — everything is debt, ratchet to zero, and stop there."** Half right,
and it is now the rule. What a count cannot do on its own is order the list:
`sensing#staleAfterS` and `@prefix sensing:` are one occurrence each and are not remotely the same
size of problem, while `agent/readings.rq`'s prefixed read of the same term is zero occurrences and
is the same problem again. A count ranks by form. That is what the triage table is for, and it is
why the taxonomy survived its demotion instead of being deleted along with the ruling it was
written to support.

# Consequences

- `orexis:KeeperShape`'s comment keeps its original claim and gains the open-set argument. No target
  and no constraint moved — the shape's behaviour on every shipped world is unchanged.
- The ratchet's `UNCLASSIFIED` block is reclassified in place: nine occurrences, all debt, in the
  order above, each saying what removes it. What the test *enforces* is untouched, and **#334's
  endgame is restored** — the list empties and the ratchet flips to a prohibition.
- [package](/domain/package.md)'s count was three keys stale — twenty-one when the ratchet landed,
  eighteen since #339 retired the reflex. Corrected, and the ratchet named as the count of record
  so the number is not restated in two places again.
- [the-mind-is-not-a-package](the-mind-is-not-a-package.md) says the same thing about the lever
  half that `orexis:KeeperShape` does, and under this rule it needed no amendment. It briefly carried
  one, from this record's first ruling; it was reverted.

# Seams left open

- ~~**Nothing enforces the rule beyond the count.**~~ Closed with
  [the-region-want-is-sensings-want](the-region-want-is-sensings-want.md)'s third step. The ratchet reads the
  prefixed form where it means something — a query string, a rule or a shape with its prose
  stripped — scans for every namespace the loader reports rather than five families by hand, and
  resolves every term it finds against what the ontologies declare (#344). `agent/world.py`'s
  market vocabulary had already left with the wiring; what the widening found was the bus.
- **The rule says nothing about a package borrowing another package's word.** Packages already do —
  `market/effects.ttl` names `actuation:hasActuator` — and that is a different question, since
  neither of them claims to stand alone. Out of scope here because the kernel/package direction is
  the one with a contract behind it.
- **Three of the nine have nowhere to go yet.** Rows 4, 5 and 6 each wait on a home for knowledge
  that has none: a kernel-owned way to name a measurement range, an owner for the no-sensor
  warning, and the simulation package that does not exist. They are debt with a prerequisite, which
  is why the table says so rather than pretending an issue could close them today.

# Paid since — the keeper, and the actuator shape

Three more rows left the allowlist in one change. The keeper's copy of the market's direction
(`market:Raises`/`market:Lowers`, looked up by the keeper when a watch opened) became something
the ACTOR said: `expect(rises=…)`, or the sign of the delta it sized — the actor always held
the word (and since #510 it says neither: the step's own prediction is what the watch holds,
and the actor passes only its tolerance). The keeper's two lookups of the sensing family — a look once the watch opens, and the
cadence that sets how long a reading takes to arrive — went the same way: the actor nudges its
own sensing and passes `seeing_s`. And `ag:SimulatedActuatorShape`, the selector targeting
`actuation:actuates`, is `actuation:SimulatedActuatorShape` in that package's own shapes.
(AMENDED. It landed one package short: every term it CHECKS is `mqtt:`, so it is
`sim:StandInReportsShape` now — it went to the transport first and one package further on the
same day, once the deletion test was run the way deletions actually happen. The note left on it — *a shape targeting
`actuation:actuates` is this package's, whatever the term it checks belongs to* — had the ends the
wrong way round, which
[a-shape-belongs-to-the-vocabulary-it-checks](/decisions/a-shape-belongs-to-the-vocabulary-it-checks.md)
settles by asking what a deletion leaves behind. THIS record's own ruling stands: the kernel may
name no package word at either end.) What
remains on the list is the two sensing terms in the desire warning shape, the namespace
constants onboarding interpolates, and the migration destinations — and `agent/world.py`, which
the scan cannot see and the next change is about.

# Paid since — the region want, the widened scan, and what it found

The desire warning shape went to sensing with the region (`sensing:UnwatchedRegionShape` now — it was `BeyondSurvivalShape` then, and #275 renamed it for what it actually checks), and the
kernel's `sosa:` went with it: `store.PREFIXES` no longer declares a vocabulary the kernel does
not speak, and the `SOSA` constant is `onboarding/namespaces.py`'s. The scan then widened — every
namespace, both forms, resolved — and what it found in the kernel was not the market vocabulary
this record feared but the BUS: four `mqtt:` terms in `agent/world.py`'s one query, and the
reachability check in `orexis:SimulatedDeviceShape`. Both are on the list as a fifth kind, with the
transport package answering "where is the bus" itself as what removes them. The
namespace constants — the ratchet's third kind, twelve once every namespace was scanned for —
have since left the way `SOSA` did, to `onboarding/namespaces.py`: nothing in the kernel read
them, only the sovereign's generators. What the list holds now is the bus, the migration
destinations, and one shape widener.

# Paid since — the bus

The fifth kind is gone, and the concept behind it with it. How an agent reaches its society is
a capability the fact of a bus grants ([the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md)):
the `mqtt:MessageBus` query, the credential, paho, the delivery loop and the watchdog all
live in `packages/orexis-transport-mqtt/`; the reachability half of the simulated-device shape is
`sim:StandInReachableShape`; `Module` defines no messaging hook. What the list holds
now is the migration destinations and one shape widener, and the kernel names no package's
word in any query, rule, shape or constant.
