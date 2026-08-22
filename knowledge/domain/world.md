---
type: Domain Concept
title: World (a ratified genesis output)
term: http://example.org/agora#World
description: What a world is made of — public topology plus one private beliefs file per agent — the three rules for authoring one, and what genesis derives rather than accepts. Several worlds coexist; which one is seeded decides what each agent becomes.
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
agora-validate simulation  # plants, a market, a supplier, valves — devices stood in for
agora-validate sensing     # one subject, one real board, one agent
```

| | holds | derivation produces |
|---|---|---|
| `simulation/` | 3 plants + agents, a supplier, a barrel market, 3 valves, a meddler who waters pots unasked — every device stood in for, on a 24× clock (`ag:timeScale`: one bench hour is one simulated day) | `Subscribing` + `Bidding` per plant agent; `Hosting` + `Actuation` for the supplier |
| `sensing/` | one subject, one real board, one agent | `Subscribing`, and nothing else |

There were three. `society/` held what `simulation/` holds and expected real devices for it, and
the two differed by 45 lines of ~230 with identical beliefs — so it went, and the world that can
run without hardware is the one that stays. See
[two-worlds-were-one](/decisions/two-worlds-were-one.md).

# Anatomy

```
world/<name>/
  *.ttl                public topology, in as many files as suits it:
    world.ttl            the society — agents, subjects, markets, what is wired to what
    hardware.ttl         the stand — hosts, boards, peripherals, which pin each leg is on
  beliefs/<agent>.ttl  one per agent — its private parameters, its opinions
  secrets/             this society's signing keys (gitignored, never committed)
  mosquitto/           generated: this world's broker config, ACL and passwords
  compose.yaml         generated: its broker and one container per agent
```

A world is one self-contained directory. Nothing about it lives anywhere else, which is what
makes adding, copying or deleting one a single move.

**The public topology is every `*.ttl` at the world root, not one named file.** They are loaded
into a single graph in sorted order, so splitting them changes nothing any query sees — it is
purely about what a person reads and reviews at once. A world small enough to say in one file
stays one file; one that has grown a second concern can separate it without telling anything.
Nothing lists them: a new file is picked up by being there, the same rule capabilities are found
by.

`beliefs/` is deliberately not swept up. Those are per-agent and private, and an agent is
mounted only its own — see below.

That is all of it. There is no config file in this project; anything that looks like
configuration is either a fact about the world or somebody's belief, and lives in one of these
two files. See [world-graph](/decisions/world-graph.md) and [belief-base](/domain/belief-base.md).

# The three rules

## 1. State connections, never abilities

**`world.ttl` must not contain `ag:hasCapability`.** State what exists and what is plugged into
what; seeding runs each capability's `rules.ru` and derives what that wiring implies. This is
load-bearing: a declaration can drift from reality, a derivation cannot.

The rule is now kept by the shape of the store rather than by discipline. A derivation writes to
`graph/world/derived` and the ratified graph holds exactly what the files say, so a declared
capability and a derived one are told apart by reading rather than by remembering — and a reader
that wants both simply asks, because every public graph is the default graph of a query. See
[who-put-the-fact-there](/decisions/who-put-the-fact-there.md).

| you state | genesis derives |
|---|---|
| `sensing:polls` a sensor whose `sensing:senseMode` is `sensing:ScheduledProcedure` | `sensing:Subscribing` |
| `sensing:polls` a sensor whose `sensing:senseMode` is `sensing:PushProcedure` | `sensing:Listening` |
| `market:bidsIn` a market | `market:Bidding` |
| `market:hosts` a market | `market:Hosting` |
| `actuation:hasActuator` anything that is a kind of `actuation:Actuator` | `actuation:Actuation` |

Reflash a board from `Push` to `Scheduled`, re-seed, and its agent gains an interval to state —
with no edit to the agent, because there is nothing about the agent to edit. See
[who-holds-the-clock](/decisions/who-holds-the-clock.md) for what those three sense modes mean.

The market rows are the **weakest** of these, and worth naming as such: `market:bidsIn` says "is a
bidder" in other words, where `sensing:senseMode` states a physical fact about hardware. Deriving
market roles from declared *desires* instead is an open seam — see below.

## 2. Every wire name is stated

No process builds a topic from a naming convention. A sensor states its own `mqtt:readingTopic`
and `mqtt:commandTopic`; a market states its three channels; the bus states its host and port. A
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
| aim, endowment, price ceiling | `beliefs/<agent>.ttl` | desire — a fern and a succulent may disagree and neither is wrong |
| sleep intervals, freshness limit | `beliefs/<agent>.ttl` | how closely *this* agent chooses to watch |

If two agents could reasonably disagree about it, it is a belief.

Beliefs then divide again, and the two shipped worlds show it: the same agent has
`sensing:slowSleepS` 600 in `simulation` and 10 in `sensing`, because the **circumstance** differs, not
because it wants anything different. Operational beliefs (cadence, freshness) track the kind of
world; stake beliefs (aim, endowment, price) are the agent's own and derivable from
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
   implying no ability — usually a missing `sensing:senseMode`, or a device that is not a kind of
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
capability can actually run alone. It has no market, so nothing can derive `market:Bidding`, so no
agent has it — and sensing has to stand up by itself or the claim is false.

The two ship with **the same device ids and channels on purpose**. One flashed board runs in
either; which world is in the store decides whether its agent merely watches or also buys. That
is the model-driven claim reduced to something checkable by re-seeding: the hardware did not
change, the model did.

# There is no default world

Nothing here is true of every world at once, so nothing may assume one. Every command takes the
world as a required argument, and `genesis.current_world()` refuses rather than guessing:

```
no world: set AGORA_WORLD_DIR (a mounted world) or AGORA_WORLD (a name).
Available: sensing, simulation
```

There was a `DEFAULT_WORLD = "society"` once, and it was wrong twice over. It put an **instance
name** in kernel code, which the first rule above forbids — `"society"` is no more allowed there
than `"supplier"` or a topic string. And its fallback was the dangerous kind: a process that was
never told which world it belonged to did not fail, it quietly joined the society. That puts a
misconfigured agent on the same topics as the real one, and two agents ingesting the same
readings looks like doubled data rather than like a missing variable — a failure that has cost
real time here twice.

An agent never sets either variable itself. Its container is given `AGORA_WORLD_DIR` pointing at
the one world mounted into it, which is also why it never learns that other worlds exist.

# A stand-in is steered on the same topic a board is commanded on

A simulated device needs a way to be repositioned — set it dry and watch what an agent does about
it — and the obvious move is a second, simulation-only topic. It is the wrong move. The command
topic **already** is a device's control surface: a real board reads the keys it knows off it and
ignores the rest, so `{"set": 0.05}` reaching hardware is silently discarded. Riding the same
channel costs no new term, no new shape, no new grant and no new topic, and it keeps the ACL for a
stand-in identical in shape to a board's.

What does NOT ride it is water. A valve opening reaches the soil over the dose topic, through the
real actuation path, because that is physics rather than an operator's hand — routing it through
the steering verbs would mean the simulation quietly stopped testing whether watering works.
Measured, with the whole loop closing:

```
{"set":0.05}  ->  agent: moisture 0.050 -> bid 1.000 L @ EUR 0.727
              ->  agent: won 1.000 L
              ->  sim:   received 1000 ml -> 0.550     <- over the dose topic
              ->  sim:   cadence now 30.0s, then 220s once recovered
