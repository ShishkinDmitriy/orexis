---
type: Decision
title: A claim is water at a time, and a round is a graph holding during its period
status: accepted
timestamp: 2026-09-12T20:00:00Z
description: >-
  The sovereign's ruling of 2026-09-12 on what a market plant does with a foreseen crossing,
  after #620's measurement showed a bid placed by subtraction landing in a round that had
  closed. Four claims. A round is a graph holding during its period, so a search standing at a
  future instant never sees a round that will have closed — built. A winner receives a CLAIM
  with the time it can be used, not water, so the presenting is what is placed at the instant
  and never the bid — built. The host turns the claims it issued into predicted arrivals and plans its
  supply on them — built. A plant asks for a dose at an instant, and a host opens a round only where
  the asks exceed its supply — built. Refused — placing a bid by subtraction from a deadline, a
  claim as immediate water, the backward walk over preconditions #620 sketched, a round row that
  outlives its period unswept, and buying made available by a want's instant alone.
---

# The claim

**A round is a graph holding during its period.** Written on the offer into a graph of its own
per round, classified as the agent's, with `dcterms:temporal` from the offer to `closesAt` in
the periods table
([a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md)). The row's
presence within its period is the openness, exactly as
[a-round-is-a-fact-and-offering-is-an-action](/decisions/a-round-is-a-fact-and-offering-is-an-action.md)
said of the row alone, and no rule asks the clock: a reader asking about an instant inside the
period is handed the round, and one asking about an instant past it is not. A search rooted at
a predicted crossing (#619) therefore never plans a bid into a round that will have closed. The
host's word still ends it (`close_round` drops the graph); the sweep drops what outlived its
period. This is the retrofit the period record deferred until measured, and the measurement is
the second row of the table below.

**A winner receives a claim with the time it can be used, not water.** The bid says when the
water is wanted; the claim says from when it can be used; the water is served when the claim is
presented. So an agent may win now and use it in four hours, and what an instant-bound want
places at the instant is the PRESENTING of a claim, never the bid — the bid is taken while a
round is open, which is now or not at all
([#625](https://github.com/ShishkinDmitriy/orexis/issues/625), built). On the wire the bid
carries `wanted_at`, the instant the bidder intends to present — the want's instant less the
pour the host's valve takes, read off Acquiring's own landing — and the claim comes back with
`usable_from` and `usable_until`, the venue's window running from the wanted instant; the
claim fact carries them as `market:usableFrom` and `market:usableUntil`. The Presenting step
is placed by the action itself, `orexis:readyAt` reading the claim's usable instant, and the
keeper holds it on the scheduler until then and asks its `readyWhen` only after; the host
refuses a presentation before the window opens and the claim stands. And the search for an
instant-bound want stands at the latest start first and, finding nothing on that menu, at the
present — where the round is — and a plan is placed at the instant of the root it was found
from, never by subtraction: found from the present, it is taken now.

**The host predicts the arrivals it promised.** A claim it issued with a usable window is an
arrival expected inside that window — an occurrence, a fact ABOUT a window stated inside a graph
whose own period says how long it is worth believing — and its supply want reads those as
demand, so the refill upstream is planned ahead of the presenting
([#626](https://github.com/ShishkinDmitriy/orexis/issues/626), built). The prediction was
already there: every claim the host issues is a debt in its ledger, and `market:owedFrom`
carries the claim's usable instant onto it. The market package's drift, `market:Draining`,
reads the ledger where the water package reads a rate — the level at a future instant is what
the vessel holds less what it owes to holders whose windows have opened by then, a discharged
debt not owed — and its crossing is the first window at which the litres owed take the level
under the floor, stated as an instant. So the host's stock root foresees exactly as a plant's
does: three litres held, one and a half owed in an hour and one more in two, the crossing is
the second window, and foreseeing six hours the host plans Acquiring from the city from the
present, where the round is, with nothing presented yet.

**A plant asks ahead, and a round is the allocation under scarcity.** A want derived from a
predicted crossing is a request for a dose at an instant, announced where LOW is announced
today: the reading after the crossing is foreseen carries the ask out on the event topic —
the litres a bid would be sized to, wanted at the want's instant less the pour — once per want
and instant ([#627](https://github.com/ShishkinDmitriy/orexis/issues/627), built). The ask is
not a step: nothing is searched for it, and the plan follows the answer. A host whose stock
covers the ask at that instant — what it holds, less what it already owes to holders whose
windows open by then, less the ask, still inside its vessel's region — grants a claim with no
round, usable from the instant asked for, and owes it in its ledger with the window, so the
grant is an arrival its drift reads like any other; a host whose stock does not convenes a
round, exactly as a LOW convenes one, and the round is the allocation under scarcity. On the
plant's side a claim held and not yet presented is what makes buying available and the
tender done: the search finds Acquiring from the latest start, since a claim, unlike a round,
holds at every instant, and the plan is placed there; at its instant the tender is taken with
nothing to bid, and the presenting is placed at the claim's window. Three litres held, half a
litre asked for in three hours: granted. One and a half asked for in an hour, granted, then one
more in two: by then the barrel holds one and a half, less one is half, under its floor of one —
a round.

# What was measured, and what it refused

The simulation plant at 0.47, drying at 0.12 a day, crosses its floor in four hours and,
foreseeing six, derives the instant-bound want. Three passes, before the round had a period:

| round open now | the pass's root | result |
|---|---|---|
| none | projected to the crossing less Acquiring's 900 s | nothing on the menu — a purchase cannot be foreseen, only reacted to |
| for 60 s | projected, 3.75 h out | Acquiring, PLACED 3.75 h out, in a round closing in 60 s — the row had no period and a future root still saw it |
| for 60 s | now | Acquiring now, the water in 900 s, met at the instant — the honest plan |

- **A bid placed by subtraction from the deadline** is the second row: refused. A step's instant
  is the instant of the root the plan was found from, and the bid's is the round's.
- **A claim as immediate water** is what made the second row look right: refused, by the ruling.
- **The backward walk over preconditions** [#620](https://github.com/ShishkinDmitriy/orexis/issues/620)
  sketched: refused as the mechanism. The market's method already chains bid then present; what
  fixes the bid's instant is the round's period, and what fixes the presenting's is the claim's
  window. Neither is a search.
- **A round row outliving its period** unswept until an offer or a tick: refused. The door ends
  it for every reader at once; the sweep is hygiene for a graph a restart left behind.
- **Buying made available by a want's instant alone** — the first shape of #627, Acquiring on
  the menu wherever the want is met AT an instant, the ask answered while the tender waits:
  refused on running it. A pass standing at the latest start found Acquiring there and placed
  the whole plan hours out — past the round a host that could not cover the ask convenes now,
  which the placed tender would never have bid in. What makes buying available is a fact that
  holds at the instant the search stands at: a round's period, or a claim held.

# What the build touched

The round's writer and readers, and one door. `rounds.open_round` writes the graph, its
classification and its period; `close_round` drops all three; `rounds_of` asks at an instant;
the market's rule texts read `market:hasRound` from the default graph rather than from the
beliefs graph they used to name, so the reader's list decides. A rule's SELECT reads as its CONSTRUCT
always has — public knowledge and the agent's own — handed the same graphs, of the kinds a
rule reads at the instant a node stands at, which the afforder and the urgency choir now build
per node. One defect found beside it: a tender bid into the first open
round the store listed, and with a claim that named no round the old one still stood; it bids
into the round closing last, the newest offer.

The ask road touched the two market modules and one action. The bidder asks on the reading
recorded, through the event topic sensing announces on, and wakes the mind when a claim
arrives with no tender standing; the host routes an event carrying `asks` and `wanted_at` to
its grant-or-convene, where covering is one query over its ledger and the region its stock
want states; Acquiring is available on a claim held, Tendering is done by a claim held and
unpresented whenever it was claimed — beside the claim cleared since the step was adopted,
which a host with no redeem channel writes as presented on arrival and which stays the
only kind that counts — and the tender taken with such a claim in hand bids nothing. A claim
whose window closed unpresented is a graph past its period (#645) — handed to nobody and
dropped by the one sweep — or every later tender would be done by it. And one line in the keeper: a plan standing at its LAST step and waiting —
held until the watch is live, or placed at the claim's window — is in progress and not
re-decided. It was not, since #510 counted only a step still to come, and that was harmless
while the round's close left nothing on the menu; with the claim held the pass found buying
available on the very claim the standing plan was about to present, and adopted it twice.

# Seams left open

- **The pour the bidder subtracts** is Acquiring's landing for the litres it bid, less the
  venue's window — the host's valve as the rule states it; a host whose valve differs from
  the rule's serves late by the difference, and the keeper's verdict says so.
- **The ask goes out on the reading after the crossing is foreseen**, one cadence after the
  pass that derived the want, because the bidder announces where it reads and the pass runs
  after the announcing. An ask at derivation would need the mind to say downward that a want
  was derived, a point the choir does not have.
- **A crossing that moves asks again.** The ask is once per want and instant; a child derived
  at a later instant is a new ask, and the earlier grant stands as a debt until its window
  closes. The host does not net the two, and a plant may hold two claims for one need.
- **The host's rounds are its own word.** The host's row for its round arrives `Recorded` and a
  bidder's `Received`; nothing reads the difference yet.
