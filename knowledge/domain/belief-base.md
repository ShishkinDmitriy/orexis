---
type: Component
title: Belief base
term: http://example.org/agora#BeliefBase
description: One belief base per agent, not one shared store — named-graph layout, SOSA observations, provenance, and the split between the series and the graph.
---

# What it is

The knowledge substrate. Two stores by role, joined by subject URI. See
[two-store-beliefs](/decisions/two-store-beliefs.md).

- **InfluxDB** — the series (record): every reading, history, trends. Shared.
- **An embedded quad store, one per agent** — the world (topology) as of the version that agent
  booted with, the vocabulary, its own beliefs, and its own sensed state.

**There is no shared triplestore.** Each agent holds its own belief base as a file inside its
own container, built at boot from the ratified Turtle in `world/<world>/`. Nothing else can
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
  (`packages/core/agora/` and every `packages/<family>/<name>/`): classes and properties (World,
  Agent, Sensor, Valve, Plant, Band, servedBy…). The vocabulary agents read from context.
- `:world` — the sovereign-authored **topology**, and *only* topology: which agent acts for
  which plant, which sensors it is wired to (`polls` — the access grant), which valve
  waters what, which source supplies it, plus the physical facts about that hardware
  (calibration, capacity, drying rate) and the current world version. Public: every agent
  reads all of it. It exists so the wiring is stated **once** instead of being repeated in
  every agent's beliefs. Written by genesis, not sensed. Nothing interpretive lives here —
  no targets, no bands, no cadence, no prices. See [world-graph](/decisions/world-graph.md).
- `:beliefs/<agent>` — one agent's **private opinion**: its aim (`ag:aims`), its sensing cadence
  and freshness limit, its value curve. Its comfort limits are NOT here — those are the region
  its subject states, deduced and public.
  Per-agent, not shared; two agents may hold different numbers about the same plant and
  neither is wrong.
- `:sensed` — current *state*: what each sensor read, stamped `underWorldVersion` and carrying
  its `resultTime` (which is what the freshness gate checks). In an adversarial society this
  is the witness of record and the only graph a justification may cite; in v1's trusted-agent
  mode it is self-asserted (see below). Forecast lives here too (tense in the timestamp).
- What agents assert during negotiation is untrusted and is never merged into `:sensed`.
  There is no `:claims` graph — a bid is a message on the bus, weighed and discarded, and
  what survives a round is the co-signed claim rather than the assertions that produced it.

**And that is five of them.** The list above is the original trust partition and is no longer
the whole store: the mind grew a graph per modality, and provenance grew one per arrival. The
full set is whatever `ag:Graph` has instances of — ask, never count — but for orientation it is
now `graph/beliefs/<agent>`, `graph/sensed`, `graph/world`, `graph/world/derived`,
`graph/world/entailed`, `graph/ontology`, `graph/ontology/entailed`, `graph/provenance`,
`graph/desire`, `graph/constraint`, `graph/intentions/<agent>`, `graph/obligations/<agent>`,
`graph/deliberation`, `graph/effects`, `graph/evidence/<agent>`, `graph/revisions/<agent>`,
`graph/summaries/<agent>`, `graph/classification` and `graph/instruments`. See
[the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) for the three axes that classify
them and [who-put-the-fact-there](/decisions/who-put-the-fact-there.md) for why the public ones
split by who authored the fact. Two caveats as
[a-store-is-a-modality](/decisions/a-store-is-a-modality.md) is carried out: the desire-modality
graphs are also served from the desires store's rebuilt copy, which is what deliberation reads;
and `graph/intentions/<agent>` has moved OUT of a deployed belief base into the intention
modality's own room of the volume (`<state>/intentions`, beside `<state>/belief-base`) — a
pathless test mind keeps it here, exactly as pre-split volumes did.

The graphs themselves are **typed, self-describing resources** (`:world a agora:WorldGraph`,
`:beliefs/fern a agora:DesireGraph ; agora:beliefsOf agora:fern_agent` — the pick record, typed by its modality since `ag:BeliefsGraph` retired) — a graph catalog,
not magic strings. Topology (durable, authored) is kept out of `:sensed` (sensed, overwritten)
and out of the belief graphs (opinion, revisable): three origins, three kinds of graph. See
[genesis](/decisions/genesis.md) and [world-graph](/decisions/world-graph.md).

