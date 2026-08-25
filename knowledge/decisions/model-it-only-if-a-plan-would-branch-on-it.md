---
type: Decision
title: Model it only if a plan would branch on it — which self-beliefs an agent holds, and which are telemetry
description: >-
  An agent could believe things about every layer under it and every part of itself, and most
  of that would be a belief base churning faster than the world it is supposed to describe.
  Decided on one test — model it only if a belief about it changes which plan gets selected,
  everything else is telemetry — and on what follows: infrastructure reaches belief only through
  a named projection, anything the interpreter already knows is COMPUTED and never asserted,
  self-telemetry gets bands rather than raw values, reflection caps at one level, and beliefs
  about peers stay first-order.
status: accepted
timestamp: 2026-08-26T20:00:00Z
---

# The test

**Model it only if a belief about it changes which plan gets selected.** Everything else is
telemetry: log it, report it, never believe it. The cost of getting this wrong is not tidiness —
it is a belief base that churns faster than the world does, waking the deliberator for facts no
plan branches on.

# The layers below

Transport state mostly fails the test. Retries, QoS bookkeeping, handshakes: no plan branches on
them, and they are handled where they happen
([the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md)). Their
PROJECTIONS pass it, and each is named deliberately rather than leaking upward:

| projection | why a plan branches on it |
|---|---|
| a sensor unreachable | fall back to an estimate, or refuse to actuate blind |
| the bus degraded | do not open an auction you cannot settle |
| an actuator faulted | the goal is unachievable — a deliberation input, not an error |

Three predicates, not a model of a broker. None of the three is built: what exists is the
freshness want going cold, which covers *cannot see* and is what the planner acts on today. Each
becomes worth minting when a plan would actually take the other branch: the first when an
agent holds an estimate worth falling back to, the second when a host can tell a quiet venue
from an unreachable one, the third when a plan can name a compensating action.

# Self-beliefs are six different things, and the column that matters is store-or-compute

| kind | example | store or compute | here today |
|---|---|---|---|
| resource | the wallet, the water allocation | **store** — external state | `market:hasEndowment` authored, balance held in memory — the one row that breaks the rule ([#395](https://github.com/ShishkinDmitriy/orexis/issues/395)) |
| intention introspection | am I already pursuing this? | **compute** | `keeper.standing(action, want)` over the ledger |
| capability | do I hold any way of doing this? | **compute** | `Self.can`, `agent.provider(family)`, and the menu derived on every ask |
| epistemic | how stale is what I believe? | **compute** | the freshness want, from `resultTime` and the horizon the agent published |
| performance history | does this lever ever pay? | **store** | the ledger's `endMet` verdicts; `suspects()` computes over them |
| meta-control | what does deliberating cost me? | store | the trace's verdict counts; no model, so no token cost yet |

**Anything the interpreter already knows is a derived predicate over interpreter state, never an
asserted belief.** Assert *pursuing(g)* into the belief base and there are two sources of truth
for one fact, and the asserted one will be wrong within the hour. Jason gets this right with
`.intend` and `.desire` as internal actions evaluated on demand; the equivalent here is that
every question about what stands is a query over the intention graph, and every question about
what this agent can do is a query over the world graph. Assert only what comes from outside, or
what is genuinely expensive to recompute.

**Embodiment is its own tier.** *This valve is stuck*, *this pump is available* — not beliefs
about the world and not beliefs about the mind, but about the body, and they sit beside the
projections above. They are what makes compensation plannable: a plan can only declare a
compensating action if the agent has a belief about whether the effector still works. The
nearest thing that exists is suspicion — `suspects()` flags an (action, want) pair whose end has
gone unmet `suspectAfter` times running, which is the graph claiming a movement the world keeps
refusing. It is flagged and never auto-retracted, because what to do about a belief that is not
paying is a decision
([an-intention-stands-until-the-world-answers](/decisions/an-intention-stands-until-the-world-answers.md)).

# Where it goes wrong

- **Deliberation storms.** Self-telemetry churns faster than the world. Put queue depth or load
  in the belief base and the revision function fires constantly. Anything modelled gets the same
  treatment sensor data gets: **bands and transitions, never raw values**
  ([band](/domain/band.md)) — which is already why an announcement carries LOW and not 0.31.
- **Regress.** Beliefs about beliefs about beliefs. **Cap at one level of reflection** unless a
  specific plan needs the second, and it almost never does.
- **Social nesting.** In an auction this is the real hazard: reasoning about what one bidder
  believes another will bid is unbounded, and it is how a multi-agent system becomes
  unshippable. **First-order observed behaviour only** — that this agent won that round, what it
  has bid before — and reliability estimated from observation rather than from a nested
  epistemic state. Nothing here nests today, and the structure helps: a bid is sealed and
  private ([deterministic-bid](/decisions/deterministic-bid.md)), so there is nothing to model a
  peer's reasoning FROM, and what a host records about a participant is an
  [obligation](/domain/obligation.md), which is first-order by construction.

# What this settles for the shipped worlds

Resource beliefs and the epistemic layer — freshness, the source a reading came from, whether an
instrument is still speaking — carry nearly all the weight in `world/simulation`. Capability and
performance history become load-bearing when the market starts needing an agent to bid honestly
about what it can actually deliver, which is
[strategic-supplier](/decisions/strategic-supplier.md)'s seam.

# Seams left open

- **The three projections are unnamed and unbuilt.** Deliberately: each waits on a plan that
  would take the other branch, and minting a predicate nothing reads is the failure this record
  exists to prevent.
- **Meta-control has nothing to weigh yet.** A model in deliberation is what would give
  *deliberation costs me this much* a plan to change.
- **One level of reflection is a rule with no enforcement.** Nothing refuses a belief about a
  belief about a belief; the cap is a habit until something tries.
