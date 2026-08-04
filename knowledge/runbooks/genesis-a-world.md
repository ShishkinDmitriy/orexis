---
type: Runbook
title: Genesis a world
description: Author a new world and seed it — what you write, what genesis derives instead, and the four checks that tell you the result hangs together before anything runs.
tags: [genesis, world, seeding, validation]
timestamp: 2026-08-04T00:00:00Z
---

# When to use this

You are adding a society: new hardware, a new test rig, or a variant of an existing world.
Editing an existing world is the same steps from 3 onward.

Background, if the *why* matters: [world](/domain/world.md) for what a world is made of,
[genesis-process](/domain/genesis-process.md) for the conversation that produces one.

# 1. Describe it in English first

Not ceremony. The questions it forces are the ones the Turtle has to answer, and they surface
only once something concrete is on the table:

- *is that board reachable at any moment, or does it sleep?* → decides the perception capability
- *who owns the barrel?* → owning the venue derives `ag:Hosting`, owning valves `ag:Actuation`
- *thirsty at what number?* → a band is opinion; nothing can infer it

# 2. Write `genesis/<name>/world.ttl`

Copy `genesis/sensing/world.ttl` — it is the minimum that still produces a working agent: a
bus, a world version, the graph catalog, a subject, a device, an agent.

**Do not write `ag:hasCapability`.** State what exists and what is wired to what; seeding
derives the rest. This is the rule the whole design rests on — a declaration can drift from
reality, a derivation cannot.

| you state | genesis derives |
|---|---|
| `ag:polls` a sensor with `ag:senseMode ag:Scheduled` | `ag:Subscribing` |
| `ag:polls` a sensor with `ag:senseMode ag:Push` | `ag:Listening` |
| `ag:bidsIn` a market | `ag:Bidding` |
| `ag:hosts` a market | `ag:Hosting` |
| `ag:hasActuator` a kind of `ag:Actuator` | `ag:Actuation` |

Every device states its own channels — nothing builds a topic from a naming convention. A
board whose `PLANT_ID` disagrees with the world simply never gets read, and nothing warns you.

# 3. Write one `beliefs-<agent>.ttl` per agent

Only the blocks for capabilities the wiring will give it. Unsure which? Do step 4 and read the
output.

Two families, and they behave differently ([genesis-process](/domain/genesis-process.md)):
**operational** (`ag:fastSleepS`, `ag:slowSleepS`, `ag:maxReadingAgeS`) follows the *kind* of
world — a bench rig wants 10s, a garden wants 600s; **stake** (`ag:hasTarget`, `ag:bandLow`,
`ag:bandHigh`, `ag:hasEndowment`, `ag:maxValuePerL`) is the agent's own and derivable from
nothing.

Register each in the catalog inside `world.ttl`:

```turtle
<http://example.org/agora/graph/beliefs/fern> a ag:BeliefsGraph ; ag:beliefsOf ag:fern_agent .
```

# 4. Seed, and read what it decided

```bash
agora-seed <name>
```

```
seeded world 'sensing' (topology) -> .../graph/world
derived fern      -> Subscribing
seeded fern      private beliefs -> .../graph/beliefs/fern
```

**Read the `derived` lines.** They are the cheapest place a misunderstanding surfaces. An agent
that derived nothing has wiring implying no ability — almost always a missing `ag:senseMode`,
or a device that is not a kind of anything the rules recognise.

Seeding replaces `:ontology`, `:world` and every `:beliefs/*` graph **in this world's dataset**
and touches no other world. It leaves `:sensed` alone, so readings survive. It is also, today,
an unintended re-*birth*: it overwrites beliefs an agent may have revised. Harmless while
nothing revises them — see [agent](/domain/agent.md) §Lifecycle.

# 5. Validate

```bash
agora-validate <name>   # one world's belief base; exits non-zero on any violation
```

Capability-aware: a shape applies to an agent only if that agent derived the capability it
belongs to. It catches a subscribing agent with no interval, an interval outside the
constitutional bounds, a listening agent that stated one anyway, a band whose floor is above
its ceiling, a device on a bus with no channel, and an agent with no capability at all.

# 6. Credentials, then deploy

```bash
agora-acl           # every world: a dataset each, and one credential per agent
# then restart Fuseki so it loads the new dataset
```

`agora-acl` takes no world — a new world needs a new Fuseki **dataset**, and the config
defining them all is one file. Run it **before** generating the compose file: without it the
per-agent `.pw` files do not exist, the bind mount becomes a directory, and every agent
silently falls back to admin, undoing the isolation. `agora-compose` warns, but only if you
read it.

Then [run-a-world](/runbooks/run-a-world.md).

# It went wrong

| symptom | cause |
|---|---|
| `derived <agent> -> ` nothing | wiring implies no ability; check `ag:senseMode` and that devices are typed |
| `agora-validate` fails on a missing belief | the wiring derived a capability whose block you did not write |
| agent boots, no readings | the board's `PLANT_ID` and the world's `ag:readingTopic` disagree |
| `no world called '<name>'` | the directory needs a `world.ttl`; `agora-seed` lists what it found |
