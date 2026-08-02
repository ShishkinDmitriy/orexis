---
type: Domain Concept
title: Voucher
description: The token you win in the auction — a co-signed, single-use claim on the supplier for N litres, redeemed to actuate.
tags: [market, capabilities, settlement, futures]
timestamp: 2026-08-02T00:00:00Z
---

# What it is

The auction result as an object. A **voucher** is what you *win*: "bearer is owed N litres of
water from supplier S this round." It is distinct from the **access grant** that statically
binds an agent to a device — the access grant is *granted* (at genesis), the voucher is *won*
(each round). See [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# Shape

`sub` (who won), the supplier, `amount_l`, `debit` (the price), `round`, `jti` (single-use),
`exp`. **Co-signed** by the **host** (`match_sig` — the seller offered it) and
**clearing** (`val_sig` — it passed validation). Concretely a JWT/JWS; v1 signs with Ed25519.

# A claim, not a valve command

The voucher is a claim on the **supplier** (the resource owner), not a command to a specific
actuator. The holder redeems it with the supplier; the supplier maps *how much* (the voucher)
+ *which valve* (its `{plant_id → valve}` map, keyed by `sub`) and drives it. The buyer never
names a valve. See [supplier](/domain/supplier.md) and [executor](/domain/executor.md).

# Redemption — spot vs futures

- **Spot (v1):** redeemed on win — win → actuate now. Transient authorization; `exp` ≈ now.
- **Futures (v2):** **held and spent later**, any time until `exp` — win and actuate
  *decoupled*, the timing the agent's. Enables temporal strategy (water at night, wait for
  rain, hedge a forecast). See the futures item in [roadmap](/decisions/roadmap.md).

# Single-use

`jti` makes it single-use: the pump (and, in the futures model, the supplier's redemption
ledger) tracks spent vouchers so one win can't settle twice (double-spend / double-actuation).

# Why it exists even for immediate watering

Two roles, only one of which needs a held object:

- **Authorization** (always) — the co-signed proof that *this* actuation won the auction and
  cleared (the actuate boundary). Even spot routes through it.
- **Instrument** (futures) — a held, spendable claim.

See [thin-trusted-infra](/decisions/thin-trusted-infra.md) and
[clearing-as-validator](/decisions/clearing-as-validator.md).
