---
type: Decision
title: A contested state is leased, not bought — and only desires may be bid for
description: The sovereign's door, put beside the barrel. Water is divisible, consumed, and
  wanted in one direction; a door is none of those, so what the auction allocates stops being a
  quantity and becomes an interval of control. The bid names a state, clearing chooses between
  incompatible worlds instead of dividing a pool, and a claim's expiry turns out to be a lease's
  end. The guardrail the comparison exposes is sharper than the mechanism: a market allocates
  between DESIRES and never between a desire and a rule, or safety is for sale.
---

# A contested state is leased, not bought

Asked by the sovereign after the planner landed: an agent controls a door, in a coalition with
an agent responsible for air conditioning and one responsible for security. One wants it open,
another closed. How does the door end up open by day and closed at night? And then, seeing the
shape of it: *previously we had an auction for a shared resource, now it is also a shared door —
but different goals.*

The comparison is the useful part. A door is shared the way a barrel is shared, and almost
nothing else about it is the same.

## Three differences, and each one moves the mechanism

**Divisible against indivisible.** Two litres split three ways; a door cannot be 0.6 open. So
clearing stops dividing a pool and starts CHOOSING between incompatible allocations — which is a
different matching rule, not a different parameter.

**Consumed against persistent.** Fern's half-litre is gone once poured. A door somebody opened
stays open until somebody closes it, so the winner does not TAKE anything — it SETS something,
and the setting holds after the round is over.

**One direction against opposite ones.** Every bidder in the water market wants more water; they
differ in how much and in what they will pay. The air conditioner wants the door open and
security wants it closed. A bid can no longer be a quantity and a price: it has to name the
state it is bidding for.

## So what is scarce is TIME, and the vocabulary already exists

If the good is not consumed and only one setting can hold at once, the scarce thing is the right
to hold the door in a state FOR AN INTERVAL. That is a lease rather than a purchase.

And it lands on something built for another reason entirely. `market:redeemWindowS` and a claim's
`exp` were added so an obligation could have an honest source of urgency — a debt's heat is the
room its claim has left ([an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md)).
A door lease is a claim whose window IS the duration of control. The term was invented for a
deadline and turns out to describe a lease, which is the ordinary way a vocabulary earns its
keep.

## The door agent wants nothing, and that is a class now

The sovereign's own addition: **the door agent has no desires of its own — only obligations,
received by claims.** It holds the lever, so it hosts the venue; it acts for no subject that
states ranges, so it deduces no region and wants nothing for itself; and what it owes is
recorded because owing is granted by holding a lever others may demand.

That is exactly `world/simulation`'s city, which was broken until this morning for precisely
this reason — the ledger lived inside a capability granted by having a stake, so the one agent
whose failure to deliver would leave no evidence was the one best placed to fail
([#233](https://github.com/ShishkinDmitriy/agora/issues/233)). The door makes it a class with two
members rather than a peculiarity of the mains, which is the usual sign that a split was cut in
the right place.

## The guardrail, which is sharper than the mechanism

**If security bids for the door, safety is for sale.** A well-funded air conditioner outbids the
security agent, the building stands open at 3am, every module behaves exactly as written, and the
ledger shows a fair auction. Nothing in the market can notice, because a market's whole business
is that the highest valuation wins.

So the line is: **a market allocates between DESIRES, and never between a desire and a rule.**
*Closed at night* belongs at `sh:Violation` — no price, no round, no bidding — and the planner
already enforces it for nothing extra, because it validates each candidate world against the
legitimacy shapes and discards any plan that would reach an illegitimate one
([a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)). What the
auction is for is the genuinely contested case: two agents at the same severity, both legitimate,
neither entitled — comfort against ventilation, not comfort against safety.

This is the strongest argument the severity axis has had. It is not bookkeeping about how loud a
report should be. **It decides what may be bought.**

## Temporal wants live on the condition, not on the agent

"Open by day, closed at night" needs a want that knows the time, and the home for it is
`ssn-system:inCondition` — which this project already writes and uses degenerately, as a wrapper
around a property and two numbers. SSN's conditions exist to say *this holds under these
circumstances*, so a range that applies between 06:00 and 22:00 is native modelling rather than
an extension. The guarantee is preserved exactly: the SUBJECT states when it needs what, and no
agent authors its own ends.

The freshness want already proves the runtime half works — its horizon is computed at validation
time through `sh:sparql`, because SHACL core can only compare against a literal written into the
shape.

**But the world's legitimacy must stay time-independent even where a state's is not.** If
`agora-validate` consulted the clock, a world that passes at noon would fail at midnight and the
gate would stop being a gate. So validation holds a world to EVERY condition it states, and only
the runtime check asks what time it is.

## Contradiction, in its three kinds

- **Inside one agent** — already answered, loudly. Ranges that contradict intersect to nothing,
  no region derives, and the agent refuses to start rather than holding incoherent ends.
- **Between a desire and a rule** — not a contradiction at all, but a bound. Different severities,
  and the planner already refuses plans that cross it.
- **Between two desires** — the only genuine contest, and the market is what this architecture
  has always used for a contested scarce thing.

# Seams left open

- **Preemption is the question water cannot ask.** Once poured, a litre cannot be taken back; a
  door can be taken back mid-lease. If security's urgency spikes at 22:00 while the air
  conditioner holds a lease until 23:00, does the lease bind? That is not a market question — it
  is *when may a commitment be broken*, which is the intention machinery's own subject, and
  `patienceS` is where its opinion currently lives. A lease is a commitment that outlives the
  moment of deciding, which is what an intention is.
- **What a bid says when it names a state.** A quantity and a price are comparable across
  bidders; a state and a price are not obviously so, and two agents bidding for opposite settings
  are not bidding for "the same good in different amounts". Whether the existing valuation
  vocabulary stretches to it, or a state-bid is a different message, is undecided here.
- **Whether a lease should be visible as an obligation.** A winner holding a door is owed
  something by the host for an interval, which is the ledger's shape — but the debt is the
  CONTINUED holding of a state rather than a dose that goes out once, and nothing has been
  designed for a debt discharged continuously.
