---
type: Domain Concept
title: Agent
description: A certified, self-interested principal with a wallet and a stake — the only tier the trust boundary constrains.
tags: [agent, identity, architecture]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

The general notion of an **agent**: a self-interested principal that holds a *stake* (a
desire and a [wallet](/domain/wallet.md)) and therefore the only tier the trusted core is
built to constrain. Services (gateway, clearing, executor) are stake-free and are *not*
agents. The concrete kinds are the [plant agent](/domain/plant-agent.md) (advocates a
moisture target) and the [supplier](/domain/supplier.md) (a strategic seller); both are
agents in this sense — they have positions to advance and can be lied through.

# Identity — not an LLM session

An agent's identity is a bundle of durable, external parts, never chat history:

- **Charter** (static) — identity, plant URI, desire, endowment, skill set, system prompt.
- **Certificate** — the signed proof of *who it is*; issued with the charter in v1. See
  [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).
- **Wallet** — the single budget for water and thinking ([wallet](/domain/wallet.md)).
- **Active intention** — the committed plan, persisting until its `valid_while` fails.
- **Attested testimony** — the read-only common record it may cite (its own beliefs are
  private; there is no shared knowledge). See [belief-base](/domain/belief-base.md).

The LLM is a *stateless pure function* called inside a plan body; memory lives in the wallet
and beliefs. This is what lets many agents share one model yet hold separate, stable
positions.

# What an agent owns (judgment, private data, perception)

Interpretation and initiative belong to the agent, not infra (see
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md)):

- **Its own band.** "Am I `:LOW`?" is desire-relative — the agent computes it from the
  attested measurement + its charter target. The gateway attests the number, not the verdict.
- **Its private state.** Its moisture (need-to-know), value curve, and beliefs are the
  agent's — attested but scoped private. It shares its *bid*, not its state.
- **Its perception.** The agent drives sensing (pull, not push) and how often — it can even
  tell the sensor to sleep — paying for it (perception is a priced action); a bid must cite a
  *fresh* reading.
- **Its self-metrics.** It may log its own view (wallet, wins) as **untrusted** claims; the
  authoritative ledger is clearing's.

# What an agent may NOT do

The three privileged powers are never granted to an agent, no matter how spotless its
reputation or valid its cert — because a single defection here does irreversible real-world
harm:

1. **Author attested facts** — only the [gateway](/domain/gateway.md) writes `:attested`.
2. **Mint / debit currency** — only [clearing](/domain/clearing.md) does.
3. **Actuate hardware** — only the trusted executor touches the pump, post-constitution.

Everything an agent does is a *request* to the trusted core; every message from a peer is
*data to weigh*, never an *instruction to obey*. See [trust-boundary](/decisions/trust-boundary.md).

# AuthN vs AuthZ

- An agent **bears a certificate** — durable proof of *who it is* (authentication).
- An agent **receives capability grants** — ephemeral, scoped, per-round proof of *what it
  may do now* (authorization), issued by clearing as the auction result and settled by the
  trusted core. It never receives a standing power, only a bounded, expiring grant.

Both are self-verifying signed artifacts, checked locally. See
[authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# Invariants

- The **bid is deterministic**; the LLM produces only the stance/justification
  ([deterministic-bid](/decisions/deterministic-bid.md)).
- Every justification **cites attested triples** or is rejected (the leash).
- The bid is a function of **unmet demand** ([bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md)).
- Identity and stake are **external and durable**; the LLM call is stateless.

The [plant agent](/domain/plant-agent.md) specializes this with its two-layer (reactive /
deliberative) BDI architecture.
