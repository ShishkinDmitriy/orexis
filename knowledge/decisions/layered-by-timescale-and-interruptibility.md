---
type: Decision
title: The layers are timescale and interruptibility, and intention progression is the middle one
description: >-
  Three-layer architectures are usually drawn as push versus plan, which puts the wrong work in
  the wrong place — a sensor handler that calls a model, a plan step that spins waiting for a
  value. Decided that this society is layered by how long a piece of work may take and whether
  it may be interrupted, that the belief base is the interface between the layers rather than
  plumbing under them, and that the middle layer is BDI's own contribution over Gat and Firby —
  not sequencing, but intention progression, which carries commitment across the gap between
  two deliberation episodes.
status: accepted
timestamp: 2026-08-26T16:00:00Z
---

# What was true before

The code already had three kinds of work and no name for the split. Handlers decode a reading
and write it; the keeper holds what the agent is committed to and hands a standing act to an
actor when a trigger changes; the deliberator searches. Every record so far argued one of them
in isolation — [an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md),
[a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md),
[sensing-owns-the-reading-pipeline](/decisions/sensing-owns-the-reading-pipeline.md) — and
nothing said which layer a new piece of work belongs in, which is the question a contributor
actually has.

# What is decided

**The axis is latency and interruptibility, not push versus plan.**

| | latency | interruptible | searches |
|---|---|---|---|
| reactive | ms | n/a — atomic | no |
| progression | s–min | suspends | no |
| deliberation | s | should be | yes |

**Reactive** is the event handlers: `handle(channel, payload)`, offered to every module by
whoever holds the connection. Bounded, non-blocking, no search. Their job is to **classify and
write** — decode, scale, upsert an observation, take a bid into the round, note a device's
status — never to decide.

**Progression** is executing what is already committed. It is neither reactive (it spans time
and holds state) nor deliberative (it searches nothing): the keeper's ledger, `take_standing`,
and an [actor](/domain/actor.md) answering False for *not now* so the [intention](/domain/intention.md)
stands until a trigger changes the answer. This is the layer BDI names and a generic three-layer
architecture does not — Gat's 3T, Firby's RAPs and Bonasso all have a sequencing layer, and what
BDI adds is that its contents are **intentions with a lifecycle**, which is what carries
commitment across the gap between two deliberation episodes.

**Deliberation** is the search: `decide` over the [imaginarium](/domain/imaginarium.md), ranked
by simulation. Slow, and it should be interruptible. It runs when something goal-relevant moved.

**The belief base is the interface, not plumbing between the two.** It is what decouples the
cadences — a handler writing at the board's rhythm and a search reading at the agent's — and it
is where the timestamps and the instrument live that make freshness a question anyone can ask
rather than a guess. Every hard question so far settled there and not in either neighbour:
staleness became a want with a measure ([the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md)),
a dead sensor became a freshness want going cold rather than a special case
([a-test-that-asserted-nothing](/decisions/a-test-that-asserted-nothing.md)'s neighbour, #124),
and event thinning became the upsert key plus the summary window
([one-agent-many-sensors](/decisions/one-agent-many-sensors.md), [review](/domain/review.md)).
What decides whether a write is worth waking the deliberator for is the revision function, not
the handler that produced it.

**The rule that falls out**, and it is the reason to write this down: *anything that blocks
belongs in progression, anything that searches belongs in deliberation, anything that must never
block belongs in the reactive layer.* Most architectural mistakes are one piece of work in the
wrong row.

**Where the model sits.** A model may be asked in **deliberation only**. Sensing's cadence, the
bid arithmetic and the dose are deterministic code and stay so
([deterministic-bid](/decisions/deterministic-bid.md)); a plant agent stays committed to a water
grant through progression while readings keep arriving underneath it, and no handler ever waits
on anything.

# What is already true of the code

- **Reactive**: every `handle`, and sensing's decode/scale/upsert path. None of them blocks.
- **Progression**: the keeper's ledger and its patience tick, `execution.take_standing`, the
  bidder's give-up timer, the host's bid window, actuation's sweep — each on a `Timer` of its
  own, so a wait is a suspension and never a spin.
- **Deliberation**: `Planner`, over a per-pass imaginarium that is dropped with the pass.
- **The lifecycle, in the words the ledger already uses**: adopt; *stands* (BDI's suspended —
  the act is committed and its actor cannot act yet); satisfied; dropped, including *outwaited*,
  which is supersession by a fresher decision. Fail is a separate fact rather than an outcome:
  satisfied-and-`endMet` false is the false-knowledge signature
  ([an-intention-stands-until-the-world-answers](/decisions/an-intention-stands-until-the-world-answers.md)).

# What this makes wrong, and it is wrong today

**A search runs on the transport's network thread.** A reading arrives, sensing writes it and
tells the choir, and actuation's and bidding's `on_reading_recorded` call
`execution.pursue_for`, which calls `decide`, which searches — all inside `handle`, on the
callback thread. That is deliberation in the reactive row: it blocks every other message for the
length of a pass, and a slow deliberator (a model, later) would stall the bus. Filed as
[#392](https://github.com/ShishkinDmitriy/orexis/issues/392) rather than fixed here, because
the fix is a design choice — a queue the deliberator drains on its own clock, or a marker the
belief base's revision function sets — and this record is what makes it visible.

# Seams left open

- **No explicit suspend/resume/fail vocabulary.** The ledger says stands/satisfied/dropped and
  the meanings above are read off those; naming them would be a vocabulary change with no reader
  yet.
- **Deliberation is not interruptible.** The table says it should be; a pass runs to completion.
  Bounded depth is what keeps that affordable, and a model in the loop is what would end it.
- **The revision function is implicit.** What is worth waking the deliberator for is decided by
  who calls `pursue_for` and when, not by one named function over the belief base.
