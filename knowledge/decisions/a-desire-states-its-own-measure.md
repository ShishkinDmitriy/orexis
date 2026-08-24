---
type: Decision
title: A desire states its own measure, and the measure is the aim's
description: >-
  Found by reading two deliberation mechanisms side by side — the reflex steered toward the
  AIM while the planner scored worlds from the region's geometric CENTRE, so they pursued
  different targets whenever the pick sat off-centre, and the shipped loner world sat exactly
  there. Closed by reifying the desire into a node that carries its met-shape (unchanged in
  content), a declared urgency measure as SPARQL run by our own Python against whichever world
  is being judged, and a label. The measure reads the aim at query time; the planner no longer
  short-circuits a met desire; steering toward the pick comes out of satisficing with a
  natural deadband. The prerequisite for retiring the reflex, which this change deliberately
  does not touch.
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
derivation (`agent/desires.ru`), carrying three things.

- **`ag:metWhen`** — the SHACL node shape that is the met-test. Its CONTENT is unchanged from
  when the desire was it; what changed is that it hangs off the desire node rather than being
  it. It governs the outcome LABEL and a duty's discharge, never how hard to try.
- **`ag:measuredBy`** — a node carrying `sh:select`, SHACL-AF's word for a SPARQL SELECT held
  as a literal in the graph, the same mechanic a means' effect rule uses for `sh:construct`.
  Our own Python runs it (`agent/measure.py`), the way `agent/effects.py` runs a construct;
  pySHACL is never asked to. The contract: one binding, `?urgency`, in 0..1, parameterised by
  substitution like an effect rule (`$subject`, `$property`, `$sensed`, `$beliefs`, `$value`)
  and evaluated AGAINST A WORLD — the belief base for the live number, or a candidate possible
  world inside the planner. One measure, asked of whichever world is being judged.
- **`rdfs:label` and `rdfs:comment`** — authored by the derivation ("SoilMoisture inside
  0.45-0.65, aiming 0.55"), for dashboards and the sovereign's ask channel, refreshed on every
  rebuild, which every recorded re-pick triggers.

The region desire's measure is compiled with the deduction's own numbers baked — the bounds
are its conclusions, and a rebuild that moves them recompiles the text — and the AIM
deliberately not baked: the query reads `ag:aims` out of `$beliefs` at query time, so a review
that moves the pick moves the urgency with no rebuild, falling back to the region's centre
exactly while no aim is picked. Distance is scaled by the survival room on the side the value
sits — the asymmetry `Region.urgency` always had, kept and re-anchored: room below the aim is
aim-to-floor, above it aim-to-ceiling, so being 0.05 out costs what the room in that direction
says it costs. An unmeasured property COALESCEs to 1.0 explicitly, because this engine binds
NOTHING for arithmetic over an unbound value, and an unmeasured want must never read as no
urgency. `Region.urgency` in Python survives as the reference arithmetic and the fallback for
a want stating no measure; nothing on the live path computes urgency twice.

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
  the same missing operation.
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
