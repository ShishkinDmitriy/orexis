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

- **Its own id** — the only thing an agent process is *told*. One process, one agent.
- **Charter** — two halves, deliberately different in kind: its **wiring** from the public
  [world](/decisions/world-graph.md) (what it acts for, what it may poll, which market, and
  the capabilities all of that *derives*) and its **own beliefs** (desire, endowment, limits,
  cadence, value curve) from `:beliefs/<agent>`. It reads both from its id and needs nothing
  else. See [capability-modules](/decisions/capability-modules.md).
- **Certificate** — the signed proof of *who it is*; issued with the charter in v1. See
  [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).
- **Wallet** — the single budget for water and thinking ([wallet](/domain/wallet.md)).
- **Active intention** — the committed plan, persisting until its `valid_while` fails.
- **The public record** — the world's wiring and the sensed measurements it may cite (its own
  beliefs stay private; there is no shared knowledge). See [belief-base](/domain/belief-base.md).

The LLM is a *stateless pure function* called inside a plan body; memory lives in the wallet
and beliefs. This is what lets many agents share one model yet hold separate, stable
positions.

# What an agent owns (judgment, private data, perception)

Interpretation and initiative belong to the agent, not infra (see
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md)):

- **Its own band.** "Am I `:LOW`?" is desire-relative — the agent computes it from the sensed
  measurement + its own `bandLow`/`bandHigh`. The record holds the number, never the verdict;
  the band is not stored anywhere at all.
- **Its private state.** Its moisture (need-to-know), value curve, desire, and limits are the
  agent's, and live in its own `:beliefs/<agent>` graph. It shares its *bid*, not its state.
  What is *public* is only the wiring — see [world-graph](/decisions/world-graph.md).
- **Its perception.** Where the hardware allows it, the agent drives sensing and decides how
  often — it can even tell the sensor to sleep — paying for it (perception is a priced
  action); either way a bid must cite a reading it still trusts. Built in v1 except the
  price: see [sensing](/domain/sensing.md).
- **Its self-metrics.** It may log its own view (wallet, wins) as **untrusted** claims; the
  authoritative ledger is clearing's.

# Lifecycle — birth is not start

Three distinct events, and conflating any two of them turns a belief back into configuration.

| | when | what happens | repeatable |
|---|---|---|---|
| **birth** | once, per agent per world | the agent comes into existence: its beliefs graph is created from what the sovereign ratified | **no** — a second birth discards who the agent became |
| **start** | every time a process comes up | reads the world, reads its own beliefs, runs the modules its capabilities name | yes, freely |
| **stop** | the process goes down | modules release timers and connections; **beliefs survive** | yes |

Start and stop are **pause and resume**. Nothing about the agent changes across them — it is
the same agent, not running. That is why opening beliefs can be the agent's own to revise
thereafter: revision survives a restart precisely because a restart is not a birth.

Birth is the only event that may author beliefs, and it is the sovereign's act, not code's
(see [genesis-process](/domain/genesis-process.md)). Death — an agent removed from the world —
is unmodelled; [genesis](/decisions/genesis.md) flags it as the hard case in a destructive
migration, because a wallet and outstanding commitments have to go somewhere.

In deployment the verbs line up: `podman compose up` is start, `down` is stop, and neither
touches a belief. **Birth is the agent's own first boot** — it writes its opening beliefs from
the ratified files if, and only if, it has none, and logs `born`. Every start afterwards
refreshes the public world and leaves beliefs alone.

The three are now separated in the code, not merely in this document. An agent's belief base is
a persistent volume of its own, so a restart cannot reset who it became; discarding it takes an
explicit `down -v`, which is a re-birth by another name and is meant to look like one.

# What an agent may NOT do

The three privileged powers are never granted to an agent, no matter how spotless its
reputation or valid its cert — because a single defection here does irreversible real-world
harm:

1. **Author facts about others** — an agent writes only its own `:beliefs/<agent>` and its
   own reading; it never writes the [world](/decisions/world-graph.md) (the sovereign's) or
   another agent's graph. Under an adversarial assumption a witness authors readings too —
   see [trusted-agent-mode](/decisions/trusted-agent-mode.md).
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
- Every justification **cites triples from the record** or is rejected (the leash).
- The bid is a function of **unmet demand** ([bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md)).
- Identity and stake are **external and durable**; the LLM call is stateless.

The [plant agent](/domain/plant-agent.md) specializes this with its two-layer (reactive /
deliberative) BDI architecture.
