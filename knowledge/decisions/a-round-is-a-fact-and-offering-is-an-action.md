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
`market:Acquiring`'s `ag:available` walks the plumbing — *winnings can physically reach my pot*
— and stops there: it says *I could buy*, never *I can buy now*.
[an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md) made
the consequence honest rather than removing it: the keeper's tick commits an `Acquire`, the
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
`?via market:hasRound ?r . ?r market:closesAt ?t FILTER(?t > NOW())`. The row then has the
property every other row has — *a row whose premises cannot hold does not exist* — and three
things follow without a line of policy:

- the keeper's tick commits an Acquire only when one is executable, and `bidding.take` loses
  its "no round pending" branch;
- an Acquire intention means *bid in this round*: adopted when the offer is heard (the offer
  handler runs execution, as it does today), satisfied by the claim, dropped at close — and
  between rounds the desire stays hot and nothing stands, which is the truth;
- the convening ceiling becomes visible in the trace rather than in a standing row: a plant
  that wants water and has no round reads `no candidate`, which is the finding the standing
  Acquire was hiding.

**3. Offering is an action.** `market:Offering a ag:Action ; ag:means ag:Offer`, taken by
`market:Hosting`, in the market's `actions.ttl` beside Acquiring and Serving:

- *available* where `$me market:hosts ?via`, no `market:Round` stands on `?via`, the cooldown
  since the last has elapsed (read from `$beliefs` — the host's own graph, which a rule may
  name), and the vessel holds at least the lot it would offer;
- *effect*: a `market:Round` on `?via` appears; the stock is unchanged, because an offer moves
  no water — the serve does;
- *lands* at once and is *confirmed by construction*: saying so makes it so, the first
  `ag:ByConstruction` effect shipped and the reason that route exists.

**4. The two-step is a plan, not a handler.** With 3, a host owing a round on a dry vessel
plans it: Offering's premise needs stock, Acquiring's effect raises stock, and *acquire
upstream, then offer* falls out of two nodes that never mention each other — the same way
*refill, then serve* already does for Apply (#255). `announce`'s deferral, the `deferred` dict
and the reopen-on-reading handler dissolve; the `ag:Offer` intention adopted on deferral is
simply the plan's head, standing, exactly as any other. This is also #340's answer, arrived at
from the other end: the dealer refills past its aim **because it has a round to open and cannot
open it**, not because it holds a separate want for stock. The serveability desire the issue
proposed is not derived; serveability is Offering's precondition.

# What is deliberately not decided

**What the host wants when it convenes.** A plan needs a want, and today the want is supplied
by the demand shock: a participant's `LOW` is the fact that makes a round owed, as a claim is the
fact that makes a dose owed — a want someone else sourced, in
[an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md)'s
sense. Deriving that want from the LOW verdict is the implementing change's, and so is its
**word** — this record does not name it, because a term is defined in the change that uses it.
The other three shocks are three more sources of the same want, each a later change. Whether a
host would *rather* sell — costs, a reserve, a season — remains
[strategic-supplier](/decisions/strategic-supplier.md)'s seam, untouched: this makes Offer
plannable, and a plannable act is not yet a wanted one.

**Which side holds the clock.** A bidder's `closesAt` row expires by the filter alone; a host's
round is closed by its own timer as today. A round that is a fact could be closed by a rule
on a clock of its own, which is [who-holds-the-clock](/decisions/who-holds-the-clock.md)'s
question and not this one.

# Order of work

Three changes, each a PR, in this order because each is the next one's premise:

1. the round as a belief, both sides, with `market:Round` and its four properties (#357);
2. Acquiring's availability walks it, and the bidder executes from the offer (#358);
3. Offering as an action, the LOW-sourced want, the deferral dissolved, #340 closed (#359).

# Seams left open

- **The lot is still one number.** Offering's effect offers `market:offerQuantityL` capped by
  stock, as `announce` does now. The standing-offer record's first seam is unchanged.
- **Uniform-price's uncontested round still runs as a ceremony.** A round that is a fact does
  not let the host know demand before bids are in; it only lets everyone plan around the fact
  that one is open.
- **A round wanted by nobody who can convene** — the standing-offer ceiling — is narrowed, not
  closed: a dealer can now plan its way to a round it owes, but a plant still cannot ask for
  one. The buy-side convening shock stays a decision for the day a plant sits between its band
  and its aim across many rounds, which is that record's own trigger for revisiting.
