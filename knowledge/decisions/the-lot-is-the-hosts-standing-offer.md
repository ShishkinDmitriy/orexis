---
type: Decision
title: The lot is the host's standing offer, and the threshold that opens a round is not the one that makes a bid
description: A round is triggered by a band crossing and sized by a fixed host belief, so its size has nothing to do with what anyone needs. Why the host is deliberately blind to quantity before a round, what the two-threshold split costs — measured at half the lot in demand that can never convene one — and what an iterative auction would buy.
tags: [market, auction, lot, demand, thresholds, privacy, seams]
timestamp: 2026-08-07T00:00:00Z
---

# What actually happens

Three steps, and the quantity appears in none of the first two.

1. An agent records a reading and announces a **band** on its event topic — `LOW`, `OK` or
   `HIGH`. A verdict, never a demand. The host works fine with no `value` in the payload at
   all, which a test pins.
2. The host hears `LOW`, checks its cooldown, and announces a round for
   `ag:offerQuantityL` at `ag:reservePricePerL`. Both are its own standing beliefs. Nothing
   about the trigger enters the offer except the log line naming who it was.
3. Only now does anyone state a quantity, in a **sealed bid** computed from a deficit no one
   else can see.

So the first agent in trouble picks the **moment**, not the **size**. It never says "I need
1 litre" and there is nowhere in the protocol for it to.

# Why the lot is not sized from demand

Because the host cannot know demand before the round, and that is the design rather than an
omission.

The whole point of one process per agent is that a bid is a function of a *private* valuation:
what an agent wants, and how badly, is the thing no peer can compute. Sizing a lot from demand
means asking "how much do you want?" before the auction — and that answer *is* the valuation.
Asking it is the round.

What the host hears instead is a verdict. `LOW` is disclosure an agent chooses to make about
its own state, in a form that reveals a threshold rather than a number. A host that could size
its offer from demand would be a host that had already been told what it is supposed to
discover.

# Why the trigger is not the bid

Two different numbers do two different jobs, and nothing said so until now:

| | fern | tomato | succulent |
|---|---|---|---|
| `ag:bandLow` — what opens a round | 0.35 | 0.30 | 0.12 |
| `ag:hasTarget` — what makes a bid | 0.55 | 0.50 | 0.22 |

A bid is computed from `target - moisture`; the announcement is computed from `bandLow`. An
agent between the two is below its target, will bid if a round opens, and **cannot open one**.

That is defensible: convening a round is expensive — a message to everyone, a bid window, a
clearing round trip — and doing it because one plant is mildly below target would spend the
society's attention on nothing. Trouble is the right trigger. The trap is that it was never
written down, so it reads as an oversight, and the two thresholds can drift apart in a beliefs
file with nothing to notice.

## What the gap costs, in this world

With `ag:litresPerFraction 2.0` for all three, the demand that exists between `bandLow` and
`hasTarget` is:

```
fern       (0.55 - 0.35) x 2.0 = 0.4 L
tomato     (0.50 - 0.30) x 2.0 = 0.4 L
succulent  (0.22 - 0.12) x 2.0 = 0.2 L
                                 -----
                                 1.0 L   against a 2.0 L lot
```

**Half the lot can be wanted by agents none of whom can ask for it.** It is served only when
someone else crosses into trouble first, and if nobody does, it is not served at all.

Worth putting beside it: total demand with all three pots at zero is
`1.1 + 1.0 + 0.44 = 2.54 L` against the same 2.0 L. So the auction barely binds even in the
extreme — this society is close to never actually scarce, which is a strange property for one
built to study scarcity.

# The uncontested round is still priced as if contested

`ag:PayAsBid` — the rule this society runs, in `capabilities/matching/` — is greedy and
discriminatory: eligible bids sorted by price, filled highest first, each paying its own bid.
When total demand comes in under the lot there is no rival for anything, and every bidder still
pays what it offered — so an agent is charged for its own urgency in a round where nothing was
scarce.

The rule is now one member of a family rather than the only thing there is, so *"pay-as-bid
versus uniform price is a separate argument"* has somewhere to happen — see
[matching-is-a-capability](matching-is-a-capability.md). That does not fix the
gap below, which is a defect **in** pay-as-bid rather than a reason to prefer another rule.

[market](../domain/market.md) says the supplier should simply **dispense** in that case. Nothing
implements it, and nothing can implement it *before* a round, for the reason above: demand is
unknown until bids are in. It could be implemented *after* — the bids are in hand and the total
is known at `close()`. That is a real and closable gap, filed as [#50](https://github.com/ShishkinDmitriy/agora/issues/50) rather than argued here.

# What an iterative auction would buy, and cost

An ascending clock — the host names a price, bidders answer with a quantity, the price rises
until demand meets supply — would let the lot be *discovered* instead of declared. The domain
already has the machinery: `ag:litresPerFraction` converts a deficit into litres, so a bidder
can answer a price with a quantity honestly at every tick.

Three costs, and the third is the one that matters:

- **Latency.** A round becomes several exchanges. Boards sleep between readings and the link
  here runs at −80 dBm; `ag:bidWindowS` multiplies by the number of ticks.
- **More state.** The host holds an open round across rounds of messages, and every failure
  mode of a partially-completed auction becomes real.
- **It changes what is private.** A sealed bid discloses a valuation to nobody. An ascending
  auction discloses a *demand curve* to everyone watching the topic — one point per tick. That
  is a larger disclosure than this project has anywhere else, and it would be made to peers
  rather than to a host. Trading privacy for allocative efficiency is a legitimate choice; making
  it by accident, while reaching for a better lot size, is not.

# Seams left open

- **The lot is one number for every round.** It does not vary with the season, the tank level,
  or how many agents are plumbed in. `ag:capacityL` is the physical ceiling and is checked by
  clearing, but nothing connects it to what is offered.
- **Nothing ties `bandLow` to `hasTarget`.** A beliefs file can state a `bandLow` above its
  target, which would make an agent announce trouble it will not bid on. No shape forbids it,
  because it is not obviously wrong — an agent may want to be told about a state it does not
  intend to act on.
- **The host has no stake in when to open.** It reacts to other agents' verdicts and holds no
  view of its own about whether now is a good time to sell, which
  [strategic-supplier](/decisions/strategic-supplier.md) says it otherwise is.

# When to revisit

**The first round where an agent that wanted water never got a chance to ask** — visible as a
plant sitting between its band and its target across many rounds while others are served. That
is the symptom the arithmetic above predicts, and seeing it once turns this from a design note
into a thing to fix.
