---
type: Process
title: Auction
description: >-
  How a scarce good changes hands on a venue - six actions, split between the bidders and the
  host, each saying a document the other side believes and the rules read. Calling, Offering,
  Tendering, Clearing, Presenting, Serving. Nobody runs it; each agent plans its own part for its
  own desires, and the protocol is what their plans come to.
---

# The six actions

| action | who | says | the rules then conclude |
|---|---|---|---|
| `market:Calling` | a bidder in trouble | a [call](/domain/market/call.md) on the venue | the host has a call to answer |
| `market:Offering` | the host | a [round](/domain/market/round.md), open until it closes | the venue is `market:open`; the call is `market:offered` |
| `market:Tendering` | each bidder | a bid: litres at a price per litre | — |
| `market:Clearing` | the host, at the round's close | the round again, cleared, and a [claim](/domain/market/claim.md) to each winner | the call is `market:answered`; a winner `market:holdsClaimOn` the venue |
| `market:Presenting` | a holder whose reading is below its range | a presentation of its claim | the claim is `market:presented` |
| `market:Serving` | the host | the claim again, discharged — and a command to its valve | the holder's claim is discharged |

# Why nobody runs it

Each side is only searching for its own desires. A grower wants its soil inside its range; the
cheapest plan it finds is to call, tender and present, since it holds no water. The
[host](/domain/market/host.md) wants no call unanswered and no presented claim unserved; its plans are
to offer, clear and serve. The documents are the only contact between them, and each plan waits on
the other's documents as it would on a reading.

# What is left open

Pay-as-bid is the one matching built: a winner pays what it bid. Uniform price, an iterative
auction of several rounds and a wallet that makes a bid mean something are designed and unbuilt.
