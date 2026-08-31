---
type: Decision
title: The action is the kind — means was the joint, and the joint is one node
description: >-
  `orexis:Means` was a class of five individuals that nothing read. A means existed to be the
  joint between three surfaces — an affordance row, an effect rule, an intention — and
  an-action-is-one-node made those surfaces one node, so a name whose only job was to point at
  that node one-to-one was a second owner of it. Retired: an intention commits to the action
  (`orexis:by`), a row carries it, a trace weighs it, the packages' short-lived means
  (`market:Acquire`, `sensing:Observe`, …) go with the class, and the kernel's ontology keeps
  `orexis:Action` and no individual of anything.
status: accepted
timestamp: 2026-08-26T00:00:00Z
---

# What was true before

Five means, each typed `orexis:Means`: Observe, Actuate, Acquire, Apply, Offer. `means.md` called
a means "the joint" — the one term an affordance row offered, an effect rule attached to
(`orexis:effectOf`), and an intention committed to (`orexis:by`), so that three parts of the design
that knew nothing of each other could be joined without storing a correspondence. That was
true and useful while the three were three files.

[an-action-is-one-node](/decisions/an-action-is-one-node.md) folded them: one `orexis:Action`
node carries the precondition, the effect and the taker. From then on every shipped means
pointed at exactly one action and every action named exactly one means — `orexis:means` was a
one-to-one edge whose two ends could never differ. The sovereign asked what `orexis:Means` was
for, and the grep answered: nothing reads it. No query asks `?x a orexis:Means`, no shape targets
it, no code names it. It was the `orexis:Mode` argument again — a term whose whole content is
restated by another node is a second owner of that content.

# What is decided

**The [action](/domain/action.md) is the kind.** What a row carries (`Affordance.action`),
what an intention commits to (`orexis:by`), what a trace weighs (`orexis:wouldTake`) and what the
keeper keys patience and suspicion on is the action node: `sensing:Observing`,
`actuation:Dosing`, `market:Acquiring`, `market:Offering`, `market:Serving` — and
`market:Presenting`, the buyer's hold on a won claim, which needed a node the moment an
intention could name nothing else. `orexis:Means`, `orexis:means` and the five individuals are
deleted; the kernel's ontology keeps `orexis:Action` and names no individual of anything.

**Two acts are two commitments.** Where a means keyed the patience, two actions of one kind
would have absorbed each other's impulse; keyed on the action they are distinct. No shipped
package has two, and this is the one semantic shift, stated so nobody rediscovers it as a bug.

**The series tag keeps the retired word.** `metrics.event(... means=...)` still tags an
intention event `means`, carrying the action's local name — the same rule as `agent_want`: a
measurement name is an external surface with history behind it, and renaming it splits every
series at the cutover.

**Old ledgers migrate to the node.** Every older spelling — the intention package's, the
kernel's, and the packages' short-lived means — lands on the action in `vocabulary.MOVED`;
`Apply` lands on `Presenting`, which is what it meant in every volume old enough to hold it.

# What it cost

A rename across every consumer and every test that read a local name (`"Acquire"` is
`"Acquiring"` now), and one more paragraph in the #334 allowlist for the migration
destinations. `means.md` folds into `action.md`; [lever](/domain/lever.md) and
[effect](/domain/effect.md) stay as parts of an action.

# Seams left open

- **A package with two actions of one kind** has no word for the kind they share. The day one
  ships, that is a class the package declares and its two actions are typed with — a
  sub-class of `orexis:Action`, not a return of `orexis:Means` — and nothing in the kernel changes.
