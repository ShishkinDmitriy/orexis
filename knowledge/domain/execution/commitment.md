---
type: Domain Concept
title: Commitment
description: >-
  What an intention holds the agent to, in two grains. HARD on the step in flight - handed to its
  taker and not yet answered, it is never cancelled by planning. SOFT on the plan - a walking want is
  neither searched again nor withdrawn, until its one trigger - a want a constraint couples to it
  arriving - reopens it, and the untaken steps are open to replacement.
---

# Two grains

An [intention](/domain/execution/intention.md) commits the agent to a plan, and the commitment is not
one thing. It is single-minded in Rao and Georgeff's sense — kept until achieved or believed
impossible — with a reconsideration trigger defined in advance, and never open-minded replanning
every pass. Its two grains are where the line between those runs.

**A step in flight** is a [step](/domain/execution/step.md) an intention stands at that has been
handed to its taker — an [act](/domain/execution/act.md) on record saying it was taken — and that the
world has not answered yet. The executor holds it to its prediction from its earliest landing to a
patience past its latest.

- **Hard, on the step in flight.** Nothing planning decides cancels it. A step blocked is a head not
  yet taken; a want reached ends an intention none of whose steps was taken; a reconsideration ends
  an intention after its step in flight, `execution:endsAfter`. The step can still fail by itself —
  the world answers otherwise, or the patience runs out — and that ends the intention `failed`.
- **Soft, on the plan.** The untaken steps are the plan's, and a plan is kept by default rather than
  bound. A committed step not yet started is a prediction and not a commitment
  ([committed-step](/domain/execution/committed-step.md)), and a replaced plan takes its windows with it.

# Walking

A want is **walking** where a standing intention pursues it, or a plan published and adopted by no
intention yet pursues it — read off execution's rows by `Planner.walking`. It is planning's view of
the soft grain: a walking want is not searched again, its plan is not handed down again, and its
desire reading met or unmet does not withdraw it, since the world has not answered yet.

# The one trigger, and what follows it

**A want a constraint's footprint couples to a walking one arrives.** In the derivation that is a
cluster the [constraint](/domain/planning/constraint.md) coupled which is about every instance a
walking want under the same desire is about, and more — a parcel arriving whose van can meet the one
a plan is driving. The want minted for it **reopens** the walking want, `planning:reopens`, and is
minted at the instant the walking want's step in flight lands. Nothing else reopens a walking want:
a cheaper plan found, a second want no constraint couples, or a desire read again leaves it walking.

1. **The search starts where the step in flight has landed.** A pass lays a ground boundary at each
   such landing — its `execution:landsAt`, shifted by how late it was taken, as the executor reads it
   — and the reopening want is searched from that ground, so the plan it finds begins after the step.
   What that ground holds is what the agent already sees holding then: a fictive step wrote its
   effect into the present when it was taken, and a step a drift reads is in the predictions.
2. **The joint plan agrees where it begins with the walking intention's untaken steps**, compared by
   the action each fills and the values it is filled with, never by node. Then the intention stands
   untouched — adopted when it was, ended by nothing — and only the new part of the joint plan is
   published, opening where the joint plan put it, after the kept steps. A joint plan that walks the
   same steps later does not agree: two intentions are walked side by side, and nothing holds a step
   of one after a step of the other.
3. **Otherwise the walking intention ends after its step in flight**, `superseded` — planning
   decides, execution ends, as for a step blocked — and the joint plan is adopted whole. A van turning
   back is a legitimate outcome, found by the search and decided by nobody.

Why this and not the alternatives — the elder plan as the younger's ground, conflicts reconciled
afterwards — is [one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md);
how planning and execution say these things to each other is
[planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md).
The derivation's half is held by `agent/planning/tests/derive_wants/a_coupled_arrival_reopens_the_walking_want.trig`,
the dispatcher's arrivals by `world/dispatcher/tests/test_dispatcher.py`, and what a reconsideration
costs is in [measure-the-search](/runbooks/measure-the-search.md).
