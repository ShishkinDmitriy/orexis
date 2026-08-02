---
type: Decision
title: Two stores — Influx for series, Fuseki for citable state
description: Time-series and RDF split by role, joined by plant URI, never federated.
status: accepted
stage: v1
tags: [belief-base, influxdb, rdf, sosa]
timestamp: 2026-08-01T00:00:00Z
---

# Decision

- **InfluxDB owns the *series*** — every raw reading, full history, trends, rate-of-change.
- **Fuseki (RDF) owns the *current qualitative state* and structure** — `plant :hasCurrentMoisture :LOW`,
  species, tank-sharing. Low-volume, queryable, provenance-tagged, reasoned-over. The
  tank-sharing / plumbing topology here *is* the market-cluster boundary — who competes with
  whom. See [market](/domain/market.md).
- The two are **joined by the plant URI in code**, not by any SPARQL-over-Influx federation
  (no such thing should be built — it re-creates the triple-count wall).

# Why

- Modelling millions of timestamped readings as triples kills the store and the reasoner.
- OWL/SHACL reason over *state and structure*, never over the time-series. History is queried
  from Influx directly (body-plumbing every forecasting agent has).

# Access rules

- Cite a fact → LLM-composed **SPARQL** on `:attested` (read-only, small, safe).
- Need a trend → **typed Influx function** (fixed Flux, LLM fills params only). Tighter leash
  on the high-volume quantitative path. See [belief-base](/domain/belief-base.md).

# The one seam to get right

Only the **measurement** must be single-authored — the [gateway](/domain/gateway.md) signs
`0.18` so nobody argues about the number. The numeric→qualitative *band* (0.18 → `:LOW`) is
**not** ground truth: it is desire-relative, so it is **per-agent private judgment**, not a
gateway authority. (An earlier version put the threshold in the gateway "or agents disagree
about ground truth" — that conflated measurement with judgment; agents *are supposed* to
disagree about what a reading means.) See
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md).

Note the two-store pattern (RDF current-state + Influx history) is **general** — the gateway,
clearing, and agents each use it for their own scope, scoped by who may author.
