---
type: Component
title: Clearing
description: Thin stake-free validator that checks a proposed trade and co-signs it before settlement — a notary, not an allocator.
---

# What it is

A **thin, stake-free, deterministic validator** — a predicate, not an optimizer. It does
**not** compute who wins; the host (the scarce side — see below) runs the auction and
produces a proposed trade. Clearing is invoked *after* the trade is struck and *before*
settlement: it checks the trade is well-formed and **co-signs** it. It is NOT an agent and
has no LLM. See [clearing-as-validator](/decisions/clearing-as-validator.md).

Think **notary**: it does not decide the deal; it certifies the deal is well-formed, the
parties are real, and the money is there.

# Who hosts (topology-invariant clearing)

The **scarce (short) side hosts** the auction; the host rotates with market shape, but
clearing is unchanged:

- 1 supplier, N consumers → the [supplier](/domain/supplier.md) hosts (forward auction)
- N suppliers, 1 consumer → the consumer hosts (reverse auction)
- N ↔ N → a stake-free exchange hosts (order book)

See [standalone-clearing](/decisions/standalone-clearing.md).

# What it checks (per trade)

Pure checks on the proposed trade against the participants' **signed orders** (bids or asks):

1. **Conservation** — allocated ≤ quantity offered; credits debited = credits paid; nothing
   created.
2. **Solvency / availability** — each buyer's wallet covers its bid; each seller can supply.
3. **Identity** — every party is a certified id (reads only the move, never the English).
4. **Constitution** — no allocation past rot threshold, total ≤ tank. See
   [constitution](/domain/constitution.md).
5. **Order-consistency** — the trade never exceeds any party's signed order.

Pass → clearing **co-signs** the [claim](/domain/claim.md) (`val_sig`) and hands it to the
executor arm (the [supplier](/domain/supplier.md), which actuates only a fully-signed
claim). See [authn-authz-capabilities](/decisions/authn-authz-capabilities.md). At
settlement, clearing also meters and debits wallets (water won + metabolic cost of
deliberation — see [wallet](/domain/wallet.md)); mint/debit authority lives here, never in
the host.

# Invariant

Deterministic and injection-proof: agent messages are data, never instructions. A **pure
predicate** (really a [public function](/decisions/thin-trusted-infra.md) — recomputable),
fully unit-testable in isolation — scripted trade in, valid/invalid out, no model in the
loop. **Mint** stays in infrastructure (the currency ledger); **actuate** is the resource
owner's, bounded by the cleared claim + the device fail-safe. See
[trust-boundary](/decisions/trust-boundary.md) and [thin-trusted-infra](/decisions/thin-trusted-infra.md).
