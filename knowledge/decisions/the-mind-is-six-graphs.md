---
type: Decision
title: >-
  "The mind is six graphs, and a graph is classified on three axes"
description: >-
  The sovereign's reframe of the whole core — an agent's mind is named graphs in one
  vocabulary, and what changes between them is the MODALITY of what they assert: is, may be,
  would like, could do, doing, did. Classified on three orthogonal axes (modality, visibility,
  how it arrived), which immediately shows two joints were misnamed: the region the desire
  graph holds is a CONSTRAINT nobody chose, and the graph called beliefs holds no beliefs at
  all — only picks. Birth authors picks and nothing else; amendment is an event a versioned
  world makes visible; history is a ring with Influx behind it.
status: superseded-in-part
superseded-by: a-store-is-a-modality
timestamp: 2026-08-19T13:31:09Z
---

> **Superseded in part.** The modalities stand — is, may be, would like, could do, doing,
> did — and so does everything this record found by naming them: the region is a constraint,
> the beliefs graph holds picks, norms unify, birth authors picks and nothing else. What
> moved is the CARRIER:
> [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) makes each modality a STORE
> with its own persistence, and inside a store the graphs say only who put the fact there —
> so the three axes below become two levels, and the visibility axis folds into arrival
> (there was never a shared store, and "public" always meant genesis-authored). Read the
> table of six as the map of the mind; read "graph" in it as "store" going forward.

# The mind is six graphs, and a graph is classified on three axes

Proposed by the sovereign across a long design sitting, and it names the organising principle
the architecture had been circling: **the graph is the modality.** Same subject, same
property, same units everywhere — what differs between graphs is what they ASSERT about them.

| graph | asserts | example |
|---|---|---|
| belief | what IS | fern's moisture is 0.31 |
| constraint | what MAY be | fern's moisture must stay within 0.45–0.65 |
| desire | what I PURSUE | fern aims at 0.55 |
| menu | what I COULD do | I can raise moisture by bidding at this venue |
| intention | what I am DOING | committed to acquire, since 12:04 |
| history | what I DID | dosed 0.3 L at 12:06; the claim discharged |

One vocabulary across all six is what makes the difference legible: a plan step becomes
literally a triple moving from the desire graph's shape into the belief graph's, which is the
graph-diff planning [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)
could previously only gesture at.

## Three axes, not one

A graph carries three independent classifications, and conflating them is why some graphs
never found a natural home:

