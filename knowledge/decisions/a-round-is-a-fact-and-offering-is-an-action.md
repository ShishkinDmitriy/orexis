---
type: Decision
title: A round is a fact, and offering is an action — so buying has a real precondition and convening can be planned
description: >-
  An open round lives in a Python dict on the host and on the wire, and nowhere in any store.
  So `market:Acquiring`'s precondition can only say "I could buy here", the keeper commits an
  Acquire that then waits for the market to knock, and a round can be opened by exactly one
  thing — a participant's LOW — because nothing can plan an Offer. Decided: a round is a
  belief on both sides, written when the offer is made or heard and retracted at close;
  Acquiring's availability walks it; Offering is an action with a precondition and an effect,
  taken by hosting; and the two-step the host hand-rolls on a dry vessel becomes a plan the
  ordinary search finds. What the host WANTS when it convenes is not decided here.
status: accepted
timestamp: 2026-08-25T18:00:00Z
---

# What is true now

Three facts, each recorded elsewhere, meet here.

**The round is an event.** `hosting.announce` publishes `{auction_id, quantity_l, reserve,
closes_in_s}` on the venue's offer topic and keeps `open_auction` in module memory; the bidder
keeps `pending` the same way. Nothing in any store says *a round is open on V until T*. So
`market:Acquiring`'s `orexis:available` walks the plumbing — *winnings can physically reach my pot*
— and stops there: it says *I could buy*, never *I can buy now*.
[an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md) made
the consequence honest rather than removing it: the patience tick commits an `Acquire`, the
actor answers "not now", and the intention stands until an offer arrives. It is the one action
whose precondition is known to be incomplete.

