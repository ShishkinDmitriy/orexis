---
type: Decision
title: LLM-heavy deliberation (thin BDI)
description: The LLM drives deliberation; classical BDI machinery stays thin.
status: accepted
timestamp: 2026-08-01T00:00:00Z
---

# Context

Two options for where deliberation lives: LLM-thin/classical-BDI (symbolic plan selection,
LLM only phrases content) vs LLM-heavy/thin-BDI (one LLM call over beliefs + transcript +
wallet emits the move; skills are affordances named in the prompt).

# Decision

Go **LLM-heavy**. The [plant agent](/domain/plant-agent.md)'s deliberation is one LLM call
that produces a stance; skill selection can be the model's call rather than symbolic
context-matching.

# Why

- Faster to a running society; traces read well.
- Buys the domain-swap property: agents read the ontology (T-Box) from context and compose
  their own queries, so changing the domain needs no agent code change. See
  [roadmap](/decisions/roadmap.md).

# Consequence — the formal layer becomes load-bearing

Precisely *because* deliberation is prose and persuasive, the formal layer is the only
thing between us and an agent that wins by talking well. LLM-heavy *raises* the stakes on
the ontology and constitution rather than removing them. See
[english-vs-formal](/decisions/english-vs-formal.md) and
[deterministic-bid](/decisions/deterministic-bid.md).

# Amended: the stance is an intention, made checkable

[an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md)
narrows "produces a stance" without reversing it. Prose remains how the model reasons; what it
*commits* is a typed `ag:Intention` the shapes can refuse — chosen from a menu of
affordances, never free text-to-action. The model is also not consulted per sensing: an
intention persists until satisfied, impossible or reconsidered, which is what makes an
LLM-heavy agent affordable at all. The consequence above is unchanged and is exactly the
mechanism the amendment leans on.
