---
type: Process
title: Round
term: http://example.org/orexis/market#Round
description: One iteration of bidding inside an auction — not the auction itself. The auction is the process that allocates a lot; a round is a pass of bidding within it. Exactly one is built, so today an auction has a single round and the two coincide; the iterative flow described here is designed and unbuilt. The word is the standard one from multiple-round auctions.
---

# What it is

A **round** is **one iteration of bidding inside an [auction](/domain/auction.md)** — bids in, a
provisional picture out, and the chance to bid again. It is not the auction and not the
[market](/domain/market.md):

| | what it is |
|---|---|
| [market](/domain/market.md) | the standing structure — a resource, who supplies it, who consumes it, the channels |
| [auction](/domain/auction.md) | the process that allocates one lot: it condenses, allocates, dissolves |
| **round** | one pass of bidding inside that process |

**Exactly one round is built.** `run_auction` in `packages/capability/market/auction.py` takes an offer and a set of bids
and returns a proposed trade — there is no loop, so an auction opens, collects once, matches, and
settles. Today an auction therefore has a single round and the two coincide exactly. Everything
below step 3 is the designed shape and not the running one.

That coincidence is why this page said, for a long time, that a round was *"the unit the auction
runs in"* — and then used the word the other way four lines later (*"a new deliberation round
opens"*). See
[a-round-is-an-iteration-not-the-auction](/decisions/a-round-is-an-iteration-not-the-auction.md).

# It is a fact, on both sides

Since [a-round-is-a-fact-and-offering-is-an-action](/decisions/a-round-is-a-fact-and-offering-is-an-action.md)
an open round is a `market:Round` in the belief base of whoever announced or heard it — the
venue it is on (`market:hasRound`), its lot, its reserve, and `market:closesAt` — retracted when
it is over for that agent and swept once past its close. It carries what the offer said and
nothing the offer did not: the host's window and cooldown stay its own. `market/rounds.py` is
the one writer, and the sovereign may ask a running agent whether a round is open.

# The word is the standard one

In iterative auction design a round is the iteration — the **simultaneous multiple-round
auction** used for spectrum is named for it, and clock auctions are counted the same way.

Splitting a large quantity into smaller pieces does not produce rounds; it produces **[lots](/domain/lot.md)**,
each allocated by an auction of its own. Here the lot is the host's standing offer and one
auction sells it whole — see
[the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md), and
[a-round-is-an-iteration-not-the-auction](/decisions/a-round-is-an-iteration-not-the-auction.md)
for why the two had to be told apart.

# Flow

The auction is convened by the **host** — by design the scarce side, though nothing derives that
and every shipped world states `market:hosts` on the supplier (see
[auction](/domain/auction.md), *who convenes it*).

1. **The auction condenses** — excess demand crosses above zero (a demand, supply, budget or
   belief shock — see [market](/domain/market.md)) and the host convenes. Deterministic, no LLM.
   It announces the lot, the reserve, the deadline and how it will match.
2. **Deterministic bids form** — each agent's value model produces an honest number from its own
   **sensed** moisture and target. An above-target plant bids nothing and cedes, as a reflex.
3. **Proposals and English justification** — the LLM step: at most one call per deliberating agent,
   phrasing a stance that **may cite** its sensed facts (voluntary disclosure). Provisional clear.

*Steps 1–3 are one round, and today the only one. What follows is designed and unbuilt.*

4. **A further round opens** — a shock lands (a rain forecast is recorded, a sensed belief
   changes), private value curves diverge, and agents re-bid against the partial allocation they
   can now see. This is why conversation earns its place over a one-shot auction, and it is the
   only step that makes *round* mean anything distinct from *auction*.
5. **Rounds stop and the host proposes the match** — bounded so the auction always terminates,
   primarily because deliberation costs, so bidding ends endogenously when agents can no longer
   afford to think (see [wallet](/domain/wallet.md)); a hard ceiling on rounds exists only as a
   safety backstop. The host then selects the trade from the signed bids and signs it, by whichever
   [bid matching](/domain/bid-matching.md) it announced when the auction opened.
6. **Validate and settle** — [clearing](/domain/clearing.md) checks the proposed trade
   (conservation, solvency, identity, [constitution](/domain/constitution.md),
   order-consistency) and **co-signs** the [claim](/domain/claim.md); then wallets are debited
   (water and metabolic cost) and the [supplier](/domain/supplier.md)'s
   [executor](/domain/executor.md) arm actuates the fully-signed claim, sequencing the pump.
   See [clearing-as-validator](/decisions/clearing-as-validator.md).

Steps 5 and 6 belong to the auction rather than to any one round: the match is made once, over the
bids standing when bidding stopped.

# Why iterative

Conversation only pays off with private information, shared shocks that shift valuations, and
temporal coupling — watering has all three. A sealed one-shot auction would make the conversation
redundant, which is what the single-pass path is today.

# Legibility

The transcript IS the explanation ("Fern got only 1 L because rain was forecast and it ceded to
Tomato's afternoon need"). A single optimizer can't hand you that sentence — and it is a transcript
*of rounds*, which is the other reason the iteration deserves its own word.

# What `auction_id` names

`auction_id` is minted once per auction and travels on all four payloads — the offer, the bid, the
[claim](/domain/claim.md) and the signed command. It names the auction, which is what it always
was, and the [claim](/domain/claim.md)'s replay check is keyed on it because a claim is won
once per auction rather than once per bidding pass.

The one name still spelled the old way is `market:roundCooldownS`, deliberately: it is a persisted
belief, and renaming one is what [#87](https://github.com/ShishkinDmitriy/orexis/issues/87) exists
to make safe. See
[a-round-is-an-iteration-not-the-auction](/decisions/a-round-is-an-iteration-not-the-auction.md).
