---
type: Decision
title: A round is an iteration, not the auction
description: The bundle used round for two things in one file — the whole allocating process and one pass of bidding inside it — and the code has no loop, so the two coincide and the drift was invisible. A round is the iteration, which is the standard meaning in multiple-round auction design. The auction is what condenses and dissolves, and hosting is per-auction, not per-round.
status: accepted
timestamp: 2026-08-10T00:00:00Z
---

# Context

[bid-matching-is-the-word](bid-matching-is-the-word.md) settled one word and did not look at the
next one. *Round* was used for two different things, and both uses were in `domain/round.md`:

- line 10 — *"the unit the [auction] runs in"*, which makes a round the whole allocating process;
- step 4 — *"a new **deliberation round** opens because a sensed belief changed"*, which makes it
  one pass of bidding inside that process.

Those are not the same thing, and the file defining the term held both.

**The drift was invisible because the code has no loop.** `run_round` in `agent/auction.py` takes an
offer and a set of bids, matches, validates and issues — once. So an auction opens, collects once
and settles, one auction has exactly one round, and every sentence is true under either reading.
Nothing could fail. That is what made this worth writing down rather than merely fixing: a
conflation that costs nothing today is one that survives until the day it costs a lot.

# Decision — the round is the iteration

**A round is one pass of bidding inside an auction.** The auction is the process that condenses out
of scarcity, allocates a lot and dissolves; the market is the standing structure both happen
inside. Three words, three referents:

| | what it is | built? |
|---|---|---|
| [market](/domain/market.md) | the standing structure | yes |
| [auction](/domain/auction.md) | the process that allocates one lot | yes |
| [round](/domain/round.md) | one iteration of bidding within it | **no** — exactly one, single-pass |

## Because that is what the word means everywhere else

The canonical multi-unit design is named for it: the **simultaneous multiple-round auction**, used
for spectrum, where one auction over one set of lots runs many rounds, each a pass of bidding with
results published between them. Clock auctions are counted in rounds the same way. Under the
rejected reading the format's name would be a contradiction.

Splitting a large quantity into smaller pieces does not produce rounds either — it produces
**lots**, each allocated by its own auction. Here one auction sells the host's lot whole, so that
axis is unused; see
[the-lot-is-the-hosts-standing-offer](the-lot-is-the-hosts-standing-offer.md).

## Which makes hosting per-auction

The seam in [bid-matching-is-a-capability](bid-matching-is-a-capability.md) read *"hosting a market
is structural, hosting an auction is **per-round**"*, and
[a-role-needs-something-to-be-a-role-in](a-role-needs-something-to-be-a-role-in.md) quoted it.
Corrected in both, to *owning the venue is structural, convening an auction is per-auction* — which
also removes the circularity that a literal find-and-replace would have left behind.

The distinction being drawn was always *who convenes this allocation event* against *who owns the
venue*, and that is the auction. Saying per-round only parsed while round and auction were the same
thing — which is exactly the identity this record refuses to lean on. Nothing about either argument
changes; both were about the auction and said round.

# Consequences

- **`domain/round.md` states one meaning and marks the boundary.** Steps 1–3 are the round that
  runs; step 4 onward is designed and unbuilt, and step 4 is the only thing that makes *round* mean
  anything distinct from *auction*. A page describing an unbuilt loop as though it ran is how the
  two meanings stayed comfortable together.
- **The third word now earns its keep.** Before this, *round* and *auction* named one built thing,
  while *round* was simultaneously reserved for an iteration that does not exist. That is two words
  for one referent and one word for two — the same shape as *matching / rule / format*, found the
  same way and worth the same fix.
- **A vocabulary pass covers a vocabulary, not a term.** The matching pass corrected every use of
  three words and did not ask what else in the same paragraphs was ambiguous. *Round* was one
  sentence away throughout and went unexamined.

# What the identifier turned out to be on

The seam this record opened said the identifier and the claim claim were both misnamed. Closing
it found the surface wider than the seam described: **the identifier is on four payloads, not
one** — the offer, the bid, the claim, and the signed command. They rename together or not at
all, because a bidder echoing a key the host no longer reads is a bid silently dropped, and
silence is the failure mode this project keeps rediscovering.

**The fourth is why it was worth doing before iteration exists.** `round_id` sits inside
`signing.canonical(payload)`, so the key name is part of what `match_sig` and `val_sig` cover.
Renaming it later is a change to a *signed artifact* across signer, validator and redeemer.

Two facts made it cheap today, and neither would have survived:

- **`verify_command` rebuilds the canonical form from whatever keys arrive**, rather than from a
  fixed list — so a device verifies a renamed payload without knowing anything changed. That is a
  property of how it was written, not a guarantee anyone stated.
- **Nothing persists a claim.** `ActuationModule.settled` and the simulated valve's `spent` are
  both in-memory sets, so no durable artifact carries the old key across a restart. Claims are
  spot — redeemed on win, `exp` ≈ now.

`run_round` became `run_auction` and `RoundResult` became `AuctionResult` with it: what that
function does — propose, validate, issue — is the auction's shape, which is precisely what
[auction](/domain/auction.md) says `agent/auction.py` kept when it lost the allocation.

## One consequence, and one term deliberately left

**A world must be restarted whole.** An old bidder echoing `round_id` to a new host would have its
bid dropped as belonging to no open auction. Nothing warns, because a bid for an unknown auction
is exactly what a late bid looks like.

**`market:roundCooldownS` is untouched**, and it is the one name here that is genuinely about
auctions rather than bidding passes. It stayed because it is a *persisted belief*, stated in each
supplier's beliefs file and therefore living in a volume — renaming one is the hazard
[#87](https://github.com/ShishkinDmitriy/orexis/issues/87) exists to make safe, and arming that
trap to fix a name would have been the wrong order. It should be `auctionCooldownS` once a volume
can survive a rename.

# Seams left open

- ~~**`round_id` names an auction.**~~ **Closed** — see *What the identifier turned out to be on*
  above. It is `auction_id` now, on all four payloads at once.
- **Iteration is not designed, only named.** What a bidder sees between rounds, what may be
  re-bid, and what stops the loop other than the wallet are open. `domain/round.md` describes a
  shape; nothing here commits to it.
- **Nothing enforces the vocabulary**, which the previous record already recorded and which this
  one is the evidence for.
