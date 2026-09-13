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
  supply on them. A plant asks for a dose at an instant, and a host opens a round only where
  the asks exceed its supply. Refused — placing a bid by subtraction from a deadline, a claim as
  immediate water, the backward walk over preconditions #620 sketched, and a round row that
  outlives its period unswept.
---

# The claim

**A round is a graph holding during its period.** Written on the offer into a graph of its own
per round, classified as the agent's, with `dcterms:temporal` from the offer to `closesAt` in
the periods table
([a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md)). The row's
presence within its period is the openness, exactly as
[a-round-is-a-fact-and-offering-is-an-action](/decisions/a-round-is-a-fact-and-offering-is-an-action.md)
said of the row alone, and no rule asks the clock: the door hands the round to a reader asking
about an instant inside the period and to nobody asking about one past it. A search rooted at
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
([#626](https://github.com/ShishkinDmitriy/orexis/issues/626)).

**A plant asks ahead, and a round is the allocation under scarcity.** A want derived from a
predicted crossing is a request for a dose at an instant, announced as LOW is announced today;
a host that can serve the asks from stock within their windows issues claims without a round,
and opens one only where the asks for a window exceed what it will hold then
([#627](https://github.com/ShishkinDmitriy/orexis/issues/627)).

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

# What the build touched

The round's writer and readers, and one door. `rounds.open_round` writes the graph, its
classification and its period; `close_round` drops all three; `rounds_of` asks at an instant;
the market's rule texts read `market:hasRound` from the default graph rather than from the
beliefs graph they used to name, so the door decides. A rule's SELECT reads as its CONSTRUCT
always has — public knowledge and the agent's own — and the store gained that door for selects
(`Store.query_at`, with the instant), which the afforder and the urgency choir now take with
the instant a node stands at. One defect found beside it: a tender bid into the first open
round the store listed, and with a claim that named no round the old one still stood; it bids
into the round closing last, the newest offer.

# Seams left open

- **The pour the bidder subtracts** is Acquiring's landing for the litres it bid, less the
  venue's window — the host's valve as the rule states it; a host whose valve differs from
  the rule's serves late by the difference, and the keeper's verdict says so.
- **A plant's own request.** Whether a foreseen crossing should announce at derivation or at
  some fraction of its room is the bidder's threshold reading the derived want's time room;
  #627 leaves the threshold to the package.
- **The host's rounds are its own word.** The host's row for its round arrives `Recorded` and a
  bidder's `Received`; nothing reads the difference yet.
