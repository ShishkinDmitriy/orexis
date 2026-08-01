---
type: Decision
title: Single wallet with metabolic cost
description: One wallet pays for water and for thinking; deliberation is priced.
status: accepted
stage: v1
tags: [economy, bounded-rationality]
timestamp: 2026-08-01T00:00:00Z
---

# Decision

Each agent has **one wallet**. It pays for water AND for its own deliberation — LLM tokens
and host electricity, metered by the trusted runtime per `deliberate()` call and settled
against the wallet by the [clearing](/domain/clearing.md) step, **regardless of outcome**
(winners and losers both pay to think).

# Why

- Makes the society **self-limiting**: arguing too long or deliberating too deeply spends
  the budget needed for water, so rounds terminate endogenously; the hard max-round ceiling
  stays only as a safety backstop, not the primary terminator.
- Turns **bounded rationality into an economic constraint** — an agent must decide *how much
  to think* as part of deciding what to do. Metareasoning as a line item, not a control layer.
- Aligns economy with architecture: an agent that deliberates when it should reflex goes
  broke, which enforces the reactive/deliberative split from
  [plant-agent](/domain/plant-agent.md).

# Notes

- Cost metering is deterministic and lives in the trusted core — an agent can't argue its
  own bill down. See [trust-boundary](/decisions/trust-boundary.md).
- The allowance rate vs water scarcity is the one economic knob worth tuning empirically.
- Single wallet chosen over a separate compute budget for simplicity, accepting slightly
  harder debugging (compute-spend not separable from water-spend).
