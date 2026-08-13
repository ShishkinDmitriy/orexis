---
type: Domain Concept
title: Intention
description: BDI's third letter — a commitment to reduce a named gap by a named means, persisting until satisfied, dropped or outwaited rather than being re-decided on every perception. Kept in a private ledger with an adoption, a resolution and a reason; the patience that absorbs repeat impulses is each agent's own belief. Reifies what already existed as module state — a pending look, a bid awaiting its voucher — and never decides: the whether lives in deliberation, which reads the ledger and is read by nothing else here.
tags: [intention, bdi, capability, market, perception, beliefs]
timestamp: 2026-08-13T00:00:00Z
---

# What it is

A **commitment**: reduce the gap in one property, by one means, adopted at a moment and standing
until the world answers. BDI's third letter, and the one this project ran longest without —
`bidding.pending` was an intention to observe and a bid awaiting its voucher was an intention to
acquire, both living as Python attributes that died with the process and answered to nothing.
They are rows in a graph now, each with `adoptedAt`, a resolution (`satisfied` | `dropped`) and
a `becauseOf` in both directions, because a commitment abandoned without a reason is
indistinguishable from one forgotten.

**An intention is an amortised deliberation.** Intentions exist to *save* deciding: an agent
that re-decides on every reading is a reflex machine wearing a planner's name. Here that is a
cost model rather than philosophy — deliberation is about to include an LLM call
([the decision record](/decisions/an-intention-is-an-amortised-deliberation.md)), and the
standing intention is what makes one affordable: committed means not re-consulted.

# The three means

| means | the act | adopted | resolved |
|---|---|---|---|
| `intention:Observe` | get a reading where the gap is unmeasured or stale | the bidder starts waiting on its sensor | the look comes back (satisfied) or the auction closes first (dropped, with why) |
| `intention:Acquire` | bid for what would reduce a gap | the first bid flies | the voucher arrives |
| `intention:Apply` | spend a held claim against the world | **RESERVED** — see below | |

`Observe` is first for a structural reason: at birth there is a desired state and an empty
sensed graph, so the first intention is always to look — see
[desire](/domain/desire.md) §the gap.

`Acquire` is committed to the **gap, not the round**: adopted with the first bid, absorbed for
every further bid while it stands, satisfied by the voucher. One commitment spanning several
auctions is one intention.

`Apply` is declared and unimplemented, honestly: in the spot market a [voucher](/domain/voucher.md)
is redeemed the moment it is issued, so no held claim exists for the commitment to be about. The
roadmap's **futures market** is where it becomes real — holding a voucher redeemable until `exp`
*is* this intention.

# The patience

The one piece of policy the keeper owns. Within `intention:patienceS` — each agent's own belief,
bounded by the family's constitutional floor and ceiling like a cadence — a second impulse to
adopt the same commitment is **absorbed**: `adopt` returns None and the caller treats it as its
own cooldown. Past it, a new adoption **supersedes**: the old one is resolved as dropped with
the outwaiting recorded, because honouring a dead commitment forever is as wrong as honouring it
not at all.

# Granted by a stake AND a lever

Each capability is granted by whatever fact makes it meaningful. A commitment is to reduce a
named gap by a named means, so the premise is both halves: `ag:actsFor` a subject that states
needs (else nothing to commit *about* — the supplier, all levers and no stake, keeps no ledger)
and at least one of a market position, an actuator, or a schedulable sensor (else nothing to
commit *to* — wanting without means is a wish). `world/sensing`'s agent fails the first half and
records.

# What it is not

- **Not a decider.** Nothing here chooses what to commit to; whoever acts calls `adopt` when it
  acts, and the *whether* lives in [deliberation](/domain/deliberation.md) — Reflex today, a
  model member later. Keeping and deciding share a granting premise and stay two capabilities
  because their replaceable parts differ.
- **Not public.** The ledger is a graph of the agent's own, like its beliefs and its revisions:
  an intention disclosed is strategy leaked, and the **bid is the public face** of an intention
  to acquire. The market sees what you do, never what you are trying to bring about.
- **Not a gate on the actors.** The ledger records what is done and never blocks it; what a
  standing intention absorbs is re-adoption, not the acts. Its consumers are the health series
  (`intentions_standing`, `oldest_intention_s` — a commitment growing old is an agent whose
  world stopped answering, invisible in every other series precisely because nothing is
  happening), the operator reading why an agent did what it did, and — the one it was built
  for — a [deliberator](/domain/deliberation.md) asking what already stands before deciding.
  Reflex does not ask yet; the member that will is the one that pays per decision.
