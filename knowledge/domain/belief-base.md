---
type: Component
title: Belief base
description: One belief base per agent, not one shared store — named-graph layout, SOSA observations, provenance, and the split between the series and the graph.
tags: [rdf, influxdb, sosa, provenance, isolation]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

The knowledge substrate. Two stores by role, joined by subject URI. See
[two-store-beliefs](/decisions/two-store-beliefs.md).

- **InfluxDB** — the series (record): every reading, history, trends. Shared.
- **An embedded quad store, one per agent** — the world (topology) as of the version that agent
  booted with, the vocabulary, its own beliefs, and its own sensed state.

**There is no shared triplestore.** Each agent holds its own belief base as a file inside its
own container, built at boot from the ratified Turtle in `genesis/<world>/`. Nothing else can
open it — not another agent, not an operator. Isolation is therefore *structural*: an agent's
store contains only what it may see, so there is nothing to enforce, no credential to issue and
no access registry to keep in step. See
[where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md); the mechanism it
replaced is recorded in [belief-base-isolation](/decisions/belief-base-isolation.md).

The consequence worth stating plainly: **you cannot query "the belief base"**, because there
isn't one. There are N, and each is private to its holder — which is what the design always
claimed epistemically, now made true mechanically rather than by convention.

# There is no shared knowledge — only testimony + private belief

There is no shared mind, and now no shared store either. Epistemically there is the **public
record** — the world's wiring, ratified as files and copied into every agent, like a village
land registry or the court's admissible evidence — plus **each agent's private beliefs**, which
never leave it. The record is authoritative by **institutional convention** (the leash: a
justification may cite only what is on the record), not because it is metaphysical truth; the
sensor could be wrong. What agents share is a *reference to the same measurement*, so they never
argue about whether the sensor read 0.18 — but what it *means* and what to *do* is private
and expected to diverge. That divergence is the point of deliberation (see
[round](/domain/round.md)). The named graphs below encode exactly this: one public record
(wiring + measurements), plus per-agent private belief, plus untrusted claims.

Three kinds of belief arise differently, and each gets its own home: **state** (current
moisture) is *sensed*, continuously; **topology** (who is wired to what) is *authored* once by
the sovereign and amended by re-genesis — it cannot be sensed; **desire and limits** (what an
agent wants, what it counts as too dry, how closely it watches) are *held* by each agent as
its own revisable opinion. Confusing the last two is what a config file does. See
[genesis](/decisions/genesis.md) and [world-graph](/decisions/world-graph.md).

# Named graphs — partitioned by TRUST, not topic

The graph name IS the trust tier — it is the write-authorization boundary, so "can this be
cited" is a mechanical membership check (PROV-O then records *which* witness inside it; see
below on why the graph, not the provenance triple, carries the trust):

- `:ontology` — the shared **T-Box**, merged from every package's `ontology.ttl`
  (`kernel/`, each `capabilities/*/`, `transports/*/`, `domain/*/`): classes and properties (World,
  Agent, Sensor, Valve, Plant, Band, servedBy…). The vocabulary agents read from context.
- `:world` — the sovereign-authored **topology**, and *only* topology: which agent acts for
  which plant, which sensors it is wired to (`polls` — the access grant), which valve
  waters what, which source supplies it, plus the physical facts about that hardware
  (calibration, capacity, drying rate) and the current world version. Public: every agent
  reads all of it. It exists so the wiring is stated **once** instead of being repeated in
  every agent's beliefs. Written by genesis, not sensed. Nothing interpretive lives here —
  no targets, no bands, no cadence, no prices. See [world-graph](/decisions/world-graph.md).
- `:beliefs/<agent>` — one agent's **private opinion**: its desire (`hasTarget`), its comfort
  limits (`bandLow`/`bandHigh`), its sensing cadence and freshness limit, its value curve.
  Per-agent, not shared; two agents may hold different numbers about the same plant and
  neither is wrong.
- `:sensed` — current *state*: what each sensor read, stamped `underWorldVersion` and carrying
  its `resultTime` (which is what the freshness gate checks). In an adversarial society this
  is the witness of record and the only graph a justification may cite; in v1's trusted-agent
  mode it is self-asserted (see below). Forecast lives here too (tense in the timestamp).
- `:claims` — what agents assert during negotiation. Untrusted; never merged into `:sensed`.

The graphs themselves are **typed, self-describing resources** (`:world a agora:WorldGraph`,
`:beliefs/fern a agora:BeliefsGraph ; agora:beliefsOf agora:fern_agent`) — a graph catalog,
not magic strings. Topology (durable, authored) is kept out of `:sensed` (sensed, overwritten)
and out of the belief graphs (opinion, revisable): three origins, three kinds of graph. See
[genesis](/decisions/genesis.md) and [world-graph](/decisions/world-graph.md).

