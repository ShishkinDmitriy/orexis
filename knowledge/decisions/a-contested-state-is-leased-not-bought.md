---
type: Decision
title: A contested state is leased, not bought — and only desires may be bid for
description: >-
  The sovereign's door, put beside the barrel. Water is divisible, consumed, and wanted in one
  direction; a door is none of those, so what the auction allocates stops being a quantity and
  becomes an interval of control. The bid names a state, clearing chooses between incompatible
  worlds instead of dividing a pool, and a claim's expiry turns out to be a lease's end. The
  guardrail the comparison exposes is sharper than the mechanism: a market allocates between
  DESIRES and never between a desire and a rule, or safety is for sale.
status: accepted
timestamp: 2026-08-20T21:39:53Z
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

**And the word is load-bearing, because a lease is a distributed-systems primitive with known
edges.** Gray and Cheriton (1989) named it for exactly this shape — a time-bounded grant that
expires on its own rather than being revoked, so a holder that dies costs the system a wait
instead of a stuck resource. Two of its documented hazards apply directly and neither is closed
here:

- **A lease is only as good as the clocks agreeing.** `exp` is an absolute time on the wire, so a
  holder and the door disagreeing about now is a door held past its window or released inside it.
  Everything else here is deliberately relative for this reason — sensing's freshness follows the
  cadence, a dose's deadline is its own open-seconds plus a grace — and a lease is the one place
  that reasoning does not reach, because the *point* is an interval two parties share.
- **Renewal is where the contention actually lives.** An air conditioner that re-leases every
  three minutes has a door nobody else can win, without ever holding it illegitimately. That is
  the same shape as the convening gap and is not a market fix.

The preemption question below — whether a lease binds when security's urgency spikes mid-window
— is the third of Gray and Cheriton's, and the record's answer is unchanged: it is a
constitutional question and not a market one.

## The door agent wants nothing, and that is a class now

The sovereign's own addition: **the door agent has no desires of its own — only obligations,
received by claims.** It holds the lever, so it hosts the venue; it acts for no subject that
states ranges, so it deduces no region and wants nothing for itself; and what it owes is
recorded because owing is granted by holding a lever others may demand.

That is exactly `world/simulation`'s city, which was broken until this morning for precisely
this reason — the ledger lived inside a capability granted by having a stake, so the one agent
whose failure to deliver would leave no evidence was the one best placed to fail
([#233](https://github.com/ShishkinDmitriy/orexis/issues/233)). The door makes it a class with two
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

## Temporal wants: NOT on `ssn-system:inCondition`

A first draft of this record said the home for "open by day, closed at night" was
`ssn-system:inCondition`. The sovereign refused it, and was right twice over.

`ssn-system` is the System Capabilities module: `inCondition` exists to say *this device has this
accuracy in these ambient conditions*. Hardware, qualified by environment. This project already
stretches it once by hanging `hasOperatingRange` on a PLANT rather than on a system; hanging time
on it as well would be stretching a hardware vocabulary a second time, for a purpose it was never
about.

And it answers the wrong question. A time-conditioned range makes ONE want evaluate differently.
What was being asked is which wants EXIST at all — one root mandate, *keep everything good*,
decomposed into sub-desires whose existence depends on circumstances, with stale ones ceasing to
apply. That is a lifecycle, not a comparison.

**The asymmetry it exposes is the real finding.** A menu row exists exactly while its premise
holds: cut the pipe and the row is gone, recomputed per ask, and nothing had to notice. A desire
is derived once at genesis into `graph/constraint` and sits there until the next boot. Two
conclusions drawn from premises, treated completely differently — so a want whose premise
includes *now* is frozen at the moment the agent started.

**And the safe formulation matters more than the mechanism.** "A desire becomes outdated" is one
step from "an agent decides it no longer wants something", which is the self-satisfaction loophole
wearing a clock: an agent that can retire its own wants can be satisfied by attrition. So desires
are never RETRACTED, only RECOMPUTED. The derivation is a function of premises; when the premises
change, re-running yields a different set, and a want that no longer appears was not dropped by
anyone — it is no longer implied. Nothing decides; the world says.

Two wants already disappear this way, which is the precedent to build on rather than a new idea:
a duty lapses when its claim's window closes, and a freshness want exists only where an instrument
does. A seasonal or diurnal want is the same shape with a clock in the premise instead of a claim
or a sensor. What is missing is only that the region derivation runs once and never again — see
[#263](https://github.com/ShishkinDmitriy/orexis/issues/263).

**And the world's legitimacy must stay time-independent even where a state's is not.** If
`orexis-validate` consulted the clock, a world that passes at noon would fail at midnight and the
gate would stop being a gate. Validation holds a world to EVERY circumstance it states; only the
runtime asks what time it is.

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
