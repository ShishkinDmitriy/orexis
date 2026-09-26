---
type: Domain Concept
title: Round
term: http://example.org/orexis/market#Round
description: >-
  One allocation of a venue's lot - opened by the host for the calls on it, open for bids until it
  closes, then cleared by matching. A `market:RoundGraph` the host says to every bidder on the
  venue, and says again once cleared; a graph holding during its period, so a search standing at a
  later instant does not see it open.
---

# What it is

`market:Offering` says a round: `market:onVenue`, `market:answers` the calls it was opened for,
`market:openedAt` and `market:closesAt` the venue's bid window later. While it stands uncleared the
rules conclude the venue `market:open`, which is what a bidder's `market:Tendering` requires; its
graph's period ends at the close, so what the search may see at a future instant is the instant's to
say.

# Bids, and the clearing

A bid is a `market:BidGraph` said to the host alone: litres, `market:pricePerL`, `market:inRound`.
At the close `market:Clearing` matches the round's bids against the lot, highest price first, at
least the reserve — pay-as-bid, each winner paying what it offered — says the round again with
`market:clearedAt`, and says each winner its [claim](/domain/market/claim.md).

The round is the allocation under scarcity: a host whose stock covers every ask would need no round
to decide between them, and a claim held, unlike a round, holds at every instant.
