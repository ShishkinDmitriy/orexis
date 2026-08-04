---
type: Domain Concept
title: World (a ratified genesis output)
description: What a world is made of — public topology plus one private beliefs file per agent — the three rules for authoring one, and what genesis derives rather than accepts. Several worlds coexist; which one is seeded decides what each agent becomes.
tags: [genesis, world, topology, derivation, authoring, capabilities]
timestamp: 2026-08-04T00:00:00Z
---

# What it is

A **world** is the complete model of one society: what exists, what is wired to what, and what
each agent privately wants. It is the ratified output of
[genesis](/decisions/genesis.md) — the sovereign narrates, an LLM drafts, the sovereign
ratifies — and each agent loads it at boot. The session that produces
one is [genesis-process](/domain/genesis-process.md).

Worlds are whole, not layered. `world/` holds one directory per world, each seedable on its
own; there is no base that variants extend.

```bash
agora-validate society  # plants, a market, a supplier, valves
agora-validate sensing  # one subject, one board, one agent
```

| | holds | derivation produces |
|---|---|---|
| `society/` | 3 plants + agents, a supplier, a barrel market, 3 valves | `Subscribing` + `Bidding` per plant agent; `Hosting` + `Actuation` for the supplier |
| `sensing/` | one subject, one board, one agent | `Subscribing`, and nothing else |

# Anatomy

```
world/<name>/
  world.ttl            public topology: what exists, and what is wired to what
  beliefs/<agent>.ttl  one per agent — its private parameters, its opinions
  secrets/             this society's signing keys (gitignored, never committed)
  compose.yaml        generated: one container per agent
```

A world is one self-contained directory. Nothing about it lives anywhere else, which is what
makes adding, copying or deleting one a single move.

That is all of it. There is no config file in this project; anything that looks like
configuration is either a fact about the world or somebody's belief, and lives in one of these
two files. See [world-graph](/decisions/world-graph.md) and [belief-base](/domain/belief-base.md).

# The three rules

## 1. State connections, never abilities

**`world.ttl` must not contain `ag:hasCapability`.** State what exists and what is plugged into
what; seeding runs each capability's `rules.ru` and derives what that wiring implies. This is
load-bearing: a declaration can drift from reality, a derivation cannot.

| you state | genesis derives |
|---|---|
| `ag:polls` a sensor whose `ag:senseMode` is `ag:Scheduled` | `ag:Subscribing` |
| `ag:polls` a sensor whose `ag:senseMode` is `ag:Push` | `ag:Listening` |
| `ag:bidsIn` a market | `ag:Bidding` |
| `ag:hosts` a market | `ag:Hosting` |
| `ag:hasActuator` anything that is a kind of `ag:Actuator` | `ag:Actuation` |

Reflash a board from `Push` to `Scheduled`, re-seed, and its agent gains an interval to state —
with no edit to the agent, because there is nothing about the agent to edit. See
[who-holds-the-clock](/decisions/who-holds-the-clock.md) for what those three sense modes mean.

The market rows are the **weakest** of these, and worth naming as such: `ag:bidsIn` says "is a
bidder" in other words, where `ag:senseMode` states a physical fact about hardware. Deriving
market roles from declared *goals* instead is an open seam — see below.

## 2. Every wire name is stated

No process builds a topic from a naming convention. A sensor states its own `ag:readingTopic`
and `ag:commandTopic`; a market states its three channels; the bus states its host and port. A
process is handed exactly one instance identifier — its own agent id — and discovers everything
else from it.

So renaming a channel is a genesis edit, and a board whose `PLANT_ID` disagrees with the world
simply never gets read. Nothing detects that for you.

## 3. Fact and opinion live in different files

`world.ttl` holds what everyone must agree on. `beliefs/<agent>.ttl` holds what that agent alone
thinks, and no other agent can read it — enforced, not polite
([belief-base-isolation](/decisions/belief-base-isolation.md)).

| | where | why |
|---|---|---|
| wiring, calibration, capacity | `world.ttl` | physical, public, stated once |
| target, band, endowment, price ceiling | `beliefs/<agent>.ttl` | desire — a fern and a succulent may disagree and neither is wrong |
| sleep intervals, freshness limit | `beliefs/<agent>.ttl` | how closely *this* agent chooses to watch |

