---
type: Component
title: Belief base
description: Named-graph layout, SOSA observations, provenance, the two-store split.
tags: [rdf, fuseki, influxdb, sosa, provenance]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

The knowledge substrate. Two stores by role, joined by plant URI. See
[two-store-beliefs](/decisions/two-store-beliefs.md).

- **InfluxDB** — the series (record): every reading, history, trends.
- **Fuseki (RDF/TDB2)** — current qualitative state + structure (citable beliefs).

# There is no shared knowledge — only testimony + private belief

The one triplestore is *storage*, not a shared mind. Epistemically there is no "shared
belief base": there is the gateway's **attested testimony** — a signed public record, like a
village land registry or the court's admissible evidence — plus **each agent's private
beliefs**. The record is authoritative by **institutional convention** (the leash: a
justification may cite only `:attested`), not because it is metaphysical truth; the sensor
could be wrong. What agents share is a *reference to the same measurement*, so they never
argue about whether the sensor read 0.18 — but what it *means* and what to *do* is private
and expected to diverge. That divergence is the point of deliberation (see
[round](/domain/round.md)). The named graphs below encode exactly this: one witness of
record, plus private assumptions, plus untrusted claims.

Two kinds of belief arise differently: **state** (current moisture) is *sensed* by the
gateway, continuously; **structure + identity** (topology, charters) is *authored* once by
the sovereign and amended over time — it cannot be sensed. See
[genesis](/decisions/genesis.md).

# Named graphs — partitioned by TRUST, not topic

The graph name IS the trust tier — it is the write-authorization boundary, so "can this be
cited" is a mechanical membership check (PROV-O then records *which* witness inside it; see
below on why the graph, not the provenance triple, carries the trust):

- `:ontology` — the shared **T-Box** (`ontology/agora.ttl`): classes and properties (World,
  WorldVersion, Plant, Band, servedBy…). The vocabulary agents read from context.
- `:structure` — the sovereign-authored **durable structure**: topology (`servedBy` /
  `suppliedBy`), charters (`hasTarget`), the current world version. Written by genesis, not
  sensed. See [genesis](/decisions/genesis.md).
- `:attested` — the **witness of record**: sensor/forecast-witnessed current *state*,
  gateway-signed, **agent-read-only**, stamped `underWorldVersion`. The ONLY graph a
  justification may cite. Forecast lives here too (tense in the timestamp).
- `:exp/<agent>` — an agent's **private beliefs / assumptions**, its own learning. Per-agent,
  **not shared** (if shared it becomes forgeable and trolls exploit it — the same reason
  there is no shared knowledge, only testimony).
- `:claims` — what agents assert during negotiation. Untrusted; never merged into `:attested`.

The graphs themselves are **typed, self-describing resources** (`:attested a
agora:AttestedGraph ; agora:witness agora:gateway`) — a graph catalog, not magic strings.
Structure (durable, authored) is kept out of `:attested` (sensed, overwritten): different
origins, different graphs. See [genesis](/decisions/genesis.md).

Everything meaningful is a **named** graph so it can carry provenance. The default (unnamed)
graph carries no provenance, so nothing load-bearing goes there. See
[trust-boundary](/decisions/trust-boundary.md).

# Why a named graph — and why (for now) one

The graph is a **write-authorization boundary, not a label.** Citability can't rest on a
`prov:wasGeneratedBy :gateway` *triple* — a triple is forgeable by anyone who can write, so
a troll would just self-stamp its own claim. Trust comes from **who may write the
container**, not from a stamp inside it. `:attested` is the graph only the gateway writes;
"citable?" is therefore *membership in a container you cannot write*, which no rhetoric or
forged triple can fake. (The village registry is trusted because only the registrar may
write the book — not because each entry says "signed, the registrar.") The two things are
distinct and both wanted: the **graph** = the lock (who may write); the
`prov:wasGeneratedBy` **triple** = the logbook entry (which sensor produced it).

The **singleton is a v1 artifact of having one witness** (one gateway, one sensor per
plant). The natural unit is **one graph per witness**: add independent sensors or oracles
and you get `:attested/<witness>` graphs that may disagree, with agents forming beliefs by
*weighing witnesses* — "different assumptions about the same facts" pushed up to the record
itself. Nothing is welded to there being exactly one; v1 just has one. Private beliefs
(`:exp/<agent>`) are already per-agent; only the *current consensus record* is singleton,
and in v1 it collapses to the sole witness's output.

# Access languages (deliberate asymmetry)

- Cite a fact → LLM-**composed SPARQL** on `:attested` (read-only, small, safe — looser leash).
- Need history/trend → **typed Influx functions** with fixed Flux, LLM fills params only
  (high-volume quantitative path — tighter leash). Never NL→Flux, never raw LLM Flux.
- Need both → agent code queries each and **joins on the URI**. No federation layer.

# SOSA

Observations use SOSA on the sensor edge (see [gateway](/domain/gateway.md)); the political
vocabulary (wallet, bid, desire) stays in a lean custom ontology — SOSA models observation,
not negotiation.
