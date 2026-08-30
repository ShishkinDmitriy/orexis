---
type: Decision
title: The auction, the clearing validator and the market's types are the market's — the kernel names no bid
description: >-
  `agent/auction.py` (propose, validate, issue), `agent/clearing.py` (the notary that checks a
  trade and mints claims) and `agent/market.py` (Bid, Offer, Trade, MarketState) sat in the
  kernel while the only code that called them was the market package. A kernel is what LOADS
  packages and should know no bid; all three move to `packages/orexis-capability-market/`. The one
  thing that resisted was actuation importing the market's `Claim`, which the independence
  contract forbids between packages — and the sovereign's correction resolved it: a claim is
  the EMBODIMENT of a commitment, REA's promised flow, and the commitment is the kernel's.
status: accepted
timestamp: 2026-08-26T12:00:00Z
---

# What was true before

[bid-matching-is-a-capability](/decisions/bid-matching-is-a-capability.md) moved the *allocation*
out of `agent/auction.py` into the market package and recorded that `run_round` **stayed** —
"propose, validate, issue is the auction's shape, not a strategy". True, and beside the point:
the shape of an auction is still the market's business, not the kernel's. Three kernel modules
remained whose only callers were `hosting.py`, `bidding.py`, `matching.py` and one import in
actuation: the sequence (`auction.py`), the notary (`clearing.py`) and the nouns
(`market.py` — Bid, Offer, Trade, TradeLine, MarketState, Limits, and the litre epsilon). The
kernel held a package's vocabulary in Python while its ontology, since
[the-action-is-the-kind](/decisions/the-action-is-the-kind.md), held none of it in RDF.

# What is decided

The three move: `packages/orexis-capability-market/auction.py`, `clearing.py`, and `trade.py` for the
types (the file is named for what it holds, not for the package it is in). Every import is now
relative inside the package; `tests/test_clearing.py` reaches through the package path as the
market's own `test_auction.py` already did.

**A claim embodies a commitment, and the commitment is the kernel's.** `actuation/module.py`
imported `Claim` to mint a self-dose (#190), and after the move that would be one capability
package importing another's Python — the independence contract in `pyproject.toml` refuses it,
and should. The first draft gave actuation a `Dose` of its own, the claim's shape restated; the
sovereign's correction is the better answer: a claim is the *embodiment* of REA's commitment
(the promised flow — [settlement-speaks-rea](/decisions/settlement-speaks-rea.md) already said
so), and commitment is structure, as an intention is. So `commitment.py` (progression's, `packages/orexis-progression-patience/`) holds the six
fields a valve fulfils, `Claim` extends it with the credit leg, and a self-dose is a
`Commitment` with nobody to pay. Actuation imports the kernel; the market imports the kernel;
neither imports the other. See [commitment](/domain/commitment.md).

# What did not change

The signing keys are still named `host` and `clearing` (`agent/signing.py`), because the
*roles* are the constitution's — [trust-boundary](/decisions/trust-boundary.md) — and a key
name is not an import. [a-role-needs-something-to-be-a-role-in](/decisions/a-role-needs-something-to-be-a-role-in.md)'s
line that the clearing validator is "a function; no agent holds it" stays true one directory
over.

# Seams left open

- **Two epsilons.** `market.trade.EPS` and `actuation.EPS` are the same figure stated twice.
  A kernel `quantity` module would be the honest home the day a third package needs it.
- **`amount_l` is a litre.** The commitment's flow is stated in the good's unit by name, and the
  domain is meant to be a plug-in; the field is where a unit would arrive.
- **A commitment names no step.** It says how much of what for whom, and not WHICH action with
  which bindings it is a promise to take — a plan step, once that has a name, is what a claim
  would be a commitment to.
