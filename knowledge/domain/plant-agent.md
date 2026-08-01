---
type: Domain Concept
title: Plant agent
description: A self-interested plant with a desire, a wallet, and an event-driven loop.
tags: [agent, bdi, architecture]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

One agent per plant (Fern, Tomato, Succulent), each advocating its own moisture target. A
kind of [agent](/domain/agent.md) — the only tier with a stake (a desire and a
[wallet](/domain/wallet.md)) and therefore the only tier the trusted core is built to
constrain.

# Identity (important)

An agent's identity is NOT an LLM session. It is: the **charter** (static — identity,
plant URI, desire, endowment, skill set, system prompt), the **certificate** (signed proof
of who it is; see [authn-authz-capabilities](/decisions/authn-authz-capabilities.md)), the
**wallet**, the **active intention**, and the external **attested belief base**. The LLM is
a stateless pure function called inside a plan body; memory lives in the wallet and beliefs,
never in chat history. This is what lets 50 agents share one model yet hold separate
positions.

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

- **B** = attested beliefs + forecast.
- **D** = the target as a *trajectory* (value-of-water curve), not a point. Chartered by the
  sovereign; an agent does not invent new desires.
- **Skills** = the plan library (negotiation moves: inform, bid, cede, counter_offer,
  coalition, bluff). Means, not ends. May be learned; may vary per agent.
- **I** = a desire bound to a chosen skill, committed with resources; persists unless
  `valid_while` fails (Bratman reconsideration).

# Invariants

- The **bid is deterministic**; the LLM produces only the stance/justification.
- Every justification **cites attested triples** or is rejected (the leash).
- The bid is a function of **unmet demand**. See [bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md).
