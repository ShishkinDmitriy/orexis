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

The numeric→qualitative threshold (0.18 → `:LOW`) lives in exactly ONE place: the
[gateway](/domain/gateway.md), as part of attestation. Never per-agent, or agents disagree
about ground truth.
