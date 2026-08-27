---
type: Decision
title: A lever an agent cannot pull is not a lever, and knowing is a want like any other
description: >-
  The freshness want moved out of the kernel into sensing, whose fact its premise is, and
  became a goal the search reaches instead of a state a hardcode recognised — which took three
  things with it. The Observe row is conditioned on the sense mode, so a listening agent stops
  committing to looks nothing can carry out. Cycle detection asks whether a step MEETS an unmet
  want before it prunes, because the one lever that repairs freshness is the one whose world
  nets to nothing. And the met-test says what the agent WANTS rather than what would disappoint
  it, so a missing horizon reads as unmet rather than as perfectly fresh.
status: accepted
timestamp: 2026-08-24T18:00:00Z
---

# A lever an agent cannot pull is not a lever

Asked by the sovereign as a design rather than as a defect: *freshness should be declared as a
desire — that we have an observation and it was made recently — inside the sensing package, with
plans for how we achieve it. But it depends on the TYPE of sensor: can we request a new value, or
should we just wait and report that we cannot satisfy it?*

The second half is the sharp one, and it was already false on the bench.

## What was there: a row, an intention, and nothing

`packages/orexis-capability-sensing/actions.ttl` (then `affordances.rq`) emitted the Observe row on `sensing:polls`, which is
authored for both sense modes — the derivation keys `sensing:Subscribing` and `sensing:Listening`
off the DEVICE, and both branches read the same triple. `SensingModule.sense_now()`'s base
implementation is an empty method whose docstring says *ask for a reading now, if my hardware
allows it. Listening cannot.*

So a listening agent with a want it could not satisfy got the row anyway. The keeper adopted the
intention, called the method, nothing left the process, and the commitment stood until patience
outwaited it — at which point it was dropped and adopted again, for ever, with every module
behaving exactly as written. `world/simulation`'s supplier is that agent: it acts for the barrel,
its one instrument is a float switch, and the row's every hop held.

**The fix is a premise, not a check.** `rules.ru` derives `sensing:mayAsk` from the same fact it
derives the capability from, and the row hangs off that instead. `polls` is the access grant and
is granted for both clocks alike, because receiving is reading; `mayAsk` says the traffic can go
the other way. Where it is absent the want stands, hot, and the search answers — *no lever this
agent holds points at this want*, or, where a lever exists that cannot repair it, *nothing I
could reach is better*. Both are reported. Neither reads as a look that happened.

That is the generalisable claim, and it is why this record is not called "sensing modes". An
affordance is a CONCLUSION from premises; the premises must include being able to take it. A row
whose executor is a no-op is worse than a missing row, because the missing one is legible and the
present one manufactures evidence of trying.

**One shipped agent is a mixed case and it found the other half.** `world/loner`'s gardener
subscribes to a probe AND listens to a butt-level switch, so it composes two sensing modules, and
`Agent.provider(family)` returns whichever comes first — the listener. The look it committed to
on its probe therefore reached the module that cannot ask, and nothing went out. `providers`
plural exists for exactly the family where holding two is legitimate, and the keeper asks all of
them: whoever cannot ask does nothing when asked, so the no-op costs nothing and the one that can
finally hears.

# Knowing is a want, and it belongs to whoever holds the instrument

