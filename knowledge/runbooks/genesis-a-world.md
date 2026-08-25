---
type: Runbook
title: Genesis a world
description: Author a new world and seed it — what you write, what genesis derives instead, and the four checks that tell you the result hangs together before anything runs.
---

# When to use this

You are adding a society: new hardware, a new test rig, or a variant of an existing world.
Editing an existing world is the same steps from 3 onward.

Background, if the *why* matters: [world](/domain/world.md) for what a world is made of,
[genesis-process](/domain/genesis-process.md) for the conversation that produces one.

# 1. Describe it in English first

Not ceremony. The questions it forces are the ones the Turtle has to answer, and they surface
only once something concrete is on the table:

- *is that board reachable at any moment, or does it sleep?* → decides the sensing capability
- *who owns the barrel?* → owning the venue derives `market:Hosting`, owning valves `actuation:Actuation`
- *what range does that plant need, and what will it merely survive?* → the two ranges are the
  plant's, and the agent's region is deduced from them; the *target* inside it is still opinion

# 2. Write `world/<name>/world.ttl`

Copy `world/sensing/world.ttl` — it is the minimum that still produces a working agent: a
bus, a world version, the graph catalog, a subject, a device, an agent.

**Do not write `ag:hasCapability`.** State what exists and what is wired to what; seeding
derives the rest. This is the rule the whole design rests on — a declaration can drift from
reality, a derivation cannot.

| you state | genesis derives |
|---|---|
| `sensing:polls` a sensor with `sensing:senseMode sensing:ScheduledProcedure` | `sensing:Subscribing` |
| `sensing:polls` a sensor with `sensing:senseMode sensing:PushProcedure` | `sensing:Listening` |
| `market:bidsIn` a market | `market:Bidding` |
| `market:hosts` a market | `market:Hosting` |
| `actuation:hasActuator` a kind of `actuation:Actuator` | `actuation:Actuation` |

Every device states its own channels — nothing builds a topic from a naming convention. A
board whose `PLANT_ID` disagrees with the world simply never gets read, and nothing warns you.

# 3. Write one `beliefs/<agent>.ttl` per agent

Only the blocks for capabilities the wiring will give it. Unsure which? Do step 4 and read the
output.

Two families, and they behave differently ([genesis-process](/domain/genesis-process.md)):
**operational** (`sensing:fastSleepS`, `sensing:slowSleepS`, `sensing:maxReadingAgeS`) follows the *kind* of
world — a bench rig wants 10s, a garden wants 600s; **stake** (`sensing:aims`,
`market:hasEndowment`, `water:maxValuePerL`) is the agent's own and derivable from nothing.

There is no band to author. Where a plant is parched and where it is soaked belong to the
**plant**, as `ssn-system:hasOperatingRange` and `ssn-system:hasSurvivalRange` in `world.ttl`,
and the agent's region is deduced from them — so the only stake number about moisture you are
asked for is the *target*, and it must sit inside that region or the agent will not start. See
[desire](/domain/desire.md).

Register each in the catalog inside `world.ttl`:

```turtle
<http://example.org/orexis/graph/beliefs/fern> a ag:DesireGraph ; ag:beliefsOf :fern_agent .
```

**A world's individuals live in the world's own namespace, not in `ag:`.** Declare it once at
the top of every file in the world — `@prefix : <http://example.org/orexis/world/<name>#> .` —
and write your agents, sensors, subjects and pins unprefixed: `:fern_agent`, `:local_bus`.
`ag:` is the vocabulary's; a test refuses a world that puts an individual there. The same
declaration goes in each `beliefs/<agent>.ttl`, whose subject is that same `:fern_agent`.

# 4. Validate, and read what it derived

There is nothing to seed. `orexis-validate` builds the world exactly as an agent would — from
the files, in memory — and holds it to every package's shapes.

```bash
orexis-validate <name>   # exits non-zero on any violation
```

```
  fern       Subscribing, Bidding
  supplier   Hosting, Actuation
Conforms: True
```

**Read the derived line for each agent.** It is the cheapest place a misunderstanding surfaces.
An agent that derived nothing has wiring implying no ability — almost always a missing
`sensing:senseMode`, or a device that is not a kind of anything the rules recognise. An agent marked
*(no opening beliefs authored)* is declared but has no `beliefs-<id>.ttl`, and will refuse to
start.

Capability-aware: a shape applies to an agent only if that agent derived the capability it
belongs to. It catches a subscribing agent with no interval, an interval outside the
constitutional bounds, a listening agent that stated one anyway, a target outside the region its
plant's ranges imply, an agent whose ranges intersect to nothing at all, a device on a bus with
no channel, and an agent with no capability at all.

# 5. Deploy

```bash
orexis-onboard <name>      # ONBOARDING — validate, then grant all three:
#   orexis-influx <name>     #   a bucket per agent, and a token that opens only it
#   orexis-mqtt <name>       #   a credential per principal, and the broker ACL, derived
#   orexis-compose <name>    #   writes world/<name>/compose.yaml from that world's roster
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
| `derived <agent> -> ` nothing | wiring implies no ability; check `sensing:senseMode` and that devices are typed |
| `orexis-validate` fails on a missing belief | the wiring derived a capability whose block you did not write |
| agent refuses to start, `BeliefsInvalid` | the same thing, caught at startup by the agent itself |
| agent boots, no readings | the board's `PLANT_ID` and the world's `mqtt:readingTopic` disagree |
| `no world called '<name>'` | the directory needs a `world.ttl`; the error lists what it found |