```

A push device subscribes to that topic too, and refuses only the orders about its own clock. A
real push board would not listen at all; the honest half of that is kept, and the other half is
conceded, because a stand-in that cannot be repositioned is untestable.

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
- **Isolation is structural**, which is [belief-base](/domain/belief-base.md)'s to state and
  the reason a world needs no access model of its own.
- **Derivation needs no authority.** Every agent runs `rules.ru` over its own copy and computes
  the same answer from the same ratified files.

**Parallel operation has a second requirement the belief base cannot supply: disjoint
hardware.** `simulation` and `sensing` deliberately share device ids and channels, so one
flashed board runs in either.

What that does and does not cost is worth being exact about, because the obvious fear is the
wrong one. Each world runs **its own broker on its own port** with its own ACL, so two worlds
holding `sensors/moisture_sensor_fern/reading` are two different channels and a publisher
reaches only the broker it dialled. Buckets are world-scoped too. What genuinely cannot be
shared is the **board**: one physical probe publishes to one broker, so whichever world is not
holding it sees a sensor that has gone quiet. Worlds meant to run concurrently against real
hardware need different devices, which is a genesis decision and not an infra one.

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
- **The world is mounted file by file, not as a directory.** An agent gets every public `*.ttl`
  and its **own** `beliefs/<id>.ttl`, and nothing else — it has no business reading what another agent
  was authored to want. Only an agent that derived `actuation:Actuation` also gets
  `secrets/host.key` and `secrets/clearing.key`; the generator runs the real derivation rules
  in memory to know which one that is. Verified: a plant agent's container contains exactly the
  public topology plus its own beliefs under `/app/world`, and no key.
- **`network_mode: host`.** The world states the bus as `mqtt:brokerHost "localhost"` because a
  channel name is meaningless without its broker and every member must agree on it. On a
  bridge network that stops being true for the agents while staying true for the ESP32 — two
  names for one bus, which is what stating it in the world exists to prevent.
- **There is no ordering to express.** An agent builds its own belief base from files mounted
  beside it, so it depends on nothing and can start whenever it likes. The seed service and its
  `depends_on` are gone, and with them the readiness race they papered over.

The source trees are mounted read-only, so a code change needs a restart rather than a rebuild.

```bash
agora-compose simulation
cd world/simulation && podman compose up -d
```

# Simulation — a device that is not there, and nothing else

A society you can run without hardware is a **world whose devices are stood in for**: not a flag
on a real one, not a program running beside it, and — this is the correction — not a capability
of its own either.

A simulated sensor states everything a board states: the bus it is on, the subject it monitors,
the property it observes, its topics, and who holds the clock. One extra fact, `ag:simulatedBy`,
says a process stands in for it. An agent wired to one with `sensing:polls` derives `sensing:Subscribing`
and runs the **ordinary sensing module**, because from where the agent stands there is
nothing else it could be.

The marker is on the device and never on the agent, and that is the whole design.

**What this replaced, and why it was worse than it looked.** Agents used to be wired with
`ag:models` to an `ag:ModelledSubject` and derive `ag:SimulatedSensing`, a capability that held
the model and reimplemented perceiving. So `world/simulation` exercised a *parallel
implementation* — it could pass while the real path was broken, which is the weakest possible
form of simulation. It also cost five smaller things: agent metrics silently omitted every
simulated agent, the ACL generator needed a second query, the readings dashboard caught them
only by accident, `sense_now`/`fresh_reading` had two definitions, and `ag:models` was declared
`rdfs:subPropertyOf sensing:polls` — a promise nothing kept, because shapes ran with RDFS inference
and the runtime did not. That last one is now a promise the runtime *would* keep: the vocabulary's
entailments are materialised into the store before anything reads it, so a sub-property declared
today is followed everywhere rather than wherever someone remembered a property path. See
[one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md).

An earlier draft of this page argued that "a simulated *binding* fits the existing split better
than a new capability — a capability distinguishes what an agent must decide, a binding
distinguishes how a device is spoken to". That was right, and it is what now exists, one level
lower: not a binding but the device itself.

**An actuator is stood in for the same way, and the check is the point.** A simulated valve is
an `actuation:Valve` carrying `ag:simulatedBy`, held by `actuation:hasActuator` like any other — so its
supplier derives plain `actuation:Actuation` and co-signs every command exactly as it would for
hardware. The stand-in verifies both signatures before it opens, holding the two PUBLIC keys and
no private one.

That is a correction rather than an addition. The capability it replaced said plainly that it did
not sign, "because there is nothing to convince" — honest about what it did, and wrong about what
that cost: the simulation exercised every part of actuation except the part a market exists to
make safe.

**Water flows on `mqtt:statusTopic`, never on the command.** A real plant gets wet because water
arrives; between containers the only channel is a message, so the simulated sensor waters on what
the valve *reported having dispensed*. The old arrangement read the valve's command topic, which
meant a command a real valve would refuse still watered the plant. Now a refusal publishes
nothing and the soil stays dry — which is the behaviour worth having a test for, and there is one.

**Sense mode is honoured rather than bypassed.** `sensing:ScheduledProcedure` means the stand-in keeps the
interval its agent gives it over the retained command, exactly as a deep-sleeping board does;
`sensing:PushProcedure` means it keeps its own clock and takes no orders. So the simulation exercises the
retained-cadence mechanism, which the old one never touched at all.

Before it: a separate `agora-sim` process told by an environment variable which subjects to
pretend to be. Getting that variable wrong put two publishers on one topic and both readings
were ingested — a failure that cost hours here more than once, and one the model could not warn
about because the model did not know simulation existed. It knows now.

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
- **Two publishers on one topic are still two publishers.** A stand-in configured for subjects a
  real board already publishes for puts both readings on the same topic and both are ingested.
  The world *can* warn about this now — `ag:simulatedBy` is on the device, so a world states
  which of its devices are stood in for — but nothing checks it yet, and a stray container from
  an earlier run is outside what any shape can see. `podman compose down` removes a society
  deterministically, which is half of why deployment is containers.

# Seams left open

- **Market roles are declared, not derived.** `market:bidsIn` and `market:hosts` are the two weakest
  rows in the derivation table. Stating an agent's *desire* — keep this plant alive, steward this
  source — and deriving both market capabilities from that would make them as honest as
  sensing and actuation already are, and would also yield who the counterparties are without
  anyone listing them. The STATING half has its mechanism now: a world file is TriG, so it may
  carry a named desire-graph block and, beside it, the typing that lets the catalog call the
  graph what it is — the root desire of
  [a-store-is-a-modality](/decisions/a-store-is-a-modality.md), replaced from the files on
  every boot. Deriving the roles from what is stated remains open.
- **Derivation is materialised, not maintained.** Rules run at seed time and write triples into
  `:world`; removing a wire does not retract the capability until the world is re-seeded.
- **No cross-world check.** Nothing verifies that two worlds sharing device ids agree about
  those devices' channels, which is exactly the property `simulation` and `sensing` rely on.
- **Nothing stops two worlds with shared devices running at once.** The belief bases are
  isolated; the MQTT topics are not, so both agents would ingest every reading. Refusing to
  start a world whose devices are already claimed would need a registry of what is running,
  which does not exist.
- **World kind is not modelled.** A bench world and a production one want different operational
  beliefs, and nothing expresses that but the directory you seeded — so near-identical belief
  files are hand-copied between worlds, waiting to drift.
