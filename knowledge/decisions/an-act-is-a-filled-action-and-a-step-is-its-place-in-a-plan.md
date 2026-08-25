---
type: Decision
title: An act is a filled action with a window, and a step is its place in a plan
description: >-
  An action is a template. What gets committed, taken and promised is a filled one — lever,
  want, quantity, whom for, and when — and it had no name: an affordance row carried
  three of those, an intention three, a commitment two, and the timing lived in actors'
  timers. Decided: that thing is an ACT, execution's word, with a window (not before, not
  after); a STEP is planning's word for an act at its place in a plan with what the search
  predicted; an intention commits to an act; a commitment promises one; a claim is a
  commitment to the host's Serving act for so many litres, not after its expiry.
status: accepted
timestamp: 2026-08-26T18:00:00Z
---

# What was true before

[the-action-is-the-kind](/decisions/the-action-is-the-kind.md) left `ag:Action` as the one
kernel word for acting, and it is a template: a precondition, an effect, a taker. The filled
version existed in four places and was named in none. An [affordance](/domain/affordance.md)
row is action + lever + want, unsized. The planner's `_Node.taken` is a tuple of rows plus
the sizing it asked the taker for. An [intention](/domain/intention.md) records action, lever
and want (`ag:by`, `ag:through`, `ag:pursues`) and not the size. A
[commitment](/domain/commitment.md) records how much of what for whom until when, and no
action at all. And every *when* an act carries — the bidder's give-up timer at the round's
close, the host's redeem window, the keeper's expectation deadline — is a clock some module
keeps by hand.

The sovereign asked: an action is a template, so what is the filled one, and is a claim not a
commitment to execute an action with parameters?

# What is decided

**An act is a filled action, and it is execution's word.** Action, lever, the want it serves
and what that is about, quantity, whom for, and a **window** — not before, not after. What an intention commits to (`ag:by`
names the act; the action is reachable through it), what an actor is handed (`take(act, …)`),
what a [commitment](/domain/commitment.md) promises (`Commitment.act`). A
[claim](/domain/claim.md) is therefore exactly what the sovereign said: a commitment to the
host's `Serving` act — this valve, this pot, so many litres — not after `exp`. A self-dose is
a commitment to a `Dosing` act with nobody to pay. See [act](/domain/act.md).

**A step is planning's word.** An act at its place in a plan, with what the search predicted
it would reach. `Plan.steps` holds steps; the trace's `ag:Candidate` is a weighed step; only
the head's act is ever committed. See [step](/domain/step.md). The two words keep the two
scopes apart: a step is a hypothesis that must not outlive its pass, an act is what survives
it.

**The window is the act's, not the actor's.** Not-after is what every hand-kept timer was
saying: a bid not after `closesAt`, a serve not after `exp`, a look not after the round that
wanted it closes. Not-before is the half nothing uses yet — it is where a held claim spent
later arrives, which is the futures seam in [claim](/domain/claim.md) stated as a field
rather than as a roadmap item.

# Order of work

1. `ag:Act` and the kernel dataclass; an affordance row becomes an act when the search sizes
   it; `Plan.steps` hold steps whose acts are those; `take(act, …)` (#369, landed — `agent/act.py`,
   the row sized into an act in `Planner._step_from`, `execution.carry_out(agent, act, …)`).
2. An intention commits to an act — `ag:by` names the act node, which `ag:fills` the action
   and carries lever, quantity and window; the ledger's `ag:through` became the act's; old
   ledgers migrate at the keeper's construction (#370, landed — `Standing.act`, and the
   sovereign asking the intentions modality sees the quantity and the window on the act).
3. A commitment promises an act; `Claim` carries the host's Serving act; `exp` is the act's
   not-after; the actors' hand-kept timers read the window instead (#371).

**Written after the record, and worth saying:** this record was merged as #372 and then lost
from `main` in a history rewrite; it was recovered from the orphaned commit with #369, and
its "property" became "want" on the way, since
[the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md) had landed between.

# Seams left open

- **Not-before has no writer.** The field exists once #371 lands; the first thing to write it
  is futures, which is a market decision.
- **A step's predicted world is trace only.** `ag:wouldReach` on a candidate is a number; the
  world itself is dropped with the imaginarium, by design.
