---
type: Decision
title: Thin trusted infrastructure — public functions, signed artifacts, bounded devices
description: Relax the three privileged powers toward public/verifiable mechanisms; the one irreducible trusted thing is the currency ledger (double-spend), thin in single-operator mode.
status: accepted
timestamp: 2026-08-02T00:00:00Z
---

# Context

[trust-boundary](/decisions/trust-boundary.md) put three powers in stake-free infra —
**attest, mint, actuate**. Under a trusted-agent assumption (single operator, non-adversarial)
most of that defends a threat that isn't there. Push the infra as thin as it goes, and see
what genuinely can't move.

# Decision — the three powers, relaxed toward public mechanisms

- **Attest → dropped.** Each agent self-asserts its own state as opinion (`:sensed` /
  `:classification`). Not infra. See [trusted-agent-mode](/decisions/trusted-agent-mode.md).
- **Actuate → the resource owner.** The **supplier** drives its own valves — it *executes*
  a claim (how much) + topology (which valve), it does not *decide*. Safe because the amount
  is bounded by two independent checks it doesn't control: **clearing** (a valid, cleared
  amount) upstream, and the **device fail-safe cap** downstream. The standalone executor
  dissolves into the supplier's actuation arm. See [executor](/domain/executor.md),
  [supplier](/domain/supplier.md).
- **Validity (clearing) → a public function.** Validity is *math*:
  `validate(trade, signed-orders)` is a pure function anyone recomputes to the same answer, so
  it needs no trusted service. Two enforcement flavors: a **co-signature** (trust clearing's
  key — heavier, the current code) or **recompute + challenge** (optimistic verification —
  thin, no key). Trusted mode prefers recomputation. See
  [clearing-as-validator](/decisions/clearing-as-validator.md).
- **Mint (currency) → the one that resists.** A wallet debit is *self-signed* by the payer
  (it consented via its bid); the allowance is a *deterministic rule* (every agent gets X per
  window). But **someone must hold the canonical ledger** to stop double-spend.

# The one irreducible trusted thing: the currency ledger

Everything else becomes public functions + signed artifacts + bounded devices. The single
thing that cannot be a pure function or a self-signed artifact is the **canonical ledger** that
prevents double-spend — because *"has fern already spent this credit?"* is a question about
**global order**, not local math. In **single-operator** mode it is thin: one authoritative
store. It gets heavy — **consensus** — only if you open the society to mutually-distrusting
operators. That is the real cost of going open, and it is deliberately parked. See
[roadmap](/decisions/roadmap.md).

# The shape of thin infra

- **Public functions** (anyone runs + verifies): clearing / validation, the value model, the
  band judgment.
- **Signed artifacts** (self-verifying, no service): [cert, access grant,
  claim](/decisions/authn-authz-capabilities.md), bids, payments.
- **Bounded devices** (physical, capped): sensors (self-assert), actuators (resource owner +
  fail-safe cap).
- **One thin trusted store**: the currency ledger (double-spend). Consensus only in the open
  case.

# Residuals (open, adversarial-only)

- A resource owner force-watering to rot via **repeated sub-cap doses** → needs a cumulative
  device cap + a challenge path. (Trusted mode: fine.)
- Recompute-and-challenge needs someone watching → optimistic-verification machinery (v2).

The co-signed claim we build in v1 is the **adversarial-safe fallback** for these; the pure
public-function path is the thin default under the trusted-agent assumption.
