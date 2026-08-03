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
moisture) is *sensed* by each agent's own sensor (see [sensing](/domain/sensing.md)).
**Structure + identity** (topology, wiring) is *durable* and must be *authored* — it cannot
be sensed.
Where does that come from, and — since no one describes a world correctly the first time —
how is it corrected later?

# Decision — genesis is a sovereign act, LLM-assisted

Structure and identity are seeded by **genesis**, a sovereign act in four steps:

1. **Narrate** — the sovereign describes the world in English (plants, sources, who feeds
   whom, quirks, desires).
2. **Draft** — the LLM proposes a *formal* world: the topology graph (`:fern :servedBy
   :barrel1`, `:fern_agent :polls :moisture_sensor_fern` …) and each agent's opening
   beliefs (target, bands, cadence, valuation). The LLM is a **drafting assistant, not an
   agent** — no stake, proposes only.
3. **Ratify** — the sovereign reviews, edits, accepts. Only the sovereign authors the world
   (see [constitution](/domain/constitution.md): only the sovereign amends).
4. **Write** — the ratified draft is Turtle in `genesis/<world>/`, and `agora-seed <world>`
   PUTs it: the wiring into `:world` (which agents read but never rewire), each agent's
   opening beliefs into its own `:beliefs/<agent>` (which it alone may revise). The sovereign
   authors the world in the same vocabulary the agents read — no config file, no translation
   layer. See [world-graph](/decisions/world-graph.md).

# A genesis output is a whole world, and there may be several

`genesis/` holds **one directory per ratified world**, each complete and seedable on its own —
not a base with fragments layered on it. `agora-seed <name>` loads exactly one.

This matters more than convenience. A world is the *entire* model of a system, so a second one
is not a variant of the first: it is a different society. `genesis/society` has a market;
`genesis/sensing` has one subject, one board and one agent and no market at all — which makes
it the smallest genesis output that still produces a working agent, and the proof that a
capability can stand alone. If `ag:Bidding` could only exist alongside perception, "capability"
would be a word for a bundle.

The two ship with **identical device ids and channels**, so one flashed board runs in either.
Which world is in the store decides whether its agent merely watches or also buys. That is the
model-driven claim reduced to something you can check by re-seeding.

# Agents are born from the world

Nothing lists the agents to run. `agora-up` asks the belief base `?a a ag:Agent` and starts one
process per answer, handing each the single thing an agent is ever told: its own id. The roster
*is* the ratified world, so adding an agent is adding it to `world.ttl` — no unit file, no
launcher edit, and no place for a list to drift from the model.

One OS process each, and that is not an implementation detail: the process boundary is what
makes one agent unable to read another's beliefs, and it is why a round had to become a
protocol rather than a calculation (see
[capability-packages](/decisions/capability-packages.md)). Supervision must not undo it.

**Firmware is the exception, and the contrast is the point.** A board is hardware; it is
flashed by hand and the model cannot conjure it. What genesis decides is what an *agent* is —
which is exactly why the same board is a watcher in one world and a bidder in another.

This is [english-vs-formal](/decisions/english-vs-formal.md) applied to *creation*: the story
is fuzzy human intent (English); the ratified structure is trusted formal.

# Genesis vs sensing — each belief has one origin

- **State** ← sensing, continuous. You cannot narrate the moisture.
- **Topology / identity** ← genesis (narrate → draft → ratify), durable. You cannot sense who
  is plumbed to what.
- **Desire / limits** ← genesis *seeds* them, then they are the agent's own to revise. Opening
  beliefs, not permanent law.

They never mix. See [belief-base](/domain/belief-base.md).

# Config is ratified belief, owned by a party

What looks like flat config is the *ratified output* of genesis, and each fact has an owner:

- **topology / wiring / device calibration** → the **`:world`** graph (sovereign-declared;
  agents read, never rewire — see [market](/domain/market.md)).
- **target / endowment / value curve** → each agent's own **`:beliefs/<agent>`** (internal to
  the agent — see [agent](/domain/agent.md)).
- **bands / cadence / freshness limit** → also the agent's: desire-relative judgments, not
  ground truth (see [agent-centric-epistemics](/decisions/agent-centric-epistemics.md)).
- **quantity / reserve / cooldown** → the **supplier's** own beliefs — its strategy.
- **tank capacity** → `:world`, on the source: a physical fact, and the constitution's
  allocation ceiling.

Splitting by owner keeps the epistemics honest — no shared knowledge, only testimony +
private belief. That split is now literal: it is which *graph* the triple lives in, and
there is no config file left over. See [world-graph](/decisions/world-graph.md).

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

- **The world graph carries it as identity** — the ratified topology *is* world-vN.
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

v1: an `agora:versionNumber` bumped by hand in `genesis/world.ttl` when the sovereign edits
it and re-seeds; every recorded observation is stamped with it. Archiving prior versions and
the diff/migration tooling are v2/v3.

# The line that protects trust: structure mutable, history immutable

Amendment changes the **current world and go-forward beliefs**. It must **never**
retro-edit **testimony/history** — past attestations (with their timestamps) and the Influx
series are the *record of what happened*, append-only. You may change what the world **is**,
never what it **was**. That is what keeps the witness of record trustworthy. See
[belief-base](/domain/belief-base.md) and [trust-boundary](/decisions/trust-boundary.md).

# v1 vs v2

v1 **hand-authors** the ratified output — Turtle in `genesis/`, split by owner into the world
and one file per agent — and skips the narrator; amendment in v1 = edit those files and
re-seed. The narrate → draft → ratify LLM tool, version archiving, and typed migrations are
**v2/v3 onboarding** work. Because the ratified output is already *belief in the agents' own
vocabulary*, building the narrator later changes nothing downstream: it just writes the same
Turtle. See [roadmap](/decisions/roadmap.md).
