---
type: Decision
title: An Always want is a root for the agent's whole life, and what is pursued is derived from it
status: accepted
timestamp: 2026-09-12T12:00:00Z
description: >-
  The sovereign's split of 2026-09-12, recorded before it is built. An Always want is a ROOT —
  law for every search, the premise of what is pursued, and never pursued itself. What is
  pursued is a want derived from it with a binding of its own, a lifetime and a definition of
  done — at-end when the root's shape is violated now, at an instant when a prediction says it
  will be — minted at runtime as a promise is and withdrawn when met. The binding roots the
  search — forward from the present for the first, from the node the present's drift reaches
  at the instant minus the plan's duration for the second, its steps placed backward from the
  instant. One search, two roots; the backward walk chooses instants, never states. PDDL 2.2
  and 3 map onto it term for term. Refused — planning now and letting the verdict catch the
  night, a measure that hides a time room inside a MAX, regression in state space, and a
  second planner as a capability.
---

# The claim

**An `orexis:Always` want is a root, and it is never pursued.** It is the agent's for its whole
life — every subject on the roster inside what it states it needs — and it does two jobs,
neither of which is being searched for. It is LAW: every state of every candidate plan is held
to it, which is what never-newly-enter already does with the Always wants an agent holds. And it
is the PREMISE of what is pursued: a [root desire](/domain/root-desire.md) in the forest's
sense, with the pursued wants derived under it.

**What is pursued is derived from the root, with a binding of its own, a lifetime and a
definition of done.** Two kinds, by what implies them:

