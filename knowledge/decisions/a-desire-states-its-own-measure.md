---
type: Decision
title: A desire states its own measure, and the measure is the aim's
description: >-
  Found by reading two deliberation mechanisms side by side — the reflex steered toward the
  AIM while the planner scored worlds from the region's geometric CENTRE, so they pursued
  different targets whenever the pick sat off-centre, and the shipped loner world sat exactly
  there. Closed by reifying the desire into a node that carries its met-shape (unchanged in
  content) and a label, with a declared urgency measure as SPARQL run by the kernel's
  evaluator against whichever world is being judged. On the sovereign's ruling the measure's
  CONTENT is a capability's, not the kernel's — the core is BDI, so the mind carries the slot
  and sensing declares the observation-backed measure per KIND, the effects mechanic applied
  to desire. The measure reads the aim at query time; the planner no longer short-circuits a
  met desire; steering toward the pick comes out of satisficing with a natural deadband. The
  prerequisite for retiring the reflex, which this change deliberately does not touch.
status: accepted
timestamp: 2026-08-24T12:00:00Z
---

# A desire states its own measure, and the measure is the aim's

## The finding: two mechanisms, two targets

The deliberator held two ways of deciding, and they disagreed about what was being pursued.
The reflex (`propose`/`_by_gap`) steers a property toward the agent's AIM — the pick, read
through `deducer.aim`, which deliberately refuses to default to the region's centre, because a
fabricated preference is still a fabricated belief. The planner scored candidate worlds by
`Region.urgency`, which measured distance from the region's geometric CENTRE. So whenever the
pick sat off-centre the two mechanisms pursued different targets — and once a desire was
inside its region the planner short-circuited SATISFIED without searching, the deliberator
deferred to the reflex over a comment claiming *"already met; the reflex will also propose
nothing"*, and the reflex proposed plenty: it steers to the aim, unsatisficed. The comment was
wrong in exactly the case that mattered.

Two details say this was latent design debt rather than a fresh bug. `Region.urgency`'s own
`centre` docstring read *"where an agent with no other reason to prefer would aim"* — the
centre was always a stand-in for the pick, written down as such. And the shipped `world/loner`
lives on the wrong side of the split: its gardener aims at 0.18 in a 0.10–0.30 region,
dry-side of centre, deliberately (the very example `domain/aim.md` teaches with) — so its
reflex and its planner were already pursuing 0.18 and 0.20 respectively, on the bench, in a
ratified world.

The parent record had named the requirement before anything needed it:
[a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) — *"a
goal-shape must state its measure or the planner ranks repairs blind"*. This change closes
that gap: the measure becomes the desire's own, declared in the graph, and measured from the
aim.

## The design: a node with room on it

A desire had no node — it WAS a `sh:NodeShape` the agent `ag:holds`
([a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md), now superseded in this one part).
A shape can say when a want is met and nothing else; conformance is boolean while a want has
distance. So the desire is reified: `ag:Desire` in the kernel's vocabulary, minted by the same
derivation (`agent/desires.ru`), carrying the met-test and a name — and pointing, through its
KIND, at a measure the kernel never authors.

- **`ag:metWhen`** — the SHACL node shape that is the met-test. Its CONTENT is unchanged from
  when the desire was it; what changed is that it hangs off the desire node rather than being
  it. It governs the outcome LABEL and a duty's discharge, never how hard to try.