The kernel derived the freshness want, in `agent/desires.ru`, and built its met-test as a STRING
with `sensing#staleAfterS` spelled out where no prefix reaches — one of the entries the namespace
ratchet ([#334](https://github.com/ShishkinDmitriy/orexis/issues/334)) carried as unclassified.
It now lives in `packages/orexis-capability-sensing/desires.ru`, and four allowlist entries go with it:
the horizon term and three PREFIX lines that had nothing left to bind.

**This does not re-litigate [the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md),
and the line it draws is the one that record already drew.** What an agent wants, what a want IS,
when one is met, and the region derived from a subject's stated ranges all stayed in the kernel.
What moved is one want whose PREMISE is equipment: it exists because this agent polls something,
it is judged against a horizon that package publishes, and it is repaired by that package's
lever. A rule collecting `desires.ru` from every loaded package was already there for exactly
this — the loader's own comment said *a package that grows a kind of want ships its own* — and
this is the first one to.

## It states what it wants, and that is what makes it fail loudly

The met-test used to look for a reading whose `resultTime` plus the horizon had PASSED. A shape
that hunts for a bad reading is satisfied by the absence of any reading — and by the absence of
the horizon it would have judged one against, which is the state of every sensor before its
module's first `publish_horizon`. Measured on pySHACL 0.40.1 by taking the horizon triple away:
`conforms` flipped from False to True. The agent believed every reading current, for ever, with
nothing red anywhere. That is [#342](https://github.com/ShishkinDmitriy/orexis/issues/342), found
from the kernel-borrows-a-word direction and dissolved here from the other one.

Saying it positively — *a reading of this exists, made by this instrument, taken within the
horizon* — fixes both at the root, because with nothing to find, the NOT EXISTS holds and the
want reports unmet. The measure beside it fails the same way round through its own error-COALESCE:
an unbound reading time, an unbound horizon and any arithmetic that raises all land on 1.0. Not
knowing is maximal, as it is everywhere here, and a horizon nobody published must never read as
perfect freshness.

## `sosa:madeBySensor` is what keeps it a want about KNOWING

Every effect that moves a number states the move as a predicted reading, because predicting a
value is the only way to say a value changed. Nothing else in the vocabulary can carry it. So a
DOSE's effect and a LOOK's effect are both observations, and a freshness shape that asked only
for an observation of the pair was satisfied by either — and satisfied by the dose FIRST, since
`ag:Acquire` sorts before `ag:Observe`. A thirsty plant answered a stale reading by buying water,
once, in the pass that found this.

Only a look states who saw it. `sensed_writer` writes `sosa:madeBySensor` unconditionally on
every real observation, so the want asks for one made by ITS instrument and Observe's effect
predicts one — which it had to be taught, because the rule reuses the stored node and its
retraction takes every triple off it, so a prediction that did not restate the sensor came back
having erased it. Watering a plant does not tell you how wet the soil is, and this is the clause
that says so in a language the planner reads.

It also makes the want per-instrument in fact as well as in name: it was keyed by the sensor and
labelled *through* it while saying nothing about which instrument had spoken.

# Cycle detection is about expansion, not about refusing an answer

[a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) left a warning
exactly here, and this change is what made it live:

> A signature that counted a fresher `sosa:resultTime` as somewhere new would make each look a
> new world, and this becomes a live question again.

An observation canonicalises to its upsert key and its value, never its `sosa:resultTime`, so a
look nets to nothing and the world it reaches carries its parent's signature. That is right, and
it is what keeps "look, then water" impossible. It is also fatal to a goal whose whole content is
that something was read RECENTLY: the search computed the step, found the signature already seen,
and discarded it before anything asked whether it repaired the want.

**The fix is the ORDER, and not the canonical form.** A step is asked whether it MEETS an
unmet want before `seen` decides whether to expand from it. Cycle detection exists to stop the
search spending its depth budget on worlds it has stood in — and a step that answers the question
is not a place to search onward from, it is the answer. Everything the signature was built for
survives: a look still extends the frontier nowhere, so no plan chains past one, and #254's
depth-1 defect stays fixed. Putting the timestamp into the signature was the alternative and it
breaks precisely that: every look would be a new world, "look, then look, then look" a three-step
plan.

**The guard on the guard is `met_now`.** With the want already met, a look leaves it met, so
without that clause every calm agent would answer *look* on every tick — a step that changes
nothing, reported as achieving something. Met and still urgent is steering toward the pick, which
is what the satisficing branch below it is for. Measured both ways: with the clause reverted to
the old order, three tests fail and every one of them is an agent that has stopped looking.

# What the deletion proves

`agent/deliberator.py` opened with `if desire.state in ("unmeasured", "stale"): return OBSERVE`.
It is gone, and nothing replaced it. That was the plan record's own acceptance test — *two
hardcoded things must DISAPPEAR, not survive beside it* — and the second of the two took two
changes to remove: phase B deleted the reflex around it, and this deletes the branch itself by
making the want it recognised into a want the search can reach.

Three consequences worth having in one place, because each surprised somebody:

- **An unmeasured REGION want is not repaired by looking, and that is correct.** A first look
  predicts an observation with no result, and the region's Below and Above shapes are
  `sh:qualifiedMaxCount 0` over readings past an edge — a valueless reading vacuously satisfies
  *past this edge*, so it trips both. The region want stays unmet and the freshness want beside
  it is what proposes the look. The two used to be one hardcode; they are two wants with two
  answers, and only one of them is about looking.
- **The keeper's tick asks about every want.** Its filter for `unmeasured`/`stale` was the other
  half of the hardcode — it knew which wants would say OBSERVE because a branch decided it
  before any search ran. Nothing knows that now, so it asks about all of them and carries out
  the one answer it is entitled to. The cost is a plan per want per patience period, which is
  the work `series()` already does on the metrics clock.
- **`propose_about` has to choose.** Two wants about one property, and the actors' door means
  the number — except while the number is not known, where it means the look. Stated as a rule
  (an unmet epistemic want answers first) rather than left to whichever is hotter, because both
  are legitimately 1.0 on a dry pot with a cold reading.

# Seams left open

- **The measure is binary, and the gradient waits on the price of looking.** Age-against-horizon
  is the natural continuous form. It is not what shipped, because with no cost on a look, any
  nonzero freshness urgency makes looking an improvement and the agent nudges its board on the
  patience clock rather than on the cadence. The region want's deadband comes from the dose
  sizing to nothing near the aim; a look has no analogue, since it always fully refreshes. The
  trigger is [sensing](/domain/sensing.md)'s standing seam — *sensing is not yet priced* — and
  when a look costs something, the gradient becomes rankable against it.
- **An Observe row is bound to the agent's own subject.** The row's walk demands
  `$me ag:actsFor ?subject`, so an instrument pointed at something the agent does not act for
  has no row even where the agent could ask it — the loner's water butt is unreachable twice
  over. Fixing it means the effect rule taking the row's subject as an argument instead of the
  agent's, which is a change to what a step is bound with rather than to any of this.
- **Self-review moving the horizon or the cadence.** The sovereign named it as a later step and
  it is not built. Both are settings and
  [control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md)
  governs: what a review may move is `sensing:slowSleepS` and `sensing:maxReadingAgeS` inside the
  room a world's `review:commits` leaves, never the horizon triple itself — that is published
  from the rhythm in force, and a review that wrote it directly would be writing a conclusion
  rather than moving the premise it comes from.
- **Two probes on one (subject, property).** Observe's effect binds its sensor by joining the
  wiring, so a pot with two probes predicts two readings — and each probe's freshness want is
  then repaired only by a prediction naming it. That wiring is already a `sh:Warning` at
  validation ([one-agent-many-sensors](/decisions/one-agent-many-sensors.md)) and no shipped
  world has it.
