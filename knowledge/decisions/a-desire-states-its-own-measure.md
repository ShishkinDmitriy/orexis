---
type: Decision
title: A desire states its own measure, and the measure is the aim's
description: >-
  Found by reading two deliberation mechanisms side by side — the reflex steered toward the
  AIM while the planner scored worlds from the region's geometric CENTRE, so they pursued
  different targets whenever the pick sat off-centre, and the shipped loner world sat exactly
  there. Closed by reifying the desire into a node that carries its met-shape (unchanged in
  content) and a label, with a declared urgency measure as SPARQL evaluated against whichever
  world is being judged. On the sovereign's rulings — two of them — nothing of the measure
  belongs to the core: the kernel ASKS through the choir (Module.desire_urgency) and holds no
  measure vocabulary, graph or evaluator, while sensing declares, reads and runs the
  observation-backed measure per KIND from its own file in its own namespace. The measure
  reads the aim at query time; the planner no longer short-circuits a met desire; steering
  toward the pick comes out of satisficing with a natural deadband. The prerequisite for
  retiring the reflex, which this change deliberately did not touch and which phase B has
  since deleted.
status: accepted
timestamp: 2026-08-24T12:00:00Z
---

# A desire states its own measure, and the measure is the aim's

## The finding: two mechanisms, two targets

The deliberator held two ways of deciding, and they disagreed about what was being pursued.
The reflex (`propose`/`_by_gap`) steers a property toward the agent's AIM — the pick, read
through the sensing provider's `aim`, which deliberately refuses to default to the region's centre, because a
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

A desire had no node — it WAS a `sh:NodeShape` the agent `orexis:holds`
([a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md), now superseded in this one part).
A shape can say when a want is met and nothing else; conformance is boolean while a want has
distance. So the desire is reified: `orexis:Desire` in the kernel's vocabulary, minted by the same
derivation (`agent/desires.ru`), carrying the met-test and a name — and pointing, through its
KIND, at a measure the kernel never authors.

- **`orexis:metWhen`** — the SHACL node shape that is the met-test. Its CONTENT is unchanged from
  when the desire was it; what changed is that it hangs off the desire node rather than being
  it. It governs the outcome LABEL and an obligation's discharge, never how hard to try.
