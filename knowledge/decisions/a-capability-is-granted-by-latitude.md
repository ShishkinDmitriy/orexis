---
type: Decision
title: A capability is granted by latitude — room to move and the ability to use it are one fact
description: Self-review left the kernel and became a capability family with members. What grants it is the mandate itself — an agent whose world gives it room to move gets the module that uses the room, derived rather than declared — which required the mandate to stop being a private belief.
status: accepted
stage: v1
tags: [capabilities, review, beliefs, constitution, provenance, upkeep]
timestamp: 2026-08-10T00:00:00Z
---

# Context

[a-belief-is-a-pick-within-a-range](a-belief-is-a-pick-within-a-range.md) gave an agent the right
to re-pick its own settings inside stated bounds, and built the machinery for it: summaries,
evidence, ranges, revisions, a review rule per term, and `validate_agent` as the test of whether a
revision is legitimate. All of it went in the kernel, because at the time there was one way to do
it and no second one in sight.

Two things were wrong with that, and they turned out to be the same thing.

**It had a capability's shape and the kernel's location.** 24 of the kernel ontology's 71 terms
belonged to self-review — enough to break `agent/ontology.py`'s own stated invariant that the
kernel vocabulary is what *every* agent has. Nothing else in the kernel is optional; this was.

**And it is exactly the case rule 2 describes.** Reviewing your own settings by rules the packages
ship and reviewing them by asking a model are two ways of having one ability. The *how* could
differ, which is the test for a capability rather than a function. Left in the kernel, adding the
model implementation would have been a redesign; as a family with members it is a directory.

Which left the question this record exists to answer: **how does an agent come to have it?**

# Decision — the mandate is the grant

An agent that its world gives room to move gets the ability to use the room. One premise, one
rule, in `capabilities/review/rules.ru`:

```sparql
INSERT { GRAPH $derived { ?agent ag:hasCapability ag:Reckoning } }
WHERE  { ?agent a ag:Agent ; ag:commits ?commitment . ?commitment ag:onTerm ?term }
```

Nothing declares it, nothing is listed anywhere, and there is no separate switch that could
disagree with the mandate. An agent with a mandate reviews; an agent with none has no review
module at all, keeps no summaries, and never arises. The two facts cannot drift apart because
there is only one fact.

This follows the shape perception already had — a capability that is a strict function of
something already stated, so it is `derived` and not `deduced`, and it lands in
`graph/world/derived` like every other conclusion. See
[who-put-the-fact-there](who-put-the-fact-there.md).

## Which meant the mandate had to become public

The premise has to be readable by a rule that runs at genesis, and `ag:commits` was a private
belief. Moving it was not a mechanical consequence of the derivation; it corrected the original
placement.

**An agent constraining itself is not a constraint, it is a choice.** A range is what an agent is
*allowed* — that is a governance fact, and it belongs to whoever ratified the world. The pick
inside the range is what the agent wants, and only that is an opinion. So: **range public, value
private.** `ag:commits` moved to `world.ttl`; `ag:sleepS` and the rest stayed in beliefs.

`Range`'s three sources are therefore all public now, and all intersect:

| source | what it is |
|---|---|
| constitution | what the society allows any agent — figures on the capability family |
| hardware | what the equipment can do |
| mandate | what *this* agent's world allows it — `ag:commits` |

Two things fell out of that which were not available before:

- **"A world may narrow the constitution, never widen it" became checkable.** Both ends of the
  comparison are now in graphs a single SHACL shape can see. `ag:MandateWithinTheConstitutionShape`
  finds the constitutional figures through `ag:revisableToward`, so it names no family and no
  term: a package declaring a new revisable belief is covered without editing the shape.
- **A peer could read it.** What an agent may do is now a fact about the society rather than a
  claim in a file only that agent mounts. Nothing uses this yet.

## The interval stopped being a switch

`ag:reviewIntervalS` was optional, and its absence meant "never review". That was a side channel
dressed as a decision by omission: nothing could check it, and it put the question *does this
agent reflect* in a private file where no shape and no peer could read the answer. It is now an
ordinary required parameter of the capability, exactly as `ag:fastSleepS` is for one that
subscribes — `sh:minCount 1`, floor 60 seconds, because an arising re-validates the whole agent
against every shape and is not free.

What decides whether an agent reviews is the grant, and the grant is the mandate.

## A family with two members, one of them empty

`ag:ReviewCapability` is the slot. `ag:Reckoning` — works it out itself, from the rules the
packages ship — is what exists and what the derivation grants. `ag:Consulting` — asks something
else — is declared and reserved, with no member behind it.

An unimplemented member is deliberate, and it is the whole reason for splitting: it fixes the
family's name and the shape of the seam *before* the second implementation exists, so building
the model-backed one is adding `agent/capabilities/review/` a sibling and a `PROVIDES` line
rather than re-deciding what a review is. The vocabulary that a model implementation would need —
summaries, evidence, ranges, revisions — is in the family's `ontology.ttl` and shared by both.

## Belief-base upkeep stayed in the kernel, on a clock of its own

Compaction used to ride the review timer, which was fine while everyone reviewed. Under this
decision an agent with no mandate has no review module, and would have silently stopped compacting
— a regression of the defect that motivated the whole line of work, arriving invisibly, because
nothing fails when a belief base merely grows.

So `BeliefBaseUpkeep` now runs its own hourly timer, started and stopped by the runtime. This is
also the right line and not just the safe one: **compaction is not a choice.** No agent decides
whether to reclaim its own disk, nothing could be done differently, and by rule 2 that makes it a
function rather than a capability. The ratio it fires on (`ag:maxBytesPerTriple`) stayed in the
kernel ontology with it.

`agent/metrics.py` reflects the split. `belief_compactions` comes off the kernel and every agent
reports it; the revision counts come off a module an agent may not have, through a new generic
`Module.reports()` hook — so the kernel does not import a capability's terms to describe it, and
the *absence* of those lines in the series is itself the reading: this agent was never granted any
latitude, rather than having had no second thoughts.

# Consequences

- Adding an agent that may adapt is one triple in `world.ttl`; adding one that may not is writing
  nothing. There is no third state where a mandate and a switch disagree.
- The kernel ontology is back to what every agent has. ~20 terms moved to the family.
- A review rule still belongs to the package owning the term it re-picks — `review.rq` for the
  sensing cadence stays in `capabilities/perception/`. The review capability owns *reviewing*; it
  does not own what may be reviewed.
- The old kernel `ag:CommitmentShape` used `sh:targetClass ag:Commitment` and matched nothing for
  as long as it existed: a mandate is written inline as `ag:commits [ ... ]`, and nobody types a
  blank node they are already describing. The replacements target `sh:targetObjectsOf ag:commits`.
  Worth remembering as a class of bug — a shape that never fires passes.

# Seams left open

- **Nothing chooses between members.** With one implementation the derivation names `ag:Reckoning`
  directly. When `ag:Consulting` exists, something has to select — and unlike perception, no
  hardware fact forces the answer, so it will be a `deduced` judgement at genesis rather than a
  `derived` one. The rule will need a second premise; what that premise is, is not decided.
- **A mandate covers one term, and an agent may hold several.** They are independent ranges with
  no relation between them; nothing expresses "you may loosen this one only if you tighten that
  one".
- **Nothing reads another agent's mandate.** Making it public makes that possible and no more —
  there is no bidding or trust consequence to what latitude a peer was given.
- **A mandate cannot be revised.** It is ratified, in the world, and an agent moves inside it; an
  agent asking for *more* room is a governance act with no mechanism and deliberately no design.
