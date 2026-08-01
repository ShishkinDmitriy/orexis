---
type: Domain Concept
title: Auction round
description: The bounded iterative round — open, propose, react to shocks, clear.
tags: [auction, protocol, contract-net]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

The unit of coordination, run by the trusted core (v1). Iterative-ascending so that
conversation and auction genuinely interleave: agents see the partial allocation, converse,
and re-bid. Bounded so it always terminates — primarily because deliberation costs, so rounds
end endogenously when agents can no longer afford to think (see
[wallet](/domain/wallet.md)); a hard max-round ceiling exists only as a safety
backstop, not the primary terminator.

# Flow

1. **Situation opens** — the auction condenses out of scarcity: excess demand crosses above
   zero (a demand/supply/budget/belief shock — see [market](/domain/market.md)), and the
   scarce-side host (v1 the [supplier](/domain/supplier.md)) convenes. Deterministic, no LLM.
2. **Deterministic bids form** — each agent's value model produces an honest number from its
   own attested moisture + target. An above-target plant bids nothing and cedes (a reflex).
3. **Proposals + English justification** — the LLM step: at most one call per deliberating
   agent, phrasing a stance that must cite attested triples. Provisional clear.
4. **Shocks land** — e.g. a rain forecast is attested; a new deliberation round opens because
   an attested belief changed; private value curves diverge and agents re-bid. This is why
   conversation earns its place over a one-shot auction.
5. **Host proposes the match** — the scarce side (in v1 the [supplier](/domain/supplier.md))
   selects the trade from the signed bids and signs it.
6. **Validate + settle** — [clearing](/domain/clearing.md) checks the proposed trade
   (conservation, solvency, identity, [constitution](/domain/constitution.md),
   order-consistency) and **co-signs** it; then debits wallets (water + metabolic cost) and
   the [executor](/domain/executor.md) actuates the fully-signed token, sequencing the pump.
   See [clearing-as-validator](/decisions/clearing-as-validator.md).

# Why iterative

Conversation only pays off with private info, shared shocks that shift valuations, and
temporal coupling — watering has all three. A sealed one-shot auction would make the
conversation redundant.

# Legibility

The transcript IS the explanation ("Fern got only 1 L because rain was forecast and it ceded
to Tomato's afternoon need"). A single optimizer can't hand you that sentence.
