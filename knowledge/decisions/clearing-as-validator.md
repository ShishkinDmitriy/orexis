---
type: Decision
title: Clearing validates, it does not compute
description: The scarce side runs the auction; clearing is a thin region-want-free notary that checks integrity and co-signs the trade before settlement.
status: accepted
timestamp: 2026-08-01T00:00:00Z
---

# Context

Earlier framing made clearing the thing that *computes* the allocation, called by the
supplier. Two problems surfaced: (1) "who hosts the auction" is not fixed — the **scarce
(short) side hosts**, so the host rotates with market shape; (2) an allocator invites the
suspicion "did it compute the split fairly?". Both dissolve if clearing stops computing and
starts *checking*.

# Decision

The **host** (whichever agent is on the scarce side) runs the auction and produces a
proposed trade. **Clearing is a thin, region-want-free validator** — a predicate, not an
optimizer — invoked *after* the trade is struck and *before* settlement. It certifies the
trade is well-formed and co-signs it; it never decides who wins.

Because it is a *pure predicate over signed inputs*, clearing is really a **public function**,
not a trusted service: anyone can recompute `validate(trade, signed-orders)` and get the same
answer. Two enforcement flavors — **co-signature** (trust its key; the v1 code) or
**recompute + challenge** (no key; thinnest). See [thin-trusted-infra](/decisions/thin-trusted-infra.md).

- An **allocator** is an optimizer (discretion → riggable, hard to trust).
- A **validator** is a predicate (`valid? → bool`): no discretion, no strategy, trivially
  testable. The smallest possible trusted core.

# What clearing checks (integrity invariants)

Pure checks on the proposed trade against the participants' **signed orders**:

- **Conservation** — sums balance: allocated ≤ quantity offered; credits debited = credits
  paid; no money or resource created.
- **Solvency / availability** — each buyer's wallet covers its bid; each seller can supply
  its ask.
- **Identity** — every party is a certified id. See [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).
- **Constitution** — no allocation past rot threshold, total ≤ tank. See [constitution](/domain/constitution.md).
- **Order-consistency** — the trade never exceeds any party's signed order.

*Not* checked in v1: "did the host follow a committed auction rule" (mechanism conformance).
That needs an ex-ante commitment + bond and is deferred; without it the host just makes live
offers and counterparties self-protect (exposure is capped by their own signed order).

# The signature chain (topology-invariant)

Replace "bid" with **order** (bid *or* ask) and it is identical in every market shape:

```
participant order_sig : "I (cert) will pay ≤ P for ≤ Q"  (buyer)
                     or "I (cert) will supply ≥ Q at ≥ P" (seller)   — consent + solvency/availability
host        match_sig : "I, the scarce side, propose this match"     — supplier | consumer | exchange
clearing    val_sig   : "conserves, fits every signed order, ids ok, constitution holds"
```

The settlement token is that bundle. The [actuation](/domain/actuation.md) actuates **only**
a fully-signed token — counterparties consented (orders), host proposed (match), clearing
notarized (validity). This also kills fabrication and shill bids: the host can neither sign
as another agent nor out-mint its wallet.

# Division of labour

- **Value disputes** ("I deserve the water more") are resolved by the **market** — bid more.
- **Validity disputes** ("that trade double-spends") are resolved by **clearing** rejecting
  it. Clearing has no opinion to argue with; it is a boolean.

So the host may be as *greedy* (high reserve, surplus extraction) as its scarcity allows —
that is legitimate market power. It may not *cheat* the arithmetic, identity, or physics —
clearing blocks that. Greedy-but-committed, not non-greedy. See
[strategic-supplier](/decisions/strategic-supplier.md).

# What still cannot move to the host

- **The validator's honesty** — clearing's signature *is* the integrity guarantee, so it
  stays region-want-free infra; but it is now a tiny predicate, not a discretionary allocator.
- **Atomic settlement + the mint** — someone must debit-and-actuate atomically and mint the
  allowance; those stay in infrastructure, never the host, or penalties and bonds become
  meaningless. See [trust-boundary](/decisions/trust-boundary.md) and [wallet](/domain/wallet.md).

# Relation to the other seam

This is [standalone-clearing](/decisions/standalone-clearing.md) seen from the trust side:
the **host is topology-dependent, the validator is topology-invariant**. The host rotates
(supplier / consumer / exchange); the clearing predicate is unchanged; mint and actuate stay
in infra everywhere.

# Footnotes

- A malicious validator could *censor* a valid trade (refuse to sign) — fine with one
  trusted validator in v1; replicate / threshold-sign later.
- Supplier–buyer collusion only matters where it breaks conservation (which clearing
  catches); selling cheap to a friend merely costs the seller.