- **`rdfs:label` and `rdfs:comment`** — authored by the derivation ("SoilMoisture inside
  0.45-0.65, aiming 0.55"), for dashboards and the sovereign's ask channel, refreshed on every
  rebuild, which every recorded re-pick triggers.
- **The measure** — a node carrying `sh:select`, SHACL-AF's word for a SPARQL SELECT held as
  a literal, the same mechanic a means' effect rule uses for `sh:construct`. Our own Python
  runs it — the capability's own, after the split below — and pySHACL is never asked to. The
  contract: one binding, `?urgency`, in 0..1, parameterised by substitution like an effect
  rule (`$me`, `$subject`, `$property`, `$sensed`, `$picks`, `$value`, and the region's
  numbers) and evaluated AGAINST A WORLD — the belief base for the live number, or a
  candidate possible world inside the planner. One measure, asked of whichever world is being
  judged.

## The sovereign's split, in two rulings: nothing of the measure belongs to the core

The placement was refused twice, each refusal narrower than what it refused, and both landed —
the intermediate state is merged history, not a draft this record may pretend away.

**The first cut** compiled the measure's SPARQL inside `agent/desires.ru`, per desire, bounds
baked. Refused before merging: **the core is BDI** — that an agent wants, what it wants, when
a want is met — and *how badness is measured* is planning-domain machinery, a capability's
contribution, not the mind's structure.

**The second cut** — the state PR #332 merged with — moved the CONTENT to sensing's
`measures.ttl` and kept the MACHINERY in the kernel: a kernel evaluator module (a
`measure.py` under the kernel tree, since deleted), a measures graph loaded by genesis, and
`ag:MeasureGraph` / `ag:measureOf` / `ag:measuredBy` in
the kernel vocabulary, on the effects precedent. The sovereign refused that too — *"measures
is still in core; at least don't add new into core, which is not belong to core"* — because
every one of those was new core surface that is not BDI structure, whatever its contents.

**The extraction that completes it** dissolves the machinery into the choir, the path the
house already had (`urgency` was always a hook modules contribute; the keeper already answers
it for open expectations):

- **The kernel keeps** `orexis:Desire`, `orexis:metWhen`, the label, and the derivation minting them
  (the-mind-is-not-a-package is not re-litigated: the want, its shape and its node stay
  kernel-derived) — and ASKS: `Module.desire_urgency(desire, query, sensed, value=None)`, a
  hook signature, collected max-of-answers like every choir question, with the kernel
  iterating its modules and naming no family. No measure vocabulary, no measure graph, no
  evaluator: the kernel evaluator module, `loader.measure_files()`, `MEASURES_GRAPH` and the
  three `orexis:` terms are deleted.
- **Sensing owns its whole answer**: `measures.ttl` in its own directory, `sensing:measureOf`
  in its own namespace, parsed and evaluated by its own module, which answers the hook for
  observation-backed wants — a reading against the aim, and the reading is sensing's whole
  subject. The content reaches the kernel through the hook's RETURN VALUE and nothing else:
  no kernel loader learns the file exists, no `agent/` import crosses into `packages/`.
- **Still declared per KIND, still nothing compiled**: `sensing:measureOf
  sosa:ObservableProperty` says "a want about an observable property is measured by this
  SELECT"; the module resolves a desire by asking the store what its `ssn:forProperty` object
  IS; the aim is read out of `$picks` by the query itself, and the region's numbers arrive
  as substituted parameters read off the deduced shapes at answer time — the `$litres`
  discipline, so a re-pick or a re-derivation moves the answer with no text rebuilt.
- **The fallback is defined, not implied, and unchanged in behaviour**: a want no module
  answers for scores 1.0, logged — not knowing how bad is maximal, consistent with
  `urgency(None)`. The planner-side rule was *a search that cannot rank must not conclude*, so
  a measure-less non-obligation deferred to the reflex; phase B replaced the deferral with a refusal
  at genesis, since a stake nothing measures is a fact about a world's files rather than about
  a moment. Tests pin the fallback and that no shipped world hits it, every shipped desiring
  agent holding sensing and every shipped stake being a `sosa:ObservableProperty`.
  `Region.urgency` survives as the test-only reference the declared query is held to at the
  no-pick fallback; nothing on the live path calls it.

Distance is scaled by the survival room on the side the value sits — the asymmetry
`Region.urgency` always had, kept and re-anchored: room below the aim is aim-to-floor, above
it aim-to-ceiling, so being 0.05 out costs what the room in that direction says it costs. An
unmeasured property COALESCEs to 1.0 explicitly, because this engine binds NOTHING for
arithmetic over an unbound value, and an unmeasured want must never read as no urgency.

## The planner half: met is the label, urgency is the motive

The root-level short-circuit is gone: a met desire whose measure is not zero still searches.
Shape-met governs the outcome LABEL (a met desire that weighed its levers and found none worth
pulling reports SATISFIED, never NOT_BETTER) and obligation discharge; urgency governs whether a
step is worth taking. Steering toward the pick then comes out of satisficing with a natural
deadband nobody chose as a tolerance: near the pick the dose sizes to ~0 (`dose_for` computes
from aim − value), the actor's `litres <= EPS` refusal makes the effect predict no change, and
the candidate is pruned as the world already stood in. Off the pick and inside the region, a
dose is proposed — sized, simulated and checked to improve — where the old path handed the
same case to the unsatisficed reflex. The deliberator's deferral for SATISFIED-without-steps
is gone with it; a met desire the search answered is a decision, not a hand-off. The last
deferral, for a search blind to part of the menu (`partial`), went in phase B — there is
nothing left to defer TO, and the condition is refused before a society starts.

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
- **A obligation's measure could not be declared, and the reason was already pinned.** The design
  wanted the fraction-of-redeem-window as a declared measure too, and the engine binds nothing
  for `duration / duration` — measured long before this change, with a test whose message
  already names the trigger: *"if this now binds, delete `_duty_urgency` and let desires.rq do
  the arithmetic"*. Obligation urgency therefore stays Python's, one clock, exactly as
  [an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md)
  left it. Baking epochs was considered and refused: the derivation is SPARQL and cannot
  convert a dateTime to a number either, so every path to a declared obligation measure runs through
  the same missing operation. Its future home is settled by the split above even so: the
  MARKET package's `measures.ttl`, by this same mechanic, the day the engine divides durations
  — so the kernel's measure story stays uniform, never knowing any measure's content, only how
  to evaluate one.
- **A freshness want states no measure.** ~~It has no distance to scale — a boolean and an age,
  both judged where the clock is — so its urgency stays the kernel's (1.0 unmeasured or stale,
   0.0 otherwise).~~ **It states one now**, in sensing's own `measures.ttl`, by the same
  mechanic and for the reason this bullet did not see: the numbers were the same either way,
  but a measure the kernel computes is one the PLANNER cannot ask of a world nobody is in yet,
  so every candidate scored the flat 1.0 and no look could be preferred to standing still. It
  is reified like the region (node, met-shape, label), so one mechanism reads both. Which kind
  of want it is is read off the INSTRUMENT it names rather than off a flag, and the values are
  still boolean — the gradient waits on the price of looking, which nothing charges yet.

