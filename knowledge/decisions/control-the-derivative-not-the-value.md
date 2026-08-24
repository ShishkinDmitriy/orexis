---
type: Decision
title: Control the derivative, not the value
description: >-
  The design principle the project kept applying without naming — stated once, by the
  sovereign's analogy. When you walk you control distance; when you drive you control
  acceleration. Nothing here controls a step - not a reading, not a moisture level, not a
  move. Every layer controls the rules of the layer below - a cadence not a reading, a region
  not an aim, a mandate not a belief, an affordance not an action - and the tower is why the
  sovereign can leave the room at start: control exercised entirely through rules needs
  exercising only once. Predictive, not decorative - any change that reaches down a level (a
  deliberator setting a price, a sovereign pinning an aim, a model emitting an action) is
  grabbing the walking-controls from the driver's seat, and is refused on sight.
status: accepted
timestamp: 2026-08-14T00:00:00Z
---

# The principle, in the sovereign's words

> When you walk, you control the distance. When you drive a car, you control acceleration —
> the second derivative. Here it feels the same: you don't control each step, you control
> rules. Even when we poll sensors, we don't poll them — we define cadence.

That is the move this project has made at every level, each time as if for the first time.
Stated once, here, so the next design conversation can cite it instead of rediscovering it.

# Where it already holds

| level | never controlled | controlled instead |
|---|---|---|
| sensing | the reading | the **cadence** — itself only within bounds: firmware clamp, agent clamp, constitutional clamp |
| desire | the moisture | the **aim** — a pick inside a region the agent does not control either |
| the sovereign | the aim | the **region's sources** — plant ranges, ratified once; the pick is never theirs |
| review | the belief | the **rule for re-picking** — and the mandate bounds how far, which is a bound on the *rate of drift* |
| intention | the acts | the **patience** — not "act now" but how long a commitment absorbs impulses |
| the model | the move | the **rules that produce moves** — it writes an affordance; the search exploits it forever |

The rows compose into a tower of derivatives: the agent sets the cadence (the rate of
attention), review moves the cadence *setting* (the rate of change), the mandate bounds review
(the sovereign controlling how fast an agent may change how fast it changes). Each layer's whole
authority is the next layer's parameter space.

The domain even echoes it physically: a pot is a first-order system — it dries at a stated
velocity (`ag:modelLosesPerDay` in the stand-ins, per simulated day since the physics went
time-based), moisture drains on its own — and watering is an impulse against that velocity. The
agent perceives position and only ever touches higher derivatives, which is cybernetics' old
slogan (*you control your perceptions, not your actions*) arrived at from the other end.

# Why the sovereign can leave the room

This is the same fact as
[the-model-is-consulted-at-the-edge-of-knowledge](/decisions/the-model-is-consulted-at-the-edge-of-knowledge.md)'s
governance split, seen structurally. A sovereign who controlled positions would have to stay —
every step would need them. One whose control is entirely in rules — ranges, mandates, shapes,
the constitution — exercises all of it at genesis and can vanish at start, because there is
nothing left for them to do that is not already done. The interface disappearing at runtime is
not a limitation the design tolerates; it is what the design predicts.

# What it refuses

The principle earns its place by being predictive: it says what the next mistake looks like.
Any change that reaches **down** a level is grabbing the walking-controls from the driver's
seat, and is refused on sight:

- a deliberator that sets a bid *price* — the whether is its; the how much is
  [deterministic-bid](/decisions/deterministic-bid.md)'s;
- a sovereign field that pins an *aim* — the world states ranges; a pick written in `world.ttl`
  is an agent's end authored by someone else;
- a model that emits an *action* — it writes rules (affordances) or it writes nothing;
- a shape that fixes a *value* where it should bound a range — the constitution clamps, it does
  not choose.

# What this record is not

Not a new rule — every row of the table is already enforced by its own decision, shape or test.
It is the *why* behind
[a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md),
[self-review-is-a-capability](/decisions/self-review-is-a-capability.md)'s mandate,
[the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)
and the edge-of-knowledge design, said once instead of implied four times.
