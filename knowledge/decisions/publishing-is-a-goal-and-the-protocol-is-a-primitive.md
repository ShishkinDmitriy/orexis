---
type: Decision
title: Publishing is a goal and the protocol is a primitive — and the outbox is where that pays
description: >-
  Modelling the bus as BDI splits into two proposals with opposite verdicts. Deciding to send,
  where to send, and what to do when delivery fails HAS alternatives and deadlines, so it is a
  goal — and delivery failure then becomes a deliberation input rather than an exception out of
  a socket. Framing, keepalive, acknowledgement correlation and reconnect backoff are mechanical
  and live three orders of magnitude below the interpreter's cycle, so they stay a library. The
  line is drawn at retry semantics, and the place the instinct actually pays is the outbox — a
  pending message as a committed intention, droppable when the goal that motivated it is.
status: accepted
timestamp: 2026-08-26T22:00:00Z
---

# The two proposals

**Weak: publishing is a goal, not a primitive.** Right, and worth building. The apparatus
already exists here and comes free — an [action](/domain/action.md) with a precondition and an
effect, an [intention](/domain/intention.md) that stands until the world answers, a window
(`ag:notAfter`) that is already what every hand-kept timer says, and a compensation the actor
declares. The prize is the last one: *delivery failed* stops being an exception and becomes a
fact the search can weigh. If a plant cannot get its bid to the venue, that is not a socket
error — it is a reason to reconsider the want that motivated the bid.

**Strong: the protocol's internals as beliefs and desires.** No, and not because it is
unprincipled. Two costs settle it.

*Timescale.* The interpreter cycle runs at deliberation's pace — tens of milliseconds at best,
and a model in the loop makes it seconds
([layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md)).
Retransmission lives at the millisecond. Keepalive scheduling, acknowledgement correlation and a
four-way handshake on a scheduler built for the wrong row is a protocol stack with a planner
inside it.

*Regress.* Publishing becomes a goal that requires a connection, which requires publishing a
CONNECT, which requires a connection. The cycle breaks on a primitive somewhere, so the only
question is where — and the answer is **below anything with retry semantics**.

# The line

| goal | primitive |
|---|---|
| whether to send at all | framing |
| which channel, which counterparty | keepalive |
| what to do when delivery fails | acknowledgement correlation |
| whether to escalate to another route | reconnect backoff timing |

The client library stays a library; the decision to use it becomes a plan. In this tree that
has a shape: a `Delivering` action node in the transport package, `ag:takenBy` the link that
holds the connection, its window the deadline the message is worth anything by — the same
mechanic as every other action, in the package that owns the words
([the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md)).

# Where the instinct actually pays: the outbox

Not in the protocol — in **the outbox as an intention**. A pending outbound message is a
commitment with a deadline, survivable across a reconnect, and — the one thing no transport
queue can give — **droppable when the want that motivated it is dropped**. When a plant loses the
round, its unsent bid should be retracted, not eventually delivered. A retry queue faithfully
delivers a message the agent no longer means.

Two things to watch, and both are rules this project already holds:

- **Suspend, never block.** The outbox intention must not hold the interpreter while the network
  is away — it stands, and the trigger that changes the answer takes it, exactly as a bid with
  no round stands today.
- **Give-up needs a declared compensation.** A message that half-sent may or may not have
  arrived, which is the delivery form of the irreversible-actuation problem: what an agent does
  about *possibly delivered* is a decision, not a default.

# What is true today, and why it is survivable

`Module.publish` tells `send`, and the link publishes at QoS 1, fire and forget. There is no
goal, no failure path into deliberation, and no retraction — a message queued while the session
is away is delivered by the client whenever it returns, whatever the agent has since decided.

What keeps that from hurting yet is **idempotence at the receiver**, and it is worth naming
because the outbox would inherit it: a bid is keyed by (round, bidder), so a duplicate
overwrites rather than doubling; a late bid names a round the host has closed and is dropped on
arrival; a claim carries a `jti` that is single-use. The hazard the outbox closes is not
corruption, it is **meaning** — a bid the agent no longer means arriving anyway, and an agent
that cannot tell a lost bid from a losing one.

# Order of work

1. The outbox (#396, landed) — **and not as a new action**. What it was wanted FOR is one
   guarantee — a message the agent may stop meaning is never handed to a queue — and the act
   that carries the message already had every part of it: an [intention](/domain/intention.md) that stands, a
   window, and an [actor](/domain/actor.md) whose False means *not now*. So `ag:send` answers
   whether the message LEFT, a message that states when it stops mattering is refused rather
   than queued while the link is down, and the Acquire stands until the round's close drops it.
   A `Delivering` action node buys nothing over that and would put a second machinery under the
   first; it is worth minting the day a message has no act behind it — the sovereign's reply, or
   an escalation to a second route.
2. Delivery failure as a want the search can answer — only once something branches on it, by
   [model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)'s
   test. *Escalate to another route* is the first plausible branch and needs a second transport.

# Seams left open

- **No second route.** *Escalate to HTTP* is the branch that makes delivery failure worth
  deliberating about, and there is one transport.
- **The client's queue and the act still overlap, narrowly.** Nothing with a deadline is
  queued now, so the case that mattered is closed without touching what the broker guarantees.
  What remains is a publish already in flight when the session drops: paho will retry that one,
  and the receiver's idempotence is what makes it safe. Owning the retry outright still means
  QoS 0, and that is still a decision rather than an implementation detail.
- **Nothing declares a compensation for a half-sent message.** The vocabulary exists
  (`ag:retracts`, the confirmation routes); nothing uses it for delivery.
