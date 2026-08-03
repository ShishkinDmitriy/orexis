# Genesis — ratified worlds

Each directory here is **one complete output of the genesis process**: a world model that can
be seeded on its own and run. Not fragments, not fixtures layered on a base — each is the
whole of what some society is.

```bash
agora-seed society      # the full example: plants, a market, a supplier, valves
agora-seed sensing      # the smallest one that produces a working agent
```

| | what it holds | what derivation produces |
|---|---|---|
| `society/` | 3 plants + their agents, a supplier, a barrel market, 3 valves | `Subscribing` + `Bidding` per plant agent; `Hosting` + `Actuation` for the supplier |
| `sensing/` | one subject, one board, one agent | `Subscribing`, and nothing else |

The decision behind all of this is [genesis](../knowledge/decisions/genesis.md): the sovereign
narrates, an LLM drafts, the sovereign ratifies, and what lands here is the ratified result.
This file is the practical half — what a world is made of, and how to author one.

---

## What a world is made of

```
genesis/<name>/
  world.ttl              public topology: what exists, and what is wired to what
  beliefs-<agent>.ttl    one per agent — its private parameters, its opinions
```

That is all. There is no config file anywhere in this project; if something looks like
configuration, it is either a fact about the world or somebody's belief, and it lives in one
of these two places. See [world-graph](../knowledge/decisions/world-graph.md).

### The one rule: state connections, never abilities

**`world.ttl` must not contain `ag:hasCapability`.** You say what exists and what is plugged
into what; `agora-seed` runs each capability's `rules.ru` and derives what that wiring implies.
This is the load-bearing part — a declaration can drift from reality, a derivation cannot.

| you state | genesis derives |
|---|---|
| `ag:polls` a sensor whose `ag:senseMode` is `ag:Scheduled` | `ag:Subscribing` |
| `ag:polls` a sensor whose `ag:senseMode` is `ag:Push` | `ag:Listening` |
| `ag:bidsIn` a market | `ag:Bidding` |
| `ag:hosts` a market | `ag:Hosting` |
| `ag:hasActuator` anything that is a kind of `ag:Actuator` | `ag:Actuation` |

Reflash a board from `Push` to `Scheduled`, re-seed, and its agent gains an interval to state
— with no edit to the agent, because there is nothing about the agent to edit.

### The second rule: every wire name is stated

No process builds a topic from a naming convention. A sensor states its own `ag:readingTopic`
and `ag:commandTopic`; a market states its three channels; the bus states its host and port. A
process is handed exactly one instance identifier — its own agent id — and discovers
everything else from it.

So renaming a channel is a genesis edit, and a board whose `PLANT_ID` disagrees with the world
simply never gets read. Check the two against each other by eye; nothing else will.

### The third rule: fact and opinion live in different files

`world.ttl` holds what everyone must agree on. `beliefs-<agent>.ttl` holds what that agent
alone thinks, and no other agent can read it.

| | where | why |
|---|---|---|
| wiring, calibration, capacity | `world.ttl` | physical, public, stated once |
| target, band, endowment, price ceiling | `beliefs-<agent>.ttl` | desire — a fern and a succulent may disagree and neither is wrong |
| sleep intervals, freshness limit | `beliefs-<agent>.ttl` | how closely *this* agent chooses to watch |

If two agents could reasonably disagree about it, it is a belief.

---

## Authoring a new world

Say you want `orchard/` — two trees on a shared tank, no market yet.

**1. Sketch the topology in English first.** This is the narrate step, and it is not ceremony:
the questions it forces (*what is this sensor attached to? who owns the valve?*) are exactly
the ones `world.ttl` has to answer.

**2. Write `genesis/orchard/world.ttl`.** Copy `sensing/world.ttl` as the skeleton — it is the
minimum: a bus, a world version, the graph catalog, a subject, a device, an agent. Add what
your world has. Every agent needs an `ag:localId`, and every device a channel.

**3. Write one `beliefs-<agent>.ttl` per agent** — only the blocks for the capabilities the
wiring will give it. If you are unsure which those are, seed and look: the derivation prints
what it decided.

**4. Register each agent's beliefs graph** in the catalog inside `world.ttl`:

```turtle
<http://example.org/agora/graph/beliefs/fern> a ag:BeliefsGraph ; ag:beliefsOf ag:fern_agent .
```

**5. Seed it and read what came out.**

```bash
agora-seed orchard
#   seeded world 'orchard' (topology) -> .../graph/world
#   derived tree_north -> Subscribing
#   derived tree_south -> Subscribing
```

If an agent derived nothing, its wiring implies no ability — almost always a missing
`ag:senseMode`, or a device that is not a kind of anything the rules recognise.

**6. Validate.** This is the real check, and it is capability-aware: a shape applies to an
agent only if that agent derived the capability it belongs to.

```bash
agora-validate      # exits non-zero on any violation
```

It catches a subscribing agent with no interval, an interval outside the constitutional
bounds, a listening agent that stated one anyway, a band whose floor is above its ceiling, a
device on a bus with no channel stated, and an agent with no capability at all.

**7. Bring it to life.** Nothing lists the agents — `agora-up` asks the belief base who exists
and starts one process each.

```bash
agora-acl orchard   # per-agent store credentials, if you want read isolation enforced
agora-up
```

Your new world is also covered by the test suite automatically: `test_shapes.py` globs
`genesis/*/` and holds every world it finds to the same constitution, with no test edit.

---

## Why more than one world

`sensing/` exists because the claim "capabilities are derived, not declared" is only worth
anything if a capability can actually run alone. It has no market, so nothing can derive
`ag:Bidding`, so no agent has it — and the perception capability has to stand up by itself or
the claim is false.

The two worlds use **the same device ids and the same channels on purpose**. One flashed board
works in either; which world is in the store decides whether its agent merely watches or also
buys. That is the model-driven point in one move: the hardware did not change, the model did.

---

## Editing an existing world

Edit and re-run `agora-seed <name>`. Bump `ag:versionNumber` on a structural change — every
recorded observation cites the world version it was made under, so the version is how you tell
which world a fact was true in.

Seeding replaces `:ontology`, `:world` and every `:beliefs/*` graph. It does **not** touch
`:sensed`, so readings survive a re-seed. Switching worlds does not clear the other world's
beliefs graphs; re-run `agora-acl <name>` after a switch if you use per-agent credentials.

## Two things that bite

- **Readings are not stored on the wire.** A board publishes QoS 0 and unretained, so a
  reading published while no agent is running goes to nobody. Start `agora-up` *before* the
  hardware, or the first readings are lost.
- **`agora-sim` simulates every plant in the world when `AGORA_SIM_PLANTS` is empty** —
  including ones a real board is already publishing for, on the same topic. When any hardware
  is connected, list only the virtual subjects there.
