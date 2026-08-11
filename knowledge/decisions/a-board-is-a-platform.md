---
type: Decision
title: A board is a sosa:Platform, and mc:carries was sosa:hosts all along
description: The board that three sensors share was not a thing in the model, so every fact about it was repeated per sensor or recovered by comparing topic strings. It is a sosa:Platform now, hosting its parts and they their channels. mc:carries is declared a subproperty of sosa:hosts — the first subPropertyOf axiom here, which the closure was already built for. The society states its own hosting because an agent is never given the wiring, and a test holds the two to agreeing. The codec did not move: two worlds have nine sensors and no platform.
status: accepted
stage: v1
tags: [hardware, sensing, vocabulary, reuse, sosa]
timestamp: 2026-08-11T00:00:00Z
---

# Context

Three sensors share the fern's ESP32 — one radio, one credential, one wake, one message. **None
of that was a node.** Every fact about the board was either a predicate repeated on each sensor,
or string equality between sensors computed in Python:

| fact | expressed as |
|---|---|
| which codec decodes the bytes | `codec:decodedBy` derived onto each sensor, three copies |
| the wake interval | `_aimed_with` comparing `ag:commandTopic` **strings** |
| the broker credential | `ag:onBus` on one peripheral standing in for its board |
| one message carrying several values | emergent, unmodelled |

And it let a real contradiction through: two sensors on one stream may be given two different
codecs and `agora-validate` accepts it, because the per-sensor shape asks for one codec *per
sensor* and nothing can ask for one *per stream*.

# Decision — the standard term, not a new one

**`sosa:Platform`** — *"an entity that hosts other entities, particularly Sensors, Actuators,
Samplers, and other Platforms"* — with **`sosa:hosts`**. SOSA is already in use here for
`sosa:observes` and `ag:Sensor` is already `rdfs:subClassOf sosa:Sensor`, so this is a vocabulary
the project speaks rather than one it is adopting.

The recursion is what makes the shape expressible without inventing anything:

```
Platform(esp32_fern)
   └── hosts → Platform(air_sensor_fern)      # the KY-015
                  ├── hosts → Sensor(air_temp_fern)
                  └── hosts → Sensor(air_humidity_fern)
   └── hosts → Sensor(moisture_sensor_fern)
```

## `mc:carries` was `sosa:hosts` all along

The physical decomposition was never missing — `vocabulary/microcontroller/` has had
`mc:carries` (domain Microcontroller, range Peripheral) since boards were modelled at all. It is
the same relation SOSA standardises, so it is **declared a subproperty** rather than renamed:

```turtle
mc:carries a owl:ObjectProperty ; rdfs:subPropertyOf sosa:hosts .
mc:Microcontroller rdfs:subClassOf ag:Device , sosa:Platform .
mc:Peripheral      rdfs:subClassOf ag:Device , sosa:Platform .
```

Declaring rather than renaming keeps the hardware layer reading in its own words — a wiring
document should say *carries* — while making the fact legible to anything that speaks SOSA.

**It is the first `rdfs:subPropertyOf` axiom in the project**, and `agent/inference.py` rule 4 was
written for exactly this case and had nothing to exercise: its own comment says *"there are no
`rdfs:subPropertyOf` axioms today… this is here so that reintroducing one is a vocabulary edit and
not a debugging session."* It was. Stating `mc:carries` now entails `sosa:hosts` with no widening,
verified rather than assumed.

Note the domains differ on purpose. `mc:carries` is a *board* carrying a *part*, so it cannot say
that a KY-015 hosts its own two channels. `sosa:hosts` can, which is why the society uses the
general relation and the wiring keeps the specific one.

## The society states its own hosting, and that is not duplication for its own sake

An agent is **never given `hardware.ttl`** — `agent/genesis.py` excludes it and
`tests/test_layout.py` asserts an agent's world graph contains no hardware vocabulary at all. The
enforcement is that the file is not in the container. So the entailed `sosa:hosts` exists for the
sovereign, who loads both, and does not exist for the agent, who loads one.

The society therefore states its hosting directly, in `sosa:` terms, which is vocabulary an agent
may legitimately hold. **One fact, said twice, to two audiences.**

That is a drift risk and it is guarded rather than tolerated.
`test_the_society_hosting_agrees_with_the_wiring` holds them together, in the direction drift
actually goes: rewiring a probe onto another board edits `hardware.ttl`, the society keeps the old
answer, and every gate stays green because the society is internally consistent, the wiring is
internally consistent, and no query spans them. Proved by mutating in both directions.