- **`rdfs:label` and `rdfs:comment`** — authored by the derivation ("SoilMoisture inside
  0.45-0.65, aiming 0.55"), for dashboards and the sovereign's ask channel, refreshed on every
  rebuild, which every recorded re-pick triggers.
- **The measure** — a node carrying `sh:select`, SHACL-AF's word for a SPARQL SELECT held as
  a literal in the graph, the same mechanic a means' effect rule uses for `sh:construct`.
  Our own Python runs it (`agent/measure.py`), the way `agent/effects.py` runs a construct;
  pySHACL is never asked to. The contract: one binding, `?urgency`, in 0..1, parameterised by
  substitution like an effect rule (`$me`, `$subject`, `$property`, `$sensed`, `$beliefs`,
  `$value`, and the region's numbers) and evaluated AGAINST A WORLD — the belief base for the
  live number, or a candidate possible world inside the planner. One measure, asked of
  whichever world is being judged.

## The sovereign's split: the kernel carries the slot, a capability the content

The first cut compiled the measure's SPARQL inside `agent/desires.ru`, per desire, bounds
baked. The sovereign rejected the placement, not the mechanism: **the core is BDI** — that an
agent wants, what it wants, when a want is met — and *how badness is measured* is
planning-domain machinery, a capability's contribution, not the mind's structure. The precedent
was already in the house: `agent/effects.py` (kernel) runs what `packages/capability/*/
effects.ttl` (capability) declares, and the kernel never knows any effect's content. Applied
again:

- **The kernel keeps** `ag:Desire`, `ag:metWhen`, the derivation (the-mind-is-not-a-package is
  not re-litigated: the want, its shape and its node stay kernel-derived), `ag:measuredBy` as
  the instance-level override slot several packages may one day speak, and `agent/measure.py`
  — the evaluator that runs whatever is declared.
- **Sensing declares the content**, in `packages/capability/sensing/measures.ttl`, loaded at
  genesis into a measures graph exactly as `effects.ttl` is loaded — an observation-backed
  want is measured by a reading against the aim, and the reading is sensing's whole subject.
  The choir's `urgency` hook always listed what modules contribute; this is that instinct as
  a declaration the store can show a sovereign.
- **Declared per KIND, not compiled per desire**: `ag:measureOf sosa:ObservableProperty` says
  "a want about an observable property is measured by this SELECT", and the evaluator resolves
  a desire to it by asking what its `ssn:forProperty` object IS. Nothing is compiled at
  derivation any more: the aim is read out of `$beliefs` by the query itself, and the region's
  numbers arrive as substituted parameters the caller reads off the deduced shapes at query
  time — the `$litres` discipline, so a re-pick or a re-derivation moves the answer with no
  text rebuilt. Where an instance states `ag:measuredBy`, the instance wins — which is the
  seam the planned instance-over-type overrides land in.
- **The fallback is defined, not implied**: a want whose kind no loaded package measures
  scores 1.0, logged — not knowing how bad is maximal, consistent with `urgency(None)` — and
  a test pins both the fallback and that no shipped world hits it, every shipped stake being
  a `sosa:ObservableProperty`. `Region.urgency` survives as the test-only reference the
  declared query is held to at the no-pick fallback; nothing on the live path calls it.

Distance is scaled by the survival room on the side the value sits — the asymmetry
`Region.urgency` always had, kept and re-anchored: room below the aim is aim-to-floor, above
it aim-to-ceiling, so being 0.05 out costs what the room in that direction says it costs. An
unmeasured property COALESCEs to 1.0 explicitly, because this engine binds NOTHING for
arithmetic over an unbound value, and an unmeasured want must never read as no urgency.

## The planner half: met is the label, urgency is the motive

The root-level short-circuit is gone: a met desire whose measure is not zero still searches.
Shape-met governs the outcome LABEL (a met desire that weighed its levers and found none worth
pulling reports SATISFIED, never NOT_BETTER) and duty discharge; urgency governs whether a
step is worth taking. Steering toward the pick then comes out of satisficing with a natural
deadband nobody chose as a tolerance: near the pick the dose sizes to ~0 (`dose_for` computes
from aim − value), the actor's `litres <= EPS` refusal makes the effect predict no change, and
the candidate is pruned as the world already stood in. Off the pick and inside the region, a
dose is proposed — sized, simulated and checked to improve — where the old path handed the
same case to the unsatisficed reflex. The deliberator's deferral for SATISFIED-without-steps
is gone with it; a met desire the search answered is a decision, not a hand-off, unless the
search was blind to part of the menu (`partial`), which still defers.

Consumers kept their call sites: `desires_of`, the gap, the choir's `urgency` hook (sensing's
cadence, with predicted values arriving as `$value`), and the planner all evaluate the one
declared text. The outcome vocabulary and the `agent_deliberation` series fields are
unchanged — measurement names never split series.

## What building it found

- **A zero dividend binds NOTHING.** pyoxigraph 0.5.9 divides decimals — `0.1 / 0.3` binds —
  and returns unbound for the same expression with an exact-zero dividend. No error, no
  missing row: an agent sitting exactly at its aim read as maximally urgent through the
  measure's own error-COALESCE, on the first bench run. The compiled query answers the
  zero-distance case with an `IF` before any division, and the operation is pinned in
  `tests/test_desires.py` beside the duration limit it rhymes with, so the day the engine is
  fixed the guard says so.
- **A duty's measure could not be declared, and the reason was already pinned.** The design
  wanted the fraction-of-redeem-window as a declared measure too, and the engine binds nothing
  for `duration / duration` — measured long before this change, with a test whose message
  already names the trigger: *"if this now binds, delete `_duty_urgency` and let desires.rq do
  the arithmetic"*. Duty urgency therefore stays Python's, one clock, exactly as
  [an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md)
  left it. Baking epochs was considered and refused: the derivation is SPARQL and cannot
  convert a dateTime to a number either, so every road to a declared duty measure runs through
  the same missing operation. Its future home is settled by the split above even so: the
  MARKET package's `measures.ttl`, by this same mechanic, the day the engine divides durations
  — so the kernel's measure story stays uniform, never knowing any measure's content, only how
  to evaluate one.
- **A freshness want states no measure.** It has no distance to scale — a boolean and an age,
  both judged where the clock is — so its urgency stays the kernel's (1.0 unmeasured or stale,
   0.0 otherwise). It is reified like the region (node, met-shape, label), so one mechanism
  reads both; the measure it does not carry is part of the epistemic seam below.

# Seams left open

- **Phase B: retire the reflex.** Decided and deliberately deferred: delete `propose`,
  `_by_gap`, `_direction_of` and the rung ladder once the search demonstrably subsumes them,
  and refuse at genesis an affordance-contributing means with no effect rule — a lever the
  planner cannot simulate is a lever whose package never said what it does, and `partial`
  exists only because such levers are still legal. The reflex stays in this change as the
  control the sovereign compares the search against.
- **Epistemic wants through the search.** A freshness goal has a met-shape and no measure, so
  the planner still scores it by the not-knowing constant rather than by anything a candidate
  world could improve — Observe reaches it through the state machinery, not through
  satisficing. Routing it through the measure needs the staleness clock question answered
  (the store's NOW against the reader's), and is not needed by anything shipped.
- **The region shape's Below/Above split retiring `market:direction`.** The parent record
  already argues it: Raises repairs the Below violation, Lowers repairs Above, and the one-bit
  effect hardcoded into the reflex becomes a match between two shapes. It waits on phase B,
  because the reflex is `market:direction`'s last consumer.
