---
type: Decision
title: Deterministic bid, LLM justification
description: The bid number is code; the LLM only argues around it.
status: accepted
timestamp: 2026-08-01T00:00:00Z
---

# Context

If the LLM produces the bid amount, rhetoric inflates the number the system acts on, and
the auction stops being honest.

# Decision

The **bid amount is deterministic code** — a value model over attested moisture, target,
evaporation, forecast (see [wallet](/domain/wallet.md) and
[plant agent](/domain/plant-agent.md)). The **LLM produces only the stance**: the English
justification and any coalition move. The mediator clears on the number; it ignores the prose.

# Why

- The number an agent acts on can't be talked up; only the talk around it varies.
- Stub the LLM out and the agent still transacts on its deterministic bid — the model adds
  legibility and coalition reasoning, not core function.

# Related

- The justification cites the agent's sensed facts — "the leash." Originally mandatory (cite
  or be rejected); relaxed to **voluntary disclosure** in trusted mode (reveal to be believed,
  witness-signed to be credible). See [agent-centric-epistemics](/decisions/agent-centric-epistemics.md)
  and [belief-base](/domain/belief-base.md).
