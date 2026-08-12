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
- *who owns the barrel?* → owning the venue derives `market:Hosting`, owning valves `actuation:Actuation`
- *thirsty at what number?* → a band is opinion; nothing can infer it

# 2. Write `world/<name>/world.ttl`

Copy `world/sensing/world.ttl` — it is the minimum that still produces a working agent: a
bus, a world version, the graph catalog, a subject, a device, an agent.

**Do not write `ag:hasCapability`.** State what exists and what is wired to what; seeding
derives the rest. This is the rule the whole design rests on — a declaration can drift from
reality, a derivation cannot.

| you state | genesis derives |
|---|---|
| `perception:polls` a sensor with `perception:senseMode perception:ScheduledProcedure` | `perception:Subscribing` |
| `perception:polls` a sensor with `perception:senseMode perception:PushProcedure` | `perception:Listening` |
| `market:bidsIn` a market | `market:Bidding` |
| `market:hosts` a market | `market:Hosting` |
| `actuation:hasActuator` a kind of `actuation:Actuator` | `actuation:Actuation` |

Every device states its own channels — nothing builds a topic from a naming convention. A
board whose `PLANT_ID` disagrees with the world simply never gets read, and nothing warns you.

# 3. Write one `beliefs/<agent>.ttl` per agent

Only the blocks for capabilities the wiring will give it. Unsure which? Do step 4 and read the
output.

Two families, and they behave differently ([genesis-process](/domain/genesis-process.md)):
**operational** (`perception:fastSleepS`, `perception:slowSleepS`, `perception:maxReadingAgeS`) follows the *kind* of
world — a bench rig wants 10s, a garden wants 600s; **stake** (`water:hasTarget`, `water:bandLow`,
`water:bandHigh`, `market:hasEndowment`, `water:maxValuePerL`) is the agent's own and derivable from
nothing.

Register each in the catalog inside `world.ttl`:

```turtle
<http://example.org/agora/graph/beliefs/fern> a ag:BeliefsGraph ; ag:beliefsOf ag:fern_agent .
```

# 4. Validate, and read what it derived

There is nothing to seed. `agora-validate` builds the world exactly as an agent would — from
the files, in memory — and holds it to every package's shapes.

```bash
agora-validate <name>   # exits non-zero on any violation
```

```
  fern       Subscribing, Bidding
  supplier   Hosting, Actuation
Conforms: True
```

**Read the derived line for each agent.** It is the cheapest place a misunderstanding surfaces.
An agent that derived nothing has wiring implying no ability — almost always a missing
`perception:senseMode`, or a device that is not a kind of anything the rules recognise. An agent marked
*(no opening beliefs authored)* is declared but has no `beliefs-<id>.ttl`, and will refuse to
start.

Capability-aware: a shape applies to an agent only if that agent derived the capability it
belongs to. It catches a subscribing agent with no interval, an interval outside the
constitutional bounds, a listening agent that stated one anyway, a band whose floor is above
its ceiling, a device on a bus with no channel, and an agent with no capability at all.

# 5. Deploy

```bash
agora-onboard <name>      # ONBOARDING — validate, then grant all three:
#   agora-influx <name>     #   a bucket per agent, and a token that opens only it
#   agora-mqtt <name>       #   a credential per principal, and the broker ACL, derived
#   agora-compose <name>    #   writes world/<name>/compose.yaml from that world's roster
cd world/<name> && podman compose up -d
```

All three read the world you just ratified and grant exactly what its wiring implies — there is
no list to keep in step with it. A world with a **new device** in it mints a credential that has
to be flashed into that board before it can connect.

Nothing to provision first. Each agent builds its own belief base at boot from the world files
mounted beside it, is born if it never has been, checks itself against the shapes for the
capabilities it derived, and refuses to run if they do not hold.

Then [run-a-world](/runbooks/run-a-world.md).

# It went wrong

| symptom | cause |
|---|---|
| `derived <agent> -> ` nothing | wiring implies no ability; check `perception:senseMode` and that devices are typed |
| `agora-validate` fails on a missing belief | the wiring derived a capability whose block you did not write |
| agent refuses to start, `BeliefsInvalid` | the same thing, caught at startup by the agent itself |
| agent boots, no readings | the board's `PLANT_ID` and the world's `mqtt:readingTopic` disagree |
| `no world called '<name>'` | the directory needs a `world.ttl`; the error lists what it found |
