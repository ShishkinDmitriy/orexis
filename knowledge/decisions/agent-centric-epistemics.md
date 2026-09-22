---
type: Decision
title: Agent-centric epistemics — judgment, data, and initiative belong to the agent
description: Push interpretation, private data, and sensing to the agent; keep infra thin and honest; author by region want; disclose need-to-know; observe via sovereign god-view.
status: accepted
timestamp: 2026-08-02T00:00:00Z
---

# Context

Reviewing the design we kept finding the same shape: **infra was doing things that are
properly the agent's.** Four corrections, one principle. (The v1 *code* still does some of
these the old way — this records the target it should move toward.)

# 1. Measurement vs judgment — the gateway measures, the agent judges

`0.18` is a fact (testimony). "Is 0.18 **LOW**?" depends on what the plant *wants* — a
succulent shrugs, a fern is parched. So the band is **desire-relative interpretation, not
ground truth**, and belongs to the agent, from the attested measurement + its charter
target. Attesting `hasCurrentMoisture :LOW` into a shared graph was asserting a *judgment as
testimony* — it broke "no shared knowledge, only testimony + private belief." The
[gateway](/domain/gateway.md) attests the measurement; each [agent](/domain/agent.md)
computes its own band. (The old "threshold is the gateway's one authority" reasoning in
[two-store-beliefs](/decisions/two-store-beliefs.md) conflated measurement with judgment.)

Keep separate: the **comfort band** (desire-relative → the agent's) vs the **rot limit**
(objective physical harm → the [constitution](/domain/constitution.md)'s). Agents own what
they *want*; the constitution owns what's *physically forbidden*.

# 2. Minimal disclosure — the measurement is private-but-attested

Nobody needs fern's moisture; the market needs fern's **bid**. A market *aggregates private
information into a price without exposing it* — so moisture and value curve stay private.
Private ≠ unattested: the gateway still signs the reading (honest), it is just **scoped
private and disclosed need-to-know** (like a tax return — not published, but the auditor can
demand it). The [constitution](/domain/constitution.md)'s rot check gets a plant's
measurement on need-to-know; peers never do.

- **Shared** = market moves (bids), trades, and the rules (structure, ontology, constitution).
- **Private** = measurements, value curves, internal state.

The leash flips from mandatory to **voluntary disclosure**: an agent *chooses* to reveal an
attested fact in its justification to be believed (witness-signed, so credible). Persuasion
with receipts, on its own terms.

# 3. Agent-driven sensing — pull, not push; sensing is a priced action

The sensor should not push on its own cadence (that is the edge "acting"). Invert it: the
**agent initiates sensing and decides how often**; the firmware is a thin reactive service
(`sense` / `sleep`) — mechanism, not policy — symmetric with the pump. Honesty holds because
**cadence ≠ content**: the agent controls *when* it looks, the witness still authors *what*
it reads, and a bid must cite a **fresh-enough** attested reading (so stale, favourable data
can't back a bid, and an agent can't stay willfully ignorant to bid high).

The payoff: sensing costs energy (battery + budget), so **how much to observe becomes an
economic decision** — bounded rationality extended from cognition to *sensing*
(see [single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md)). Guard: a
**constitutional cadence floor** — autonomy over attention, but never the freedom to sleep
through a drought and rot.

# 4. Authored-by follows region want, not subject

**"About X" ≠ "authored by X."** A fact an agent has a region want in is authored by the region-want-free
holder of that power:

| Fact | About | Authored by | Why not the agent |
|---|---|---|---|
| moisture | the plant | **gateway** (witness) | it would report bone-dry |
| wallet balance / debits | the agent | **clearing** (the mint) | it would print money |
| win record | the agent | **clearing** (outcomes) | it would inflate its wins |
| private beliefs / learning / self-view | the agent | **the agent** | nothing to gain by faking its own opinion |

The agent authors only what it cannot gain by faking. Its self-metrics are welcome but
**untrusted** — solvency is checked against the mint's own record, never against a self-report.
Provenance and write-scope distinguish them. (This said *like `:claims`*, naming a graph for
untrusted peer assertions that was never built and never needed: a bid is a message on the bus,
weighed and discarded — see [belief-base](/domain/belief-base.md).)

# The economy is a clearing-authored time series

The two-store pattern (**RDF current-state + Influx history**) is *general*, not
gateway-specific — every writer uses it for its own scope:

```
agent → what it read      → :sensed             (RDF) + influx   [its own, as opinion]
agent → what it concludes → :classification     (RDF) + influx   [band, verdict]
agent → what it holds     → :picks/<agent>      (RDF) + influx   [picks, wallet, own scope]
```

**AMENDED — the writers collapsed into one.** This block read `gateway → :attested/<plant>`,
`clearing → :ledger` and `agent → :exp/<agent>`, three authorities with three graphs, and none of
those three graph names was ever built.
[trusted-agent-mode](/decisions/trusted-agent-mode.md) dropped the witness and
[where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md) dropped the shared store,
so there is one writer per agent and its own base. **The two-store pattern itself is unchanged**,
which was this section's actual claim: RDF holds current state, Influx holds the series, and every
writer uses both for its own scope.

So you can watch the *society* evolve (wallet, win-rate, water received over time), not just
soil moisture.

# Observability — sovereign god-view

Minimal disclosure is **agent-to-agent**: fern never sees tomato's wallet. But the
**sovereign** (operator) sees everything — so the economy dashboard is a sovereign-level
view. Private among peers, transparent to the sovereign.

# The one principle

Push **judgment, data, and initiative** to the agent; keep infra a **thin honest mechanism**;
**author by region want**; **disclose need-to-know**; **observe via the sovereign**. Every
correction above is one face of this.

# v1 vs the target

Recorded ahead of the code; the code has since caught up in part.

**Done.** The band is the agent's (§1) — computed from its charter, gateway decommissioned
(see [trusted-agent-mode](/decisions/trusted-agent-mode.md)). Sensing is agent-timed (§3): the
firmware is a `sense`/`sleep` service, and the *agent* now drives it — it sets the cadence
from its own urgency and nudges for a reading before it bids. The guard that pull requires
came with it: a bid must cite a **fresh-enough** reading or the agent sits the round out, and
the cadence floor is clamped on both sides of the wire. See [sensing](/domain/sensing.md).

**Not yet.** Sensing is *initiated* by the agent but not **priced** — no wallet debit per
`sense`, so "how much to observe" is not yet the economic decision §3 promises; that waits on
[single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md). Disclosure (§2) is
still coarse: one shared `:sensed` graph rather than per-plant private scopes — nothing yet
*enforces* that a peer can't read fern's moisture. And the ledger (§4) is not yet
clearing-authored. Those remain the v2 epistemics/observability work; the principle stays
pinned so the rest can follow without re-litigation.
