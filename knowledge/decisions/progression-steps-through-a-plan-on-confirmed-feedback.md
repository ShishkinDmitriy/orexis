---
type: Decision
title: Progression steps through a plan on confirmed feedback
description: >-
  The sovereign's ruling on the three layers (2026-09-02). Deliberation hands the WHOLE plan
  down; progression commits the head as now and keeps the tail on the intention as its
  expected continuation, each step carrying the world change it predicted; when the head's
  expectation is answered and the world matches the prediction, the next step is adopted with
  no search, and a failed expectation or a world that differs drops the tail and asks
  deliberation again. Refused: re-planning every tick (an eight-step delivery is eight
  identical searches); committing the tail unconditionally (a promise about a future nobody
  has seen — the earlier record's objection, which this answers rather than overrules);
  re-simulating the next step against the live world before taking it (the prediction was
  already checked by the feedback, and re-simulation costs a pass's setup).
status: accepted
timestamp: 2026-09-02T22:00:00Z
---

# Progression steps through a plan on confirmed feedback

The three layers were designed as a dumb executor, a scheduling-and-feedback layer beneath the
planner, and the planner on top: deliberation decides a plan, hands it down, and the middle
layer executes it step by step, waiting on feedback and calling the executor. The layers as
built match that in every respect but one. Every act is taken on the reactive loop's one
thread; the keeper adopts intentions, keeps patience and waits on an expectation with a
deadline; the search runs on its own worker. But progression never received a plan. The
deliberator handed it the plan's FIRST STEP alone, and the next tick ran the search again.
[an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md)
argued for that: a committed tail is a promise about a future nobody has seen, so the tail is
trace, not ledger.

That was right when a pass cost a second and a plan was two steps. The courier changed the
arithmetic: an eight-step delivery is eight full searches producing the same plan eight times,
and a solve of hanoi seven. So the ruling: **deliberation hands the whole plan down, and
progression steps through it on confirmed feedback.** The head is committed exactly as now.
The tail rides on the intention as its expected continuation, each step carrying the change
it predicted — the canonical diff the search already computes for cycle detection. When the
head's expectation is answered and the world's actual change matches the step's prediction,
progression adopts the next step with no search above it. When the expectation fails, or the
world after the step differs from the prediction, the tail is dropped and the question goes
back to deliberation.

This answers the earlier record's objection rather than overruling it. The tail is not a
promise about an unseen future; it is conditional on each step's prediction being confirmed,
and confirming a prediction is the check the middle layer already makes. What changes is only
that a confirmed prediction now advances the plan where it used to start it over.

# What was refused

**Re-planning every tick**, the shipped behaviour. Correct, and affordable for a plant whose
plan is one or two steps. Wasteful the moment a plan is long: the same search, the same
answer, eight times, at a fifth of a second each on the bench and more on a large world.

**Committing the whole plan unconditionally.** The earlier record's objection stands: a tail
taken without checking each step's prediction acts on a world nobody has seen. This record
keeps the check and changes only what a passed check leads to.

**Re-simulating the next step against the live world before taking it.** The sovereign's
choice was feedback alone. The step's prediction was checked against the world when the
expectation was answered; simulating it again would ask the same question with a pass's
worth of setup — an imaginarium, the wants snapshot, the compiled select — for a fork and a
rule run. A world that has moved shows up as a failed match, which is the case that re-plans.

# Amended 2026-09-07: what matches means is identification

The seam below that asked what "matches" means closed with #554. The keeper's verdict still
holds one committed step to its prediction, and the tail still drops on a surprise; what
changed is what happens to the search's worlds afterwards. They are kept (#553), and the next
pass identifies the present among them within the want's view
([identification](/domain/identification.md)): a step that landed as predicted resumes the
cone at the child it reached, a step that landed in a sibling the search explored resumes
there, and a present no kept world matches starts a pass from nothing. Matching is exact
within the view until intervals (#556) give a prediction a width.

# Seams left open

- **What "matches" means** — settled in the build: the step's canonical diff is held to the
  world as a generated shape, and how close a reading must land is the actor's own pick,
  [the-effect-is-one-declaration-and-the-tolerance-is-a-pick](/decisions/the-effect-is-one-declaration-and-the-tolerance-is-a-pick.md).
- **A look still ends a plan.** A sensing action's tail depends on what the look returns, so no
  tail follows one; that rule is unchanged.
- **The budget and the tail.** A pass that ran out of budget hands down the best plan it had,
  whose tail may be short of the goal; stepping through it and re-planning at its end is the
  tick model of a long horizon, now with fewer searches.

# Issues this emits

The build is filed beside this record; see the roadmap.
