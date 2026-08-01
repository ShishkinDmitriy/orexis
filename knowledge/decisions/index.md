---
type: Index
title: Decisions
description: Index of architecture decisions (ADR-style) with rationale and open seams.
tags: [index, decisions]
timestamp: 2026-08-01T00:00:00Z
---

# Decisions

Architecture decisions, ADR-style: context, the choice, why, and — where it matters —
the *seam* deliberately left open for a later stage. Read these when you're about to
change something, to check you're not welding shut a planned extension.

# Core architecture

* [trust-boundary](/decisions/trust-boundary.md) - Agents cite but never author facts, mint currency, or actuate. Three privileged powers stay in trusted infrastructure.
* [llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) - Thin BDI: the LLM drives deliberation; the formal layer becomes load-bearing, not optional.
* [deterministic-bid](/decisions/deterministic-bid.md) - The bid number is code; the LLM only produces the justification. Rhetoric can't move the number.
* [english-vs-formal](/decisions/english-vs-formal.md) - English for what's contested, formal (RDF/SHACL) for what's trusted.

# Identity & authorization

* [authn-authz-capabilities](/decisions/authn-authz-capabilities.md) - Cert = who you are (durable); signed capability grant / JWT = what you may do now (ephemeral). Revoke only on provable violation.

# Economy

* [single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md) - One wallet for water and compute; thinking costs, so bounded rationality is priced in.
* [strategic-supplier](/decisions/strategic-supplier.md) - The supplier is a genuine seller with costs and a reserve price (Design B), not a stake-free utility.

# Belief base

* [two-store-beliefs](/decisions/two-store-beliefs.md) - InfluxDB owns the series; Fuseki owns citable current-state. Joined by plant URI, never federated.

# Seams (open on purpose)

* [standalone-clearing](/decisions/standalone-clearing.md) - Clearing is a separable function the supplier calls, so N-to-N later is a change of caller, not a rewrite.
* [bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md) - Bids reflect current unmet need, so multi-source decomposition stays possible.
* [roadmap](/decisions/roadmap.md) - What v1 is, and the v2/v3 extensions each seam unlocks.