- **Violated now.** The reading's band is outside the region. A want bound `orexis:AtEnd` is
  derived under the root, naming the root and the reading in PROV. Its room is the root's state
  room, inherited, since an at-end want has none of its own ([urgency](/domain/urgency.md)). It
  is pursued forward from the present, and it is gone when its intention resolves met.
  [#618](https://github.com/ShishkinDmitriy/orexis/issues/618).
- **Predicted to be.** The drift's crossing — from the observed value, or the band's own width
  over the rate where only the band is known ([effect](/domain/effect.md)) — says when the
  reading leaves its region. A want that must hold AT that instant is derived under the root,
  naming the prediction in PROV. Its room is time, by the binding. It is pursued from the node
  the present's own drift reaches at the instant minus the plan's duration, its steps placed
  backward from the instant, and it too is gone when met.
  [#619](https://github.com/ShishkinDmitriy/orexis/issues/619).

Both are minted at runtime, as the promise road mints a want for a taker-less step and withdraws
it on the verdict ([bridge](/domain/bridge.md)). Neither is authored, and a world file names
neither. The desires modality holds the roots, the children while they live, and nothing else
that is pursued.

**The binding roots the search.** One engine, and where it begins is the child's to say. An
at-end child begins at the present, as every pass does today. An instant-bound child begins at
a node of the same tree — the present advanced by every declared drift to the instant minus the
duration, a happening edge in the sense of
[planning-branches-on-action-forecasting-on-belief](/decisions/planning-branches-on-action-forecasting-on-belief.md),
reached by nobody choosing — with the pass's clock set there, so every step's rule reads the
forecast holding at its own landing through the door that already honours a period. **What is
chosen backward is the instant of each step, never a state.** Effects are constructs run forward
at their instants as they are today, the goal stays a shape, and nothing declares an inverse.
Where a step's instant is fixed by the world's schedule rather than by subtraction — a round
convened by day for a dose at night — the walk regresses preconditions in time, which is
[#620](https://github.com/ShishkinDmitriy/orexis/issues/620) and waits for its customer.

**An instant-bound want is met AT its instant, not by it.** A dose at noon that lands in region
and drifts out by night has not prevented the night, so the end world of a candidate plan is
judged with the drift applied from its last landing to the instant. `orexis:Within` means *by* a
deadline and is refused for this. The value the axis needs is #619's first decision, and PDDL3's
word for it is `hold-after`.

# What the sovereign saw, and what was measured

Planning from now picks the wrong plan for tonight. The greenhouse shows it: a vent judged this
afternoon lands the bed in region and is planned; the same vent at 21:00 against the night's
forecast lands it below, and only the heater meets. Measured on main at `4d3700c`:

- a STEP is already grounded at its own instant — `Planner._at` is the pass clock plus the path's
  landings, it reaches the door as `when`, and `public_graphs(at)` hands a rule only the graphs
  holding then (#589);
- the ROOT is always now — the pass clock is read as the wall clock at `_search` and again at
  re-root — and the only way time passes inside a cone is a step's own landing, so no node stands
  at tonight unless a step takes until tonight;
- a dose from INSIDE the region is not pruned as already reached, contrary to the comment on
  #607. With a stand-in time-room urgency at the root, the gardener at 0.12 plans one dose, novel
  by the diff `−[zz,SoilMoisture=0.12]` — the observed value gone, the band unchanged — because an
  observation carries its result into the canonical fact. That novelty is an accident of a
  band-only reading differing from a valued one; the projected root above is what makes the
  comparison honest, an early act weighed against where the pot WILL be rather than where it is.

# What it makes structural

The binding record already says it in one sentence: maintenance is delivered by the loop, and
re-deliberation converts an Always want into repeated at-end achievement
([shall-must-and-may-are-not-strengths-of-one-scale](/decisions/shall-must-and-may-are-not-strengths-of-one-scale.md)).
Today that at-end goal is implicit — the pursued want IS the root, and the planner's law holds
the same roots as constraints — so one node does two jobs and nothing says which. The split
gives the per-pass goal a node with a binding, PROV and a definition of done, which is the forest
of [a-desire-is-a-forest-of-derived-roots](/decisions/a-desire-is-a-forest-of-derived-roots.md)
with one more kind of premise: a belief. Every premise in that forest is ratified; a prediction is
the agent's own, and the child that names it is regrown from it exactly as the tree is regrown
from its ratified premises.

It also settles #607 more honestly than #607's own sketch, which had the stake's measure answer
the larger of a state room and a time room. Deriving the instant-bound child says the same thing
by the binding, which is the axis that exists for it — one room per want, and no MAX.

# PDDL, term for term

Asked by the sovereign, and worth one table: the repo has been converging on PDDL 2.2 and 3 in
RDF for a month, and naming that lets the literature be read against the issues directly.

| PDDL | here |
|---|---|
| `always φ` constraint — prunes trajectories, never drives the planner | the root: law and premise |
| `at end φ` goal | the at-end child, #618 |
| `hold-after t φ` | the instant-bound child, #619 |
| `within t φ` | `orexis:Within`, the obligation's deadline |
| timed initial literals (2.2) | a forecast graph holding during a period, #589 |
| durative actions (2.1) | an action with a duration, #596 |
| derived predicates (2.2) | the entailment, and #108's saturation |
| preferences (3) | the soft severity |
| a temporal network over deadlines | #591, and #620's placement |

# What was refused

- **Planning now and letting the verdict catch the night.** It is what the code does, and it is
  why the greenhouse would vent this afternoon against a night it can already read. The keeper's
  verdict catches the breach a night late, and the pass that follows plans from inside it.
- **A measure that hides a time room inside a MAX** — #607's sketch. It makes an Always want
  behave as a Within want while the axis says Always, and every reader of the binding is then
  wrong about which room is being consumed. Absorbed into #619.
- **Regression in state space** — #489. A want is a shape, a set of states; an effect is a
  construct with no inverse. Neither has changed, and neither is needed, since the instant is
  what is chosen backward.
- **A second planner as a capability.** The search is the mind's and the mind is not a package.
  There is one search rooted two ways, and the backward walk of #620 is deliberation's own.

# Seams left open

- **Whether the at-end child earns its node.** Its consumers are the selector between the two
  roots, the definition of done and the ask channel's why. #618's measurement — every shipped
  world planning exactly as today — is what decides, and a level nothing consumes is a level to
  fold back.
- **How far ahead a prediction is worth a want.** Far enough and a drift says anything. The
  policy sits beside the root, and the honest bound is the horizon the reading carries.
- **A crossing that flickers** derives and withdraws a child per flip — #615's dwell, one level
  up.
- **Two children under one root at once** — below now AND predicted to be dying. Hottest wins,
  as today; nothing here composes them.