- **modality** — what its content asserts (the six above);
- **visibility** — whose it is: public knowledge every agent may read, or one agent's own;
- **how it arrived** — **asserted** (the sovereign said so), **derived** (a package's rule
  concluded it from givens), **entailed** (the vocabulary's own logic implies it), **recorded**
  (this agent's act, at runtime), **received** (another party's word — a device's reading, a
  peer's claim).

*Received* is the axis value obligations introduced, and the one whose trustworthiness is a
question: an assertion is the sovereign's by definition and a derivation is checkable
arithmetic, but a received fact is someone else's word and either carries their signature or
does not. So the graph classification and the trust story turn out to be one story.

## What the frame immediately found

**The region is a constraint, not a desire** — and the naming followed, in three steps the
sovereign drove: the graph is `graph/constraint`, typed `orexis:ConstraintGraph` **and**
`orexis:PublicGraph` (the two axes, needed independently — typing it on modality alone made it
invisible to every reader for exactly as long as it took a test to say so); the class inside
it is `orexis:Bounds`, not `orexis:Desire`; and the predicate is `orexis:boundedBy`, because an agent does
not desire 0.45–0.65, it is HELD to it — what it desires is the aim, 0.55.

*Both of those terms are gone, within a day, and the distinction they were drawn to make
survives them:* a region and an aim became SHACL differing in severity, so the predicate is
`orexis:holds` for either and the class is `sh:NodeShape`. See
[a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md). The reasoning above is why the
constraint graph is not called the desire graph, and that outlived the vocabulary.

The decisive evidence is in the running code rather than in the argument: **an agent holding
bounds and no aim pursues nothing.** If bounds were an end they would motivate alone. They do
not.

The claim outlived the clause that used to carry it, and is worth restating in the terms that
carry it now. It used to be one line — `aim()` returns None, so the reflex proposes None, over
a comment reading "an agent that picked no point has decided not to steer this property". The
reflex is gone and the enforcement is distributed, which is if anything the stronger position:
a bidder holding no aim in the property its bids are priced in is refused by a shape at boot;
an actuator with no aim sizes every dose at nothing, so the effect predicts the world it is
already in and the step is discarded; and a property with no lever at all is proposed nothing
about because there is nothing to propose. Three roads, no motivation on any of them.

What the two pairs of numbers differ in is SEVERITY, not modality: leaving the operating
region is legitimate and temporary (it is what a gap IS), leaving the survival envelope is the
subject ending. That is `sh:Warning` against `sh:Violation` — the axis
[a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) already
records — so they stay one node with two pairs, and urgency needs both at once.

The obligation in all this is not the range at all: it is **`orexis:actsFor`**, the office the
sovereign appointed. That is why no range carries an `owedTo` — you are not obliged to a
plant, which can present no claim; you are obliged by the appointment, and the plant is the
beneficiary. The range only says what discharging the office looks like, numerically.

**The original finding, for the record:** It is the plant's operating range intersected
with the instrument's, deduced by a rule; the agent cannot move it and is refused at boot for
violating it. Something you cannot move and are refused for violating is a constraint. It was
called desire because the name followed the *capability that computes it* — which is also why
`desire:Deducing`'s own comment says it has "no judgement and no latitude", the signature of
something that was never a want.

**The graph called `beliefs` holds no beliefs.** Sort its contents: the aim is a desire about
the world; the cadence, patience, ceiling and delta fraction are desires about the agent's own
conduct — every one a pick inside a mandate, revised by review on evidence. Everything the
agent actually believes is in `sensed` and the public graphs. That name followed the
*container's role* — "the agent's private store" — rather than its content.

Both misnamings came from different wrong axes, which is the argument for naming all three.

**Norms unify.** Operating and survival ranges (sourced by a species), device limits (by a
manufacturer), allocation ceilings (by the constitution), review latitude (by the sovereign)
and claims (by a peer) are one kind of thing: someone else says what this agent may do. One
class, `Constraint`, with `Obligation` the subclass that names a counterparty — because a
rotting rhizome is not an obligation owed to a plant, and the difference between a hard bound and a
debt is exactly whether there is someone to be wronged.

## Birth authors picks, and nothing else

Sorted by where content comes from, only one graph is born: beliefs are empty (an agent is
born blind, which is why its first intention is always Observe), constraints pre-exist it,
the menu is implied, intentions and history start empty — and the **desires** are what genesis
authors. So birth is one act: *the sovereign endows this agent with its opening picks inside
constraints that already existed*. Endowment (#202) is not a special case but the same act
happening again when new room appears.

## A world that is replaced makes history uninterpretable

If each start replaces the world graph, an amendment is invisible — the agent cannot tell
being born into a world from waking into a changed one — and an act recorded last week was
committed under a constitution that no longer exists anywhere, so "why did it do that" is
unanswerable however carefully reasons were recorded. `orexis:currentVersion` and
`orexis:WorldVersion` are already declared and observed by nothing, which is the tell.

**Worlds append rather than replace.** Each ratification is its own immutable graph; the
current version says which is in force; and boot compares the version held with the version
current. When they differ, that is an EVENT: recorded in history, picks re-validated against
the new bounds, new room endowed, standing commitments whose affordance vanished dropped with
"the world moved" as their reason, and debts to departed agents marked **uncollectable**
rather than deleted — a debt does not vanish because the creditor left. An agent down across
two amendments records one waking, not a replay:
amendment is a fact about the world's history, not a migration script.

This is what [genesis](/decisions/genesis.md) already claims — *"amendable and versioned;
structure mutable, history immutable"* — made true, since immutable history against a mutable
constitution is only half a memory.

## History is a ring, with the series store behind it

Recent executed intentions, doses and observations in the graph; everything streamed to Influx
for the deep questions, which is [two-store-beliefs](/decisions/two-store-beliefs.md)
unchanged. The objection — that bounding history breaks citation — is already answered by the
codebase: an expectation **copies** the baseline into its own row (#165), so nothing points
into history and whatever must outlive the window takes what it needs at commit time. No
reference counting, no pinning, no unbounded graph.

## The mind's STATES are the kernel's; the ways of reaching them are the packages'

Asked by the sovereign once the axes existed: if this is the core of Orexis, should it be in
the `orexis:` namespace? The first answer drawn here was "the frame yes, the contents no" — and
the sovereign's follow-up corrected it, rightly. Two arguments settle it the other way:

**The states are already a lingua franca.** Four packages had to name them —
market's bidding and hosting, deliberation, actuation — and a term many packages must name is
not a package-private word. That is exactly what `orexis:actsFor` and `orexis:localId` are, and the
kernel is where such words live.

**And the objection against it does not survive.** "Not every agent is a BDI agent" —
`world/sensing`'s agent wants nothing — argues against making the CAPABILITY mandatory, never
against the TERM being kernel: a class most agents hold no instance of is still a class. The
existence of a class was never a claim about the universality of its instances. (The example
this used was `orexis:Device`, which has since left for a reason of its own —
[the-substrate-is-not-the-minds](/decisions/the-substrate-is-not-the-minds.md) — and the
argument never depended on which class it was.)

So the line falls one notch over: **what a mind CONTAINS is the kernel's — desires, aims,
obligations, intentions and the means they name — and HOW a mind reaches them is the
packages'.** `desire:Deducing` and `desire:Consulting` are two ways of arriving at a region;
`intention:Keeping` is one way of keeping a ledger; each family keeps its own figures (a
patience, what this society tolerates before it stops trusting a claim). Rule
2 is untouched, because it asks only whether the HOW could differ — and
[telemetry-is-a-mandatory-capability](/decisions/telemetry-is-a-mandatory-capability.md)
already settled the mirror case: universality never promoted a term, and here non-universality
never demoted one.

It also ends a split brain the axes had just created: `orexis:IntentionGraph` holding
`intention:Intention` instances, the container kernel and the content not.

The general test, stated once: **not whether a term is universal, but whether the HOW could
differ** — and, for a noun rather than a verb, whether many packages must speak it.
[telemetry-is-a-mandatory-capability](/decisions/telemetry-is-a-mandatory-capability.md)
settled that case: reporting is granted to every agent and is still a package, because there
is more than one way to report.

The kernel therefore declares both what a graph IS — modality, visibility, arrival, which it
resolves against itself — and what a mind contains. This does not reverse
[every-term-in-its-own-house](/decisions/every-term-in-its-own-house.md): that record's
criterion is *whose term is it*, and it moved five packages' private words out of `orexis:` by
applying it. Applying the same criterion here gives the opposite answer, because these words
turned out to be everyone's.

The lifecycle joins them when it exists: birth, amendment and death are performed by the
kernel whatever an agent composes.

**What the move cost**: a term rename across every file kind, plus one belief-term migration —
`desire:aims` is in every deployed volume — carried by the by-local-name mapping
[a-volume-can-be-older-than-the-vocabulary](/decisions/a-volume-can-be-older-than-the-vocabulary.md)
built for exactly this, verified end to end. And it re-met that record's own warning: three
IRIs were built by CONCATENATION (`_INTENTION_NS + "Observe"`), invisible to any textual
rename, so writes moved while reads stayed — caught by tests, not by a scan.

## The order of work, and why

1. **Name the modalities** — vocabulary only, typing the graphs that exist. No data moves.
2. **Goals get identity and source** — DONE. Bounds are minted as a function of the agent's
   id and the property's local name (`orexis:bounds.fern.SoilMoisture`, the channel precedent) and
   carry `prov:wasDerivedFrom` the subject whose ranges produced them; an obligation carries
   the claim that raised it. A blank node is a thing nothing can reference, and an intention
   must be able to say which end it serves.
3. **`orexis:pursues`** — DONE, before it could go live. Intentions keyed on `(means, property)`
   alone, so two obligations about one property were indistinguishable: satisfying one
   satisfied both and the patience absorbed the second impulse as the first — the shape of the
   observation-keyed-by-subject bug, caught while obligations still do not drive acts. The
   goal is optional, and a row without one is keyed exactly as before, so a ledger written
   before goals had names stays readable and is never orphaned by a question it could not
   have answered.
4. **History as a ring** — gives amendment somewhere to be recorded, and gives `within_patience`
   a home matching its meaning: a question about the past.
5. **Versioned worlds, birth and amendment as events.**
6. **Move the data to match the labels** — optional, and treated so: if the types carry the
   truth, an ugly IRI with an honest type may be worth keeping until another migration makes
   the rename free.
7. **Character as source-ordering** — the sovereign bounds how far obligation outranks desire,
   the agent picks inside, review moves the pick. Default social, or the shipped worlds change
   behaviour.
8. **What an agent pursues becomes SHACL** — constraint, desire and obligation as shapes
   differing in severity and in whose graph they sit; `orexis:Bounds`, `orexis:boundedBy` and `sensing:Aim`
   retire. Before the next step, because a goal that is a pattern is what makes the next step
   expressible at all. This step was first designed as *desired states in belief's shape* and
   the sovereign turned it over within a day — see
   [a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md), which supersedes that design and
   keeps its diagnosis.
9. **Obligations drive acts** — DONE. Deliberation takes goals rather than a property and a
   value: `propose_for(goal)` answers for a stake and an obligation alike, and a host serves a
   presented claim because its deliberator proposed the move, not because a handler fired. What
   it needed first was a DEADLINE — a claim had none, so an obligation had no honest source of
   urgency — and the sovereign chose to add the fact rather than proxy it. A obligation nothing can
   serve now stays owed, stays hot, and is tried again when the vessel reports.

# Seams left open

- **Whether the menu belongs in the mind at all.** It is the one graph with no independent
  existence — a join of beliefs, constraints and wiring. Kept because a model and a sovereign
  must be able to read it, and materialising a conclusion is legitimate where authoring one is
  not; the day nothing reads it, it is the first to go.
- **What bounds the history ring.** Fixed size is the starting answer; whether the window
  should be time-shaped, act-shaped, or amendment-shaped is a measurement nobody has taken.
- **Where a received fact's trust is recorded.** Signature checking happens at the edge today
  and leaves no trace in the graph, so "this fact arrived signed" is currently a log line
  rather than a triple. The received axis value is the natural place to fix that, and it is
  not fixed here.
