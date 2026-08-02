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
- **Versioned + provenance-stamped** — each ratification is a new world-version
  (`world v2 ratified by :sovereign at T1 from story S1`), like a constitutional amendment or
  a git commit. The genesis history is itself an auditable record.
- **Sovereign-only** — amendment is the same authority as amending the constitution.
- **Migrations typed by disruptiveness** — *additive* (new plant/source: safe), *tuning*
  (adjust a target/threshold: safe-ish), *structural* (move a plant to a new source:
  recompute its cluster), *destructive* (remove a plant: what becomes of its wallet, its
  commitments?). The system **proposes the consequences**; the sovereign ratifies with eyes
  open.
- **Evidence can prompt amendment** — the system may *suggest* amendments from observed
  behaviour ("the fern keeps hitting rot at your stated target — lower it?"). A suggestion is
  a proposal; the sovereign still ratifies.

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
