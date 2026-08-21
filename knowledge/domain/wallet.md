---
type: Domain Concept
title: Wallet
description: The single budget; how bids, allowance, and metabolic cost work.
---

# What it is

One budget per agent, paying for **both** water and thinking. See
[single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md).

# Two conservation laws (deliberately different)

- **Water** — hard-conserved, zero-sum. One tank, fixed litres. The
  [constitution](/domain/constitution.md)'s physical law.
- **Credits** — NOT zero-sum. Minted fresh each window as a periodic **allowance**,
  **spent-to-void** not transferred, controlled by the **currency ledger** (like a central
  bank — the one irreducible trusted store; see [thin-trusted-infra](/decisions/thin-trusted-infra.md)).
  This is what prevents permanent losers and kills Sybil swarms (newcomers join broke and
  accrue; nobody's credits are seized).

# Bid

Deterministic willingness-to-pay from a value model over its **sensed** moisture, target,
evaporation, and forecast — computed as a **function of unmet demand**. Priced in euros as
a *unit of account* (water has a real €/L cost); real money never actually moves. See
[deterministic-bid](/decisions/deterministic-bid.md) and [bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md).

# Metabolic cost

Every `deliberate()` call is metered (LLM tokens + host electricity) as it happens and
settled against the same wallet by the [clearing](/domain/clearing.md) step, **win or
lose** — metered per call, debited at clear (clearing holds the sole mint/debit authority;
see [trust-boundary](/decisions/trust-boundary.md)). Thinking is paid like metabolism. This
is what makes rounds self-limiting and bounded rationality economic. Metering is
deterministic and settled by the mint ([clearing](/domain/clearing.md)) — an agent can't
argue its bill down.

# Intention (committed plan)

```
Intention:
  this_round:  Move            # BID(38) | CEDE | PROPOSE_COALITION(...)
  commitments: [Commit]        # promises to future rounds
  horizon:     [float]         # planned credit spend across next N windows
  valid_while: Belief          # replan if this stops holding (e.g. no_rain_forecast)
```
