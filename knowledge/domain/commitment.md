---
type: Domain Concept
title: Commitment
description: >-
  REA's promised economic flow — who it is for, what it permits, how much, from which round,
  once, until when — as the kernel's `agent/commitment.py`. What a valve FULFILS: the market's
  claim is its embodiment (the flow plus the credit leg and, on the wire, the signatures), and a
  self-dose is one with nobody to pay. In the kernel because two packages that may not import
  each other both hold it. Not BDI's commitment, which is an intention.
---

# What it is

The **promised flow**. [settlement-speaks-rea](/decisions/settlement-speaks-rea.md) aligned the
market to ValueFlows and found the correction that names this page: what you win in an auction
is a `vf:Commitment` — *a planned economic flow* — and the valve opening is the
`vf:EconomicEvent` that fulfils it. `agent/commitment.py` is that shape and nothing more: `sub`,
`scope`, `amount_l`, `auction_id`, `jti`, `exp`.

# Who holds it, and why it is the kernel's

Two capabilities meet on it and may not import each other. The market **issues** one: its
[claim](/domain/claim.md) is a `Commitment` with the credit leg (`debit`) added — the
settlement token, co-signed on the wire. Actuation **fulfils** one: `redeem` reads the six
fields a command is built from and a device verifies, whether the host handed it the market's
claim or the agent minted a self-dose (#190) — a commitment with nobody to pay. The
independence contract in `pyproject.toml` is what puts the shape in the kernel: it is REA
structure, as an intention is BDI structure.

# What it is not

**Not an [intention](/domain/intention.md).** That is BDI's commitment — the agent's own, to an
action, kept in its ledger. [a-mandate-is-not-a-commitment](/decisions/a-mandate-is-not-a-commitment.md)
ruled that the word means these two things and the governance thing takes *mandate*. An
[obligation](/domain/obligation.md) is the host's side of this one — the debt a claim raised,
recorded as a want.
