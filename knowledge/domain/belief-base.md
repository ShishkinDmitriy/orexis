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

# Named graphs — partitioned by TRUST, not topic

The graph name IS the trust tier (provenance via PROV-O makes "can this be cited" a
mechanical check):

- `:attested` — sensor/forecast-witnessed current state, gateway-signed, **agent-read-only**.
  The ONLY graph a justification may cite. Forecast lives here too (tense in the timestamp).
- `:exp/<agent>` — an agent's own private learning. Per-agent, **not shared** (if shared it
  becomes forgeable and trolls exploit it).
- `:claims` — what agents assert during negotiation. Untrusted; never merged into `:attested`.

Everything meaningful is a **named** graph so it can carry provenance. The default (unnamed)
graph carries no provenance, so nothing load-bearing goes there. See
[trust-boundary](/decisions/trust-boundary.md).

# Access languages (deliberate asymmetry)

- Cite a fact → LLM-**composed SPARQL** on `:attested` (read-only, small, safe — looser leash).
- Need history/trend → **typed Influx functions** with fixed Flux, LLM fills params only
  (high-volume quantitative path — tighter leash). Never NL→Flux, never raw LLM Flux.
- Need both → agent code queries each and **joins on the URI**. No federation layer.

# SOSA

Observations use SOSA on the sensor edge (see [gateway](/domain/gateway.md)); the political
vocabulary (wallet, bid, desire) stays in a lean custom ontology — SOSA models observation,
not negotiation.