# Seams left open

- **The measure words are one package's until a second speaks them.** `sensing:measureOf`
  is sensing's namespace deliberately: the repo's promotion test for an `orexis:` word is a word
  SEVERAL packages must speak, and today one does. The trigger is the second measure-shipping
  package — the market's obligation measure, when the engine allows it — and promotion happens
  then, not before.
- **Phase B: retire the reflex.** ~~Decided and deliberately deferred~~ — **DONE**, once this
  change had been reviewed and the search had been the control's equal at every value anyone
  compared them at. `propose`, `_by_gap`, `_direction_of`, `_my_shop_needs` and the rung ladder
  are deleted; `orexis-validate` refuses both conditions that used to need the fallback — an
  affordance-contributing means with no effect rule, and a stake that resolves no declared
  measure, the second being this record's own fallback turned into a gate. The argument and
  what the deletion cost are in
  [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md), which set
  the deletion as its own acceptance test; a seam that has been closed is left here struck
  through rather than removed, because the two phases only make sense read together.
- **Epistemic wants through the search.** ~~A freshness goal has a met-shape and no measure, so
  the planner still scores it by the not-knowing constant rather than by anything a candidate
  world could improve — Observe reaches it through the state machinery, not through
  satisficing.~~ **DONE.** The want moved into sensing, declared its measure there, and the
  state machinery it used to reach Observe through is deleted. The clock question this seam
  said had to be answered first was not the obstacle: the measure runs against whichever world
  is being judged, on the same store the horizon is published into, so the store's NOW and the
  reader's are one clock by construction. What actually blocked it was cycle detection pruning
  the one lever that repairs a freshness goal. See
  [a-lever-an-agent-cannot-pull-is-not-a-lever](/decisions/a-lever-an-agent-cannot-pull-is-not-a-lever.md).
- **The region shape's Below/Above split retiring `market:direction`.** The parent record
  already argues it: Raises repairs the Below violation, Lowers repairs Above, and the one-bit
  effect hardcoded into the reflex becomes a match between two shapes. Phase B has happened and
  the term still stands — deliberation no longer reads it, but the keeper's verification arc
  copies it into every expectation to know which way a dose should show up, so retiring it is
  repair-matching's change to make rather than the reflex's to have taken.
