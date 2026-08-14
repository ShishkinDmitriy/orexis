---
type: Decision
title: A board is a sosa:Platform, and mc:carries was sosa:hosts all along
description: The board that three sensors share was not a thing in the model, so every fact about it was repeated per sensor or recovered by comparing topic strings. It is a sosa:Platform now, hosting its parts and they their channels. mc:carries is declared a subproperty of sosa:hosts — the first subPropertyOf axiom here, which the closure was already built for. The society states its own hosting because an agent is never given the wiring, and a test holds the two to agreeing. The codec did not move, and the reason was a category error rather than a missing entity — see the-wire-is-ours-and-it-has-two-levels.
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
| the wake interval | `_aimed_with` comparing `mqtt:commandTopic` **strings** |
| the broker credential | `mqtt:onBus` on one peripheral standing in for its board |
| one message carrying several values | emergent, unmodelled |

And it let a real contradiction through: two sensors on one stream may be given two different
codecs and `agora-validate` accepts it, because the per-sensor shape asks for one codec *per
sensor* and nothing can ask for one *per stream*.

# Decision — the standard term, not a new one

**`sosa:Platform`** — *"an entity that hosts other entities, particularly Sensors, Actuators,
Samplers, and other Platforms"* — with **`sosa:hosts`**. SOSA is already in use here for
`sosa:observes` and `sensing:Sensor` is already `rdfs:subClassOf sosa:Sensor`, so this is a vocabulary
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

The physical decomposition was never missing — `packages/part/microcontroller/` has had
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
to the part they read — the society did not name that part at all. It does now, and the reason it
is not a Sensor stands: a sensor here observes one property, and this observes none itself. What
it is was corrected shortly after this record — an `ssn:System` with the two channels as
sub-systems, not a Platform, because it is hosted and mounts nothing. The board above it is both,
which is what SOSA permitting a Platform to host Platforms was doing the work of.

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

## SSN's procedural axis was not adopted here, and both deferrals have since been taken

Recorded at the time as not worth modelling, on the grounds that nothing in the code cared that a
KY-015 implements two sensing procedures rather than being two things mounted together. Both parts
of that turned out to be worth taking, and neither by the trigger named:

- the cheap alignment — `sensing:senseMode`'s values ARE `sosa:Procedure`s by definition — was
  taken in [an-observation-says-how-it-was-made](an-observation-says-how-it-was-made.md), which
  did indeed arrive by way of [who-holds-the-clock](who-holds-the-clock.md);
- the procedural axis itself was taken in
  [a-procedure-belongs-to-whatever-performs-it](a-procedure-belongs-to-whatever-performs-it.md),
  and what made it worth modelling was not code caring but the ABSENCE of it hiding a defect. A
  DHT11's single message was being explained by the credential model rather than by the part, and
  the reading path was written to match — stamping each value separately, so one physical read
  left three instants in the record. Naming what the part does is what made that visible.

The reasoning stands as a test of rule 2 and shows where it is easy to misapply. *Where nothing
could differ, there is nothing to choose* is about implementations of a CAPABILITY. A procedure is
a fact about equipment, and a fact can be worth stating for what it rules out.

# Consequences

- **The board is queryable.** `?board sosa:hosts ?sensor` answers "what else is on this thing",
  which previously required comparing topic strings and could only be done in Python.
- **`mc:carries` gained a superproperty and lost nothing.** No world changed a line of wiring, and
  the hardware layer still reads as hardware.
- **Rule 4 of the closure is exercised.** It was dead code with a comment explaining why it
  existed; it now has the axiom it was waiting for.

# Seams left open

- **The codec did not move onto the platform, and the reason turned out to be a category error
  — mine, not the model's.** `society` and `simulation` state no wiring, so they have six sensors
  and no platform between them, and deriving the codec onto a platform would leave every one of
  them without one. That was recorded here as an unanswered question — *what is a platform in a
  world with no stated hardware?* — and it is not one. A codec is a fact about a **connection**,
  and it was being hung on a node that exists for a different reason. See
  [the-wire-is-ours-and-it-has-two-levels](the-wire-is-ours-and-it-has-two-levels.md): the bearer is the principal, every
  world already has principals, and **a simulated world correctly has no platforms at all.** The
  measured hole is still open; what was blocking it is not.
- **`mqtt:onBus` did not move either**, and it is the sharper case: it mints the broker credential,
  the firmware's `MQTT_USER` is `moisture_sensor_fern`, and moving it renames a principal. Worth
  knowing meanwhile — **`ag:esp32_fern` already mints a credential with no grants at all**,
  because `hardware.ttl` states `mqtt:onBus` on it and onboarding reads the whole world. One board,
  two principals: one real and mislabelled as a peripheral, one empty and correctly named. Filed
  as [#81](https://github.com/ShishkinDmitriy/agora/issues/81).
- **The wake interval still groups by comparing command-topic strings.**
  [#78](https://github.com/ShishkinDmitriy/agora/issues/78) now has a bearer in every world rather
  than only the wired one: a wake is one connection waking, so the question is the principal's.
- **Hosting is stated, not enforced by a shape.** A test holds the society and the wiring
  together; nothing refuses a *world* whose sensor is hosted by nothing. That would be a shape,
  and it cannot be written until every world has platforms.