**Convening has one trigger.** A round opens when a participant announces `LOW` — the demand
shock — and [market](/domain/market.md) names three more (supply, budget, belief) as designed
and unbuilt. [the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md)
records the ceiling that follows: half a lot can be wanted by agents none of whom can convene,
and *the host has no stake in when to open*. `ag:Offer` is a means with no action — no
availability, no effect, no taker — adopted by hosting on a deferral (#206) and carried out by
a handler when the refill lands. The dealer's *acquire upstream, then offer* is real, and it is
hand-rolled: `announce` checks the vessel, defers, and `on_reading_recorded` reopens.

**Nothing derives serveability** (#340). The dealer's clause that bought stock up to the lot it
had promised went with the reflex, and the search cannot pursue what nobody wants: a dealer
whose aim sits below its lot stops refilling at its aim.

# What is decided

**1. A round is a belief, on both sides.** When the host announces, and when a bidder hears,
each writes into its **own** graph a `market:Round`: on which venue (`market:hasRound`, venue
to round), the lot, the reserve, and `closesAt`. Retracted when the round closes — the host on `close()`, the bidder when the claim
or the close arrives, and either side may sweep a row past its `closesAt` on the next ask.
Nothing here is disclosure: every field is already on the wire. What must **not** be written
is the host's `bidWindowS` and `roundCooldownS`, which are private beliefs precisely so that a
bidder cannot time its arrival; `closesAt` is what the offer already says.

**2. `market:Acquiring` is available only while a round is open.** One hop joins the walk:
`?via market:hasRound ?r` — or, since
[a-claim-is-water-at-a-time](/decisions/a-claim-is-water-at-a-time.md), a claim held on the
venue and not yet presented, which a host may grant on an ask with no round. The row then has the
property every other row has — *a row whose premises cannot hold does not exist* — and three
things follow without a line of policy:

- the patience tick commits an Acquire only when one is executable, and `bidding.take` loses
  its "no round pending" branch;
- an Acquire intention means *bid in this round*: adopted when the offer is heard (the offer
  handler runs execution, as it does today) or by the tick while one is open, satisfied by the
  claim, dropped at close — told by a claim, or by the clock, since a loser hears nothing — and
  between rounds the desire stays hot and nothing stands, which is the truth;
- the gate reasons from ACTIONS, not rows: a menu at genesis has no round in it, so
  `orexis-validate` refuses an action that offers rows and states no effect by reading the
  node, not the menu of the moment;
- an actor is the last boundary: a host handed an obligation's row whose vessel it knows is too low
  keeps the claim held, where the search used to keep it by planning a refill it may now have no
  round to plan into;
- the convening ceiling becomes visible in the trace rather than in a standing row: a plant
  that wants water and has no round reads `no candidate`, which is the finding the standing
  Acquire was hiding.

**3. Offering is an action.** `market:Offering a orexis:Action ; orexis:means market:Offer`, taken by
`market:Hosting`, in the market's `actions.ttl` beside Acquiring and Serving:

- *available* where `$me market:hosts ?via`, no `market:Round` stands on `?via` — held or
  imagined — the venue is not cooling (`market:coolingUntil`, a fact written
  at close into the host's own graph, so the private duration is never on a row), and the vessel
  holds *something* by the host's witness, or the host has none;
- *effect*: a `market:Round` on `?via` appears; the stock is unchanged, because an offer moves
  no water — the serve does;
- *lands* at once and is *confirmed by construction*: saying so makes it so, the first
  `ag:ByConstruction` effect shipped and the reason that route exists.

**4. The two-step is a plan, not a handler.** With 3, a host owing a round on a dry vessel
plans it: Offering's premise needs stock, Acquiring's effect raises stock, and *acquire
upstream, then offer* falls out of two nodes that never mention each other — the same way
*refill, then serve* already does for Apply (#255). `announce`'s deferral, the `deferred` dict
and the reopen-on-reading handler dissolve; the `ag:Offer` intention adopted on deferral is
simply the plan's head, standing, exactly as any other.

**What this does NOT close is #340.** The implementing change found that a partial lot is a
real round — `a-round-is-sized-by-the-vessel` sells 1.5 L from a barrel at 1.5 — so Offering's
premise is *stock > 0* and not *stock ≥ lot*, and a dealer at 1.5 L against a 2 L lot offers
1.5 L rather than refilling first. Refilling to hold a full lot is a strategy about *how* to
sell, which is the strategic-supplier seam; #340 stays open there, with the gate the issue's
second fix proposes as the cheap guard.

# What is deliberately not decided

**What the host wants when it convenes.** A plan needs a want, and today the want is supplied
by the demand shock: a participant's `LOW` is the fact that makes a round owed, as a claim is the
fact that makes a dose owed — a want someone else sourced, in
[an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md)'s
sense. The implementing change named it: a [call](/domain/call.md).
The other three shocks are three more sources of the same want, each a later change. Whether a
host would *rather* sell — costs, a reserve, a season — remains
[strategic-supplier](/decisions/strategic-supplier.md)'s seam, untouched: this makes Offer
plannable, and a plannable act is not yet a wanted one.

**Amended 2026-09-12 by [a-claim-is-water-at-a-time](/decisions/a-claim-is-water-at-a-time.md):**
the row lives in a graph of its own that holds during the round, so the door ends it for every
reader at once — a root standing hours ahead never sees it — and the sweep is hygiene for a
graph a restart left behind. The host's word still ends it first. Nothing below is false;
the backstop stopped being the only thing between a lost close and a bid into the past.

**Which side holds the clock.** ~~A bidder's `closesAt` row expires by the filter alone; a
host's round is closed by its own timer as today.~~ AMENDED by #599, and the seam turned out to
be the whole question. A fact about the venue was published at one end and DERIVED at the
other: the host declared the opening and each bidder computed the closing, privately, against
a `closesAt` it had worked out from the window with its own clock. So the host declares the
close too, on the topic that carried the offer, and a bidder's row is retracted by something
another agent DID rather than by arithmetic — which is what took `NOW()` out of the premise
above, and out of Offering's. The clock survives as the BACKSTOP, which is what it should have
been: a message can be lost and a host can die, so `closesAt` is the horizon on a belief about
another agent and `sweep_expired` is what covers silence. The general form is
[#598](https://github.com/ShishkinDmitriy/orexis/issues/598) — time is another sense, writing facts at the belief-revision seam.

**The cooldown went the same way, and the rename was the work.** `market:mayConveneAt` said
when the cooldown runs out, which is TRUE the whole time the row is written — so its presence
said nothing and every reader did the arithmetic. A row whose presence is meant to BE a fact
has to be named for the state: `market:coolingUntil`, present while the venue is cooling,
retracted by a deadline of its own landing on the loop, with the instant it carries serving as
the horizon a sweep reads when a restart leaves a row behind and no timer. So the premise asks
whether the row is there and compares nothing, and this package's rules read no clock at all —
held to it by `tests/test_clockless.py`, which names the two that are left, both sensing's.

# Order of work

Three changes, each a PR, in this order because each is the next one's premise:

1. the round as a belief, both sides, with `market:Round` and its four properties (#357);
2. Acquiring's availability walks it, and the bidder executes from the offer (#358);
3. Offering as an action, the LOW-sourced want — a [call](/domain/call.md) — and the deferral
   dissolved (#359). #340 stays open, for the reason above.

# Seams left open

- ~~**The means are still the kernel's.**~~ Closed. `Offer` left for the market with this
  record's third step; `Observe` and `Actuate` followed once their kernel holds became hooks
  (sensing satisfies the look it takes; the planner sizes a step by asking its taker,
  `Module.size`); `Acquire` and `Apply` last, once the bidder answered its own held-claim
  urgency through the `urgency` hook. The kernel's ontology kept `orexis:Means`, the class, for
  one more change — and then [the-action-is-the-kind](/decisions/the-action-is-the-kind.md)
  found nothing read it and retired the class too.
- **The lot is still one number.** Offering's effect offers `market:offerQuantityL` capped by
  stock, as `announce` does now. The standing-offer record's first seam is unchanged.
- **Uniform-price's uncontested round still runs as a ceremony.** A round that is a fact does
  not let the host know demand before bids are in; it only lets everyone plan around the fact
  that one is open.
- **A round wanted by nobody who can convene** — the standing-offer ceiling — is narrowed, not
  closed: a dealer can now plan its way to a round it owes, but a plant still cannot ask for
  one. The buy-side convening shock stays a decision for the day a plant sits between its band
  and its aim across many rounds, which is that record's own trigger for revisiting.