**Authored by stake, disclosed need-to-know** (see
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md)). Per-agent belief graphs
are already in place; the remaining scoping work is:
- `:sensed/<plant>` — the plant's own measurement, **private / need-to-know** (peers never
  read it; the constitution and the plant do). Moisture is the plant's business; the market
  needs its *bid*, not its moisture. Today `:sensed` is still one shared graph.
- `:ledger` — wallet balances, debits, and grants, **authored by clearing** (the mint), not
  by the agents they are *about* ("about X" ≠ "authored by X").
- `:beliefs/<agent>` — done: the agent's private desire and limits, and later its learning
  *and* its own (untrusted) self-metrics.

**Reads are enforced.** The store holds a per-graph access list keyed to per-agent
credentials, generated from the world, so an agent connecting as itself sees the shared graphs
and its own beliefs and nothing else — another agent's beliefs come back empty rather than
refused. Writes are *not* graph-scoped (the store cannot), which is the same
integrity-of-self-report assumption trusted-agent mode already accepts. The bus is a separate
question and is still open. See [belief-base-isolation](/decisions/belief-base-isolation.md).

Every writer uses the two stores (RDF current-state + Influx history) for its own scope; the
**sovereign** reads all of it for observability.

**Trusted-agent mode** (v1, see [trusted-agent-mode](/decisions/trusted-agent-mode.md)):
there is no witness — each plant asserts its own state, and measurement stays separate from
judgment by living in a different graph:
- `:sensed` — the agent's **sensor data** (`hasSimpleResult 0.18`), `prov:wasGeneratedBy` the
  plant. What it read.
- `:beliefs/<agent>` — the agent's **judgments and dispositions** (its band limits, target,
  valuation, and later its learning). What it concludes and what it wants.

So "fern *read* 0.18" and "fern *thinks* 0.35 is too dry" stay distinct, auditable facts. The
band itself is never stored at all — it is recomputed from the two whenever it is needed.
Re-introducing a witness (a signing sensor) for an adversarial society moves the provenance
back to the device; the graphs are unchanged.

Everything meaningful is a **named** graph so it can carry provenance. The default (unnamed)
graph carries no provenance, so nothing load-bearing goes there. See
[trust-boundary](/decisions/trust-boundary.md).

# Why a named graph

The graph is a **write-authorization boundary, not a label.** Citability can't rest on a
`prov:wasGeneratedBy :gateway` *triple* — a triple is forgeable by anyone who can write, so
a troll would just self-stamp its own claim. Trust comes from **who may write the
container**, not from a stamp inside it. `:world` is the graph only the sovereign writes and
`:beliefs/fern` the one only fern writes; "citable?" is therefore *membership in a container
you cannot write*, which no rhetoric or
forged triple can fake. (The village registry is trusted because only the registrar may
write the book — not because each entry says "signed, the registrar.") The two things are
distinct and both wanted: the **graph** = the lock (who may write); the
`prov:wasGeneratedBy` **triple** = the logbook entry (which sensor produced it).

The graph names survive the move to per-agent stores unchanged, and the reasoning above is why:
they were never about *partitioning one server*, they were about who may write a container. In
an agent's own store the boundary is doubly held — `:world` is replaced from the ratified files
on every start and is not the agent's to author, while `:beliefs/<agent>` is written once at
birth and is the agent's alone thereafter.

The **`:sensed` singleton is a v1 artifact of having one sensor per subject**. The natural unit
is **one graph per witness**: add independent sensors or oracles and you get `:sensed/<witness>`
graphs that may disagree, with agents forming beliefs by *weighing witnesses* — "different
assumptions about the same facts" pushed up to the record itself. Nothing is welded to there
being exactly one. The world is deliberately singular *as a document* — every agent holds the
same ratified copy — because a world agents disagreed about would defeat the point of stating
the wiring once.

# Access languages (deliberate asymmetry)

- Cite a fact → LLM-**composed SPARQL** on `:world` / `:sensed` (read-only, small, safe — looser leash).
- Need history/trend → **typed Influx functions** with fixed Flux, LLM fills params only
  (high-volume quantitative path — tighter leash). Never NL→Flux, never raw LLM Flux.
- Need both → agent code queries each and **joins on the URI**. No federation layer.

# SOSA

Observations use SOSA on the sensor edge, and the devices themselves are SOSA too:
`agora:Sensor` is a `sosa:Sensor`, `agora:Valve` a `sosa:Actuator`, and a plant a
`sosa:FeatureOfInterest`. The political vocabulary (wallet, bid, desire, cadence) stays in a
lean custom ontology — SOSA models observation, not negotiation. See
[sensing](/domain/sensing.md).