If two agents could reasonably disagree about it, it is a belief.

Beliefs then divide again, and the two shipped worlds show it: the same agent has
`ag:slowSleepS` 600 in `society` and 10 in `sensing`, because the **circumstance** differs, not
because it wants anything different. Operational beliefs (cadence, freshness) track the kind of
world; stake beliefs (target, band, endowment, price) are the agent's own and derivable from
nothing. See [genesis-process](/domain/genesis-process.md) §"Where opening beliefs come from".

# Authoring a world

Say you want `orchard/` — two trees on a shared tank, no market yet.

1. **Sketch it in English first.** The narrate step is not ceremony: the questions it forces
   (*what is this sensor attached to? who owns the valve?*) are exactly the ones `world.ttl`
   has to answer.
2. **Write `world/orchard/world.ttl`.** Copy `sensing/world.ttl` as the skeleton — it is the
   minimum: a bus, a world version, the graph catalog, a subject, a device, an agent. Every
   agent needs an `ag:localId`; every device needs its channels.
3. **Write one `beliefs/<agent>.ttl` per agent**, with only the blocks for the capabilities the
   wiring will give it. Unsure which? Seed and read what derivation decided.
4. **Register each beliefs graph** in the catalog inside `world.ttl`:
   `<.../graph/beliefs/fern> a ag:BeliefsGraph ; ag:beliefsOf ag:fern_agent .`
5. **Validate, and read what it derived.** `agora-validate orchard` builds the world from the
   files and prints `tree_north  Subscribing`. An agent that derived nothing has wiring
   implying no ability — usually a missing `ag:senseMode`, or a device that is not a kind of
   anything the rules recognise.
6. **Validate.** `agora-validate` is capability-aware: a shape applies to an agent only if that
   agent derived the capability it belongs to. It catches a subscribing agent with no interval,
   an interval outside the constitutional bounds, a listening agent that stated one anyway, a
   band whose floor is above its ceiling, a device on a bus with no channel, and an agent with
   no capability at all.
7. **Bring it to life.** `agora-compose orchard` writes the compose file *from the world*, one
   container per agent — nothing lists them, and nothing needs provisioning first.

A new world is covered by the test suite automatically: the shape tests glob `genesis/*/` and
hold every world they find to the same constitution, with no test edit.

# Why more than one world

`sensing/` exists because "capabilities are derived, not declared" is worth nothing unless a
capability can actually run alone. It has no market, so nothing can derive `ag:Bidding`, so no
agent has it — and perception has to stand up by itself or the claim is false.

The two ship with **the same device ids and channels on purpose**. One flashed board runs in
either; which world is in the store decides whether its agent merely watches or also buys. That
is the model-driven claim reduced to something checkable by re-seeding: the hardware did not
change, the model did.

# A world is files, and every agent holds its own copy

There is no shared store. A world is the Turtle in `world/<name>/`, and each agent builds its
own belief base from it at boot — the vocabulary, the whole world, the derivation, and its own
beliefs. See [where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md).

What that buys:

- **Worlds cannot touch each other**, and adding one disturbs nothing that is running. There is
  no shared config, no shared process and no restart.
- **Readings stay with the agent that made them**, which closes a provenance hole: an
  observation records `ag:underWorldVersion`, but two worlds can both be v1, so a shared
  `:sensed` mixed readings nothing could tell apart.
- **Isolation is structural.** An agent's store contains only what it may see, so there is
  nothing to enforce, no credential to issue and no registry to keep in step.
- **Derivation needs no authority.** Every agent runs `rules.ru` over its own copy and computes
  the same answer from the same ratified files.

**Parallel operation has a second requirement the belief base cannot supply: disjoint
hardware.** `society` and `sensing` deliberately share device ids and channels, so one flashed
board runs in either — which also means both worlds up at once puts two agents on
`sensors/fern/moisture`, and both ingest. Worlds meant to run concurrently need different
devices, which is a genesis decision, not an infra one.

# Deployment — one container per agent

`agora-compose <world>` reads the same `world.ttl` and writes `compose.yaml` beside it — a world
is one self-contained directory: its topology, its agents' opening beliefs, and the file that
runs them. It emits: a
`seed` service that runs to completion, then one container per agent, each told only its own
`AGORA_AGENT_ID`. It is generated, never hand-edited — the roster is the ratified world, so a
second list would be a second thing to drift.