**Authored by stake, disclosed need-to-know** (see
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md)). Per-agent belief graphs
are already in place; the remaining scoping work is:
- `:sensed/<plant>` — the plant's own measurement, **private / need-to-know** (peers never
  read it; the constitution and the plant do). Moisture is the plant's business; the market
  needs its *bid*, not its moisture. Today `:sensed` is still one shared graph.
- a **ledger** — wallet balances, debits and grants, authored by clearing rather than by the
  agents they are *about*. It does not exist: there is no such graph and no mint, so a
  balance is self-reported and clearing checks solvency against the bidder's own number.
  See [wallet](/domain/wallet.md), which marks what is built apart from what is designed.
- `:beliefs/<agent>` — done: the agent's private desire and limits, and later its learning
  *and* its own (untrusted) self-metrics.

**Reads are isolated STRUCTURALLY, and no longer by the store.** An earlier design enforced
privacy with per-graph access lists behind per-agent credentials in a shared triplestore; there
is no shared store now. Each agent embeds its own, in a volume of its own, and is handed one
world and its own id — so another agent's beliefs are not refused, they are *absent*. Nothing
to be let into is a stronger guarantee than an ACL, and it is why
[belief-base-isolation](/decisions/belief-base-isolation.md) is superseded in mechanism while
its reasoning about why the graph is the write boundary still holds. See
[where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md).

The bus and the series store are the two places isolation still has to be *granted* rather than
being structural, and both are —  a credential and an ACL per principal, a bucket and a scoped
token per agent, all derived from the same wiring that derives capability. See
[series-and-bus-isolation](/decisions/series-and-bus-isolation.md).

Every writer uses the two stores (RDF current-state + Influx history) for its own scope; the
**sovereign** reads all of it for observability.

**Trusted-agent mode** (v1, see [trusted-agent-mode](/decisions/trusted-agent-mode.md)):
there is no witness — each plant asserts its own state, and measurement stays separate from
judgment by living in a different graph:
- `:sensed` — the agent's **sensor data** (`hasSimpleResult 0.18`), `prov:wasGeneratedBy` the
  plant. What it read.
- `:beliefs/<agent>` — the agent's **judgments and dispositions** (its aim, its valuation, its
  cadences, and later its learning). What it concludes and what it wants. Its band LIMITS are not
  here and have not been since the region was deduced rather than authored — see
  [band](/domain/band.md), which is the page that tells a stale mention from a live one.

So "fern *read* 0.18" and "fern *thinks* 0.35 is too dry" stay distinct, auditable facts.
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
birth and is the agent's alone thereafter — with one addition that is not a reset: an
amendment may grant a capability whose opening beliefs the volume has never held, and boot
**endows** those (never-held terms arrive with their structures, held terms stay the agent's
whatever their value; `rebirth` remains the explicit discard). See
[an-amendment-endows-what-it-grants](/decisions/an-amendment-endows-what-it-grants.md).

The **`:sensed` singleton is a v1 artifact**. Within it, an observation is keyed by its subject
*and the property observed*, so a pot with a moisture probe and a temp/humidity board holds
three current observations rather than one — see
[one-agent-many-sensors](../decisions/one-agent-many-sensors.md). What is still singular is the
graph, and the natural unit for that is **one per witness**: add independent sensors or oracles
that disagree *about the same property* and you get `:sensed/<witness>` graphs, with agents
forming beliefs by *weighing witnesses* — "different assumptions about the same facts" pushed up
to the record itself. Nothing is welded to there being exactly one.

The two are different axes and it is worth not confusing them: the key separates *different
questions about one pot*, and a per-witness graph would separate *different answers to the same
question*. Today the second case has no representation at all — two sensors on one property
share a node and the last writer wins, which the shapes flag as a warning rather than refuse. The world is deliberately singular *as a document* — every agent holds the
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