**Not symmetric, deliberately.** The board carries `ag:status_led_fern` and the society omits it:
an agent polls sensors and has no business knowing about an indicator it can never observe.
Demanding the society mirror the wiring would force hardware-only parts into it, which is the leak
the no-hardware-vocabulary test exists to prevent. So the check is *wherever the wiring hosts
something the society also names, the society must agree*, plus *nothing in the society may claim
a host the wiring contradicts*.

## Which closes what #51 left open

Splitting the KY-015 into two channels gave `ag:air_temp_fern` and `ag:air_humidity_fern` no link
to the part they read — the society did not name that part at all. It does now, as a Platform
hosting both. **That is the reason SOSA permits a Platform to host Platforms**, and the reason the
DHT11 is one rather than a Sensor: a sensor here observes one property, and this observes none
itself.

# Three axes, and only two of them are standard

The question this record had to answer first was whether the SOSA/SSN split tells you how many
messages a board sends. **It does not**, and the specification is silent on it by design — there
is no guidance anywhere in SSN on how hosting or sub-system composition affects how observations
are communicated.

| axis | answers | whose |
|---|---|---|
| physical | what is mounted on what — which things share a rail, a wake, a radio | `sosa:Platform` / `sosa:hosts` |
| procedural | what implements what | `ssn:System` / `ssn:hasSubSystem` |
| **communication** | topic, codec, credential — **how many messages** | **ours; nobody standardises it** |

The relation between them is **constraint, not determination**: physical hosting tells you what
*could* share a message, and the binding tells you what *does*. One board with one radio could
still publish on three topics — nothing physical forbids it. That is precisely why #51's answer
was not derivable from the wiring and had to be measured against the credential model instead.

## SSN's procedural axis is not adopted

Nothing in the code cares that a KY-015 implements two sensing procedures rather than being two
things mounted together, so by [AGENTS.md](../../AGENTS.md) rule 2 it is not worth modelling: where
nothing could differ, there is nothing to choose.

One alignment is worth recording as available and cheap, and is **not taken here**:
`ag:senseMode`'s values are `sosa:Procedure`s by definition — *"a workflow, protocol, plan,
algorithm, or computational method specifying how to make an Observation"* is exactly what
Scheduled, Push and Pull each are. That would be alignment triples and no rename, and it belongs
with whatever next touches [who-holds-the-clock](who-holds-the-clock.md) rather than with a change
about boards.

# Consequences

- **The board is queryable.** `?board sosa:hosts ?sensor` answers "what else is on this thing",
  which previously required comparing topic strings and could only be done in Python.
- **`mc:carries` gained a superproperty and lost nothing.** No world changed a line of wiring, and
  the hardware layer still reads as hardware.
- **Rule 4 of the closure is exercised.** It was dead code with a comment explaining why it
  existed; it now has the axiom it was waiting for.

# Seams left open

- **The codec did not move onto the platform, and the reason is the finding.** `society` and
  `simulation` have **nine sensors and no platform between them**: neither states any wiring, so
  there is nothing to project a board from. Deriving the codec onto a platform would leave every
  one of those sensors with none, which `codec:SensorIsDecodedByExactlyOneShape` correctly
  refuses. So the measured hole — two sensors on one stream with two encodings validates clean —
  is still open, and its cause is now precise: not a missing entity, but an unanswered question
  about what a platform *is* in a world with no stated hardware. A simulated device is a
  container; whether that is physical hosting in SOSA's sense has to be decided before the codec
  can move. [#79](https://github.com/ShishkinDmitriy/agora/issues/79) stays open for it.
- **`ag:onBus` did not move either**, for the same reason, and it is the sharper case: it mints
  the broker credential, the firmware's `MQTT_USER` is `moisture_sensor_fern`, and moving it
  renames a principal. Worth knowing meanwhile — **`ag:esp32_fern` already mints a credential with
  no grants at all**, because `hardware.ttl` states `ag:onBus` on it and onboarding reads the
  whole world. One board, two principals: one real and mislabelled as a peripheral, one empty and
  correctly named.
- **The wake interval still groups by comparing command-topic strings.**
  [#78](https://github.com/ShishkinDmitriy/agora/issues/78) is now cheap for the fern —
  `_aimed_with` could ask the platform — and not cheap anywhere else, for the same nine-sensors
  reason.
- **Hosting is stated, not enforced by a shape.** A test holds the society and the wiring
  together; nothing refuses a *world* whose sensor is hosted by nothing. That would be a shape,
  and it cannot be written until every world has platforms.