Three details are load-bearing rather than packaging taste:

- **One container per agent, holding its own belief base.** It is a file in that agent's own
  volume, exclusively locked by its owner — nothing else can open it, including you.
- **The world is mounted file by file, not as a directory.** An agent gets `world.ttl` and its
  **own** `beliefs/<id>.ttl`, and nothing else — it has no business reading what another agent
  was authored to want. Only an agent that derived `ag:Actuation` also gets
  `secrets/host.key` and `secrets/clearing.key`; the generator runs the real derivation rules
  in memory to know which one that is. Verified: a plant agent's container contains exactly
  two files under `/app/world`, and no key.
- **`network_mode: host`.** The world states the bus as `ag:brokerHost "localhost"` because a
  channel name is meaningless without its broker and every member must agree on it. On a
  bridge network that stops being true for the agents while staying true for the ESP32 — two
  names for one bus, which is what stating it in the world exists to prevent.
- **There is no ordering to express.** An agent builds its own belief base from files mounted
  beside it, so it depends on nothing and can start whenever it likes. The seed service and its
  `depends_on` are gone, and with them the readiness race they papered over.

The source trees are mounted read-only, so a code change needs a restart rather than a rebuild.

```bash
agora-compose society
cd world/society && podman compose up -d
```

# Simulation — a world, not a mode

A society you can run without hardware is a **world whose devices are simulated**, not a flag
on a real one and not a program running beside it.

The model already states what every device is and how it is driven. A simulated device is a
*kind of device*, so an agent derives a simulated capability from it the way it derives any
other — and a world cannot then disagree with how it is actually running. That is the same
rule as everywhere else: what a thing does follows from what the world says it is.

What this replaced: a separate `agora-sim` process pretending to be hardware, told by an
environment variable which subjects to pretend to be. Getting that variable wrong put two
publishers on one topic and both readings were ingested — a failure that cost hours here more
than once, and one the model could not warn about because the model did not know simulation
existed.

**Unbuilt.** The capability and its binding do not exist yet, so today a world needs real
boards. The shape is known: a simulated *binding* fits the existing split better than a new
capability — a capability distinguishes what an agent must decide, a binding distinguishes how
a device is spoken to, and "this reading came from a soil model rather than a wire" is
plainly the second.

# Amending

Edit the files and restart the agents. Bump `ag:versionNumber` on a structural change — every
recorded observation cites the world version it was made under, so the version is how you tell
*when* within a world a fact was true. (*Which* world it was true in is now the dataset it is
stored in, since a version number alone cannot distinguish two worlds that are both v1.)

A start replaces `:ontology` and `:world` in each agent's own store, because those are not the
agent's to keep. It does **not** touch `:beliefs/*` or `:sensed` — those are the agent's, and
only an explicit re-birth discards them.

# Two things that bite

- **Readings are not stored on the wire.** A board publishes QoS 0 and unretained, so a reading
  published while no agent is running goes to nobody. Start the agents *before* the hardware,
  or the first readings are lost.
  ones a real board is already publishing for, on the same topic, and both are ingested. The
  world cannot warn you, by design: it does not know that simulation exists.

# Seams left open

- **Market roles are declared, not derived.** `ag:bidsIn` and `ag:hosts` are the two weakest
  rows in the derivation table. Stating an agent's *goal* — keep this plant alive, steward this
  source — and deriving both market capabilities from that would make them as honest as
  perception and actuation already are, and would also yield who the counterparties are without
  anyone listing them.
- **Derivation is materialised, not maintained.** Rules run at seed time and write triples into
  `:world`; removing a wire does not retract the capability until the world is re-seeded.
- **No cross-world check.** Nothing verifies that two worlds sharing device ids agree about
  those devices' channels, which is exactly the property `society` and `sensing` rely on.
- **Nothing stops two worlds with shared devices running at once.** The belief bases are
  isolated; the MQTT topics are not, so both agents would ingest every reading. Refusing to
  start a world whose devices are already claimed would need a registry of what is running,
  which does not exist.
- **World kind is not modelled.** A bench world and a production one want different operational
  beliefs, and nothing expresses that but the directory you seeded — so near-identical belief
  files are hand-copied between worlds, waiting to drift.
