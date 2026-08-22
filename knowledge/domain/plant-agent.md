---
type: Role
title: Plant agent
term: http://example.org/agora/water#Plant
description: A self-interested plant with a desire, a wallet, and an event-driven loop.
---

# What it is

One agent per plant (Fern, Tomato, Succulent), each advocating its own moisture target. A
kind of [agent](/domain/agent.md) — the only tier with a stake (a desire and a
[wallet](/domain/wallet.md)) and therefore the tier the trust model is built around.

# Identity (important)

An agent's identity is NOT an LLM session. It is: the **charter** (its public wiring from the
world plus its own private beliefs — identity,
plant URI, desire, endowment, skill set, system prompt), the **certificate** (signed proof
of who it is; see [authn-authz-capabilities](/decisions/authn-authz-capabilities.md)), the
**wallet**, the **active intention**, and its own **beliefs** (self-asserted `:sensed` +
`:opinion`; no witness in [trusted-agent-mode](/decisions/trusted-agent-mode.md)). It holds the
model the same way every agent does — see [agent](/domain/agent.md) for the invariants, which
are what let 50 of these share one model and still hold separate positions.

# Architecture — two layers, two tempos

Hybrid BDI (InteRRaP lineage):
- **Reactive** — owns the MQTT state machine, dispatches on `(performative, state)`, fires
  reflexes (a constitutional veto; ignore an unaffordable CFP), holds reconsideration guards
  (`valid_while`). Deterministic, always in control of timing. Most messages die here with
  no LLM call.
- **Deliberative** — the BDI core, reached only on a real decision. Recompute the value
  curve, prune options by wallet and [constitution](/domain/constitution.md), select a
  skill, commit an [intention](/domain/wallet.md). At most one LLM call.

Control flow: bottom-up activation, top-down execution. The agent owns no loop of its own —
its "loop" is the bus delivering messages. See [deterministic-bid](/decisions/deterministic-bid.md).

# BDI mapping

- **B** = its own sensed readings + forecast (self-asserted; the agent judges its own band).
- **D** = the target as a *trajectory* (value-of-water curve), not a point. Chartered by the
  sovereign; an agent does not invent new desires.
- **Skills** = the plan library (negotiation moves: inform, bid, cede, counter_offer,
  coalition, bluff). Means, not ends. May be learned; may vary per agent.
- **I** = a desire bound to a chosen skill, committed with resources; persists unless
  `valid_while` fails (Bratman reconsideration).

# Invariants

Every agent's are in [agent](/domain/agent.md) — a deterministic bid, an LLM that produces only
the stance, a bid that is a function of unmet demand. One is this tier's own:

- A justification **may cite** the agent's own sensed facts to be believed — *voluntary*
  disclosure, not mandatory (the leash relaxed in trusted mode; see
  [agent-centric-epistemics](/decisions/agent-centric-epistemics.md)). It is the plant edge that
  has facts of its own to disclose, which is why the choice lands here.
