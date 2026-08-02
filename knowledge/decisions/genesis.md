---
type: Decision
title: Genesis — how a world is born and amended
description: The sovereign narrates, the LLM drafts, the sovereign ratifies; genesis is versioned and amendable — structure is mutable while history stays immutable.
status: accepted
stage: v1
tags: [genesis, sovereign, bootstrapping, amendment, provenance]
timestamp: 2026-08-02T00:00:00Z
---

# Context

The belief base holds two kinds of belief that arise differently. **State** (current
moisture) is *sensed* continuously by the [gateway](/domain/gateway.md). **Structure +
identity** (topology, charters) is *durable* and must be *authored* — it cannot be sensed.
Where does that come from, and — since no one describes a world correctly the first time —
how is it corrected later?

# Decision — genesis is a sovereign act, LLM-assisted

Structure and identity are seeded by **genesis**, a sovereign act in four steps:

1. **Narrate** — the sovereign describes the world in English (plants, sources, who feeds
   whom, quirks, desires).
2. **Draft** — the LLM proposes a *formal* world: the topology graph
   (`:fern :servedBy :barrel1` …), charters (targets, endowments, quirks), starting
   thresholds. The LLM is a **drafting assistant, not an agent** — no stake, proposes only.
3. **Ratify** — the sovereign reviews, edits, accepts. Only the sovereign authors the world
   (see [constitution](/domain/constitution.md): only the sovereign amends).
4. **Write** — trusted infra materializes the ratified draft as **attested structure** +
   **signed charters**. Agents read it; they never author it.

This is [english-vs-formal](/decisions/english-vs-formal.md) applied to *creation*: the story
is fuzzy human intent (English); the ratified structure is trusted formal.

# Genesis vs sensing — each belief has one origin

- **State** ← sensing (gateway), continuous. You cannot narrate the moisture.
- **Structure / identity** ← genesis (narrate → draft → ratify), durable. You cannot sense a
  charter.

They never mix. See [belief-base](/domain/belief-base.md).

# Config is ratified belief, owned by a party

What looks like flat config is the *ratified output* of genesis, and each fact has an owner:

- **topology / species** → attested **structure** (sovereign-declared; agents read, never
  rewire — see [market](/domain/market.md)).
- **target / endowment / quirks** → each agent's **charter** + private `:exp` (internal to
  the agent — see [agent](/domain/agent.md)).
- **bands / thresholds** → the **gateway's** judgment authority (not an agent belief).
- **quantity / reserve / tank** → the **supplier's** strategy.

Splitting by owner keeps the epistemics honest — no shared knowledge, only testimony +
private belief.

# Genesis is repeatable and amendable

No one describes a world correctly the first time, so genesis is **not one-shot**:

- **Declarative reconciliation** — the sovereign narrates the *desired* world (or a change to
  it); the system computes the **delta** from the current world and proposes a *migration*,
  not a from-scratch rebuild.
- **Versioned + provenance-stamped** — each ratification is a new world-version (see
  *Versioning* below), like a constitutional amendment or a git commit. The genesis history
  is itself an auditable record.
- **Sovereign-only** — amendment is the same authority as amending the constitution.
- **Migrations typed by disruptiveness** — *additive* (new plant/source: safe), *tuning*
  (adjust a target/threshold: safe-ish), *structural* (move a plant to a new source:
  recompute its cluster), *destructive* (remove a plant: what becomes of its wallet, its
  commitments?). The system **proposes the consequences**; the sovereign ratifies with eyes
  open.
- **Evidence can prompt amendment** — the system may *suggest* amendments from observed
  behaviour ("the fern keeps hitting rot at your stated target — lower it?"). A suggestion is
  a proposal; the sovereign still ratifies.

# Versioning — a monotonic world-version

Concretely: a single monotonic **world-version**, incremented on each manual (re-)genesis or
amendment. It is used two ways, and the distinction matters:

- **Structure carries it as identity** — the ratified topology + charters *are* world-vN.
  When amended, the new structure is written as v(N+1) and the prior version is kept as an
  **immutable snapshot**, not overwritten. The sequence of versions is append-only.
- **State references it as provenance** — each runtime attestation (a moisture reading)
  stamps *"sensed under world-vN"*. The reading still versions by its **timestamp** (it is a
  time series); the world-version records *which structure was in force* when it was recorded,
  so history stays interpretable after an amendment.

Do **not** version the sensed value *by* genesis — moisture changes for reasons unrelated to
the world's structure. Version the structure; reference it from state.

This is what mechanically reconciles the line below: the world is **event-sourced** —
amendments append a version, the version chain never mutates, and the "current" world is a
projection of the latest. Rollback is a *forward* amendment (re-ratify an old version as the
new current), never an edit of the past.

v1: a `world_version` integer bumped by hand when the sovereign edits the config and
re-seeds; the [gateway](/domain/gateway.md) stamps each attestation with it. Archiving prior
versions and the diff/migration tooling are v2/v3.

# The line that protects trust: structure mutable, history immutable

Amendment changes the **current structure and go-forward charters**. It must **never**
retro-edit **testimony/history** — past attestations (with their timestamps) and the Influx
series are the *record of what happened*, append-only. You may change what the world **is**,
never what it **was**. That is what keeps the witness of record trustworthy. See
[belief-base](/domain/belief-base.md) and [trust-boundary](/decisions/trust-boundary.md).

# v1 vs v2

v1 **hand-authors** the ratified output (config files split by owner) and skips the narrator;
amendment in v1 = edit the config and re-seed. The narrate → draft → ratify LLM tool, the
world-versioning, and typed migrations are **v2/v3 onboarding** work. Because config is
already treated as *ratified belief*, building the narrator later changes nothing
downstream. See [roadmap](/decisions/roadmap.md).
