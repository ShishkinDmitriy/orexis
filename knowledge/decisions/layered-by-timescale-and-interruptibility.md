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

| [row](/domain/row.md) | latency | interruptible | searches |
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

# What this made wrong, and what fixed it

**A search ran on the transport's network thread.** A reading arrived, sensing wrote it and
told the choir, and actuation's and bidding's `on_reading_recorded` called through to `decide`,
which searched — all inside `handle`, on the callback thread. That was deliberation in the
reactive row: it blocked every other message for the length of a pass, and a slow deliberator
(a model, later) would have stalled the bus.

**Fixed (#392).** `revision.wake` leaves a [mark](/domain/revision.md) and returns, and the
marks are drained on a thread of the mind's own, started with the agent and stopped with it. Three consequences worth
knowing, because each is the rule showing its teeth:

- **A handler cannot learn what the search decided**, and two callers had been reading it. The
  bidder found out at once that nothing was proposed; it finds out at the round's close now,
  through the give-up it already kept — the more honest moment, since a reading arriving
  mid-round can change the answer. The host logged *stands unserved* on a presentation nothing
  pursued; the claim simply stays held, which is what happened anyway, and the ledger is the
  evidence rather than a log line.
- **The window moved to where the act is taken.** `on_offer` used to write the bid's
  `ag:notAfter` onto the intention it had just adopted; the actor writes it in `take`, from the
  round row it reads there — which is where the act record said it belonged.
- **The keeper's tick still searches synchronously**, deliberately: it is the mind's own clock
  rather than a callback, so marking there would only queue work for the thread already
  running it.

**Marks are deduplicated by want**, which is the beginning of the filter this record asks for:
ten readings between two passes leave one mark. What is still absent is the judgement — *did
this change anything a plan could branch on* — and that belongs in the same file.

# Seams left open

- **No explicit suspend/resume/fail vocabulary.** The ledger says stands/satisfied/dropped and
  the meanings above are read off those; naming them would be a vocabulary change with no reader
  yet.
- **Deliberation is not interruptible.** The table says it should be; a pass runs to completion.
  Bounded depth is what keeps that affordable, and a model in the loop is what would end it.
- ~~**The revision function is implicit.**~~ Named: `agent/revision.py` is the seam, and
  `wake`/`wake_for` are the one door from a change to a pass. It is thin on purpose — the rule
  it runs is still *something moved, so reconsider the want it moved* — and what it buys is
  that #392, a band filter over churning self-telemetry, and any infrastructure projection are
  each a change to one file.
