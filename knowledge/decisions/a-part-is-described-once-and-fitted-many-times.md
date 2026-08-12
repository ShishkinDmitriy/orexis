---
type: Decision
title: A part is described once and fitted many times, so the description belongs to the model
description: W3C's SSN example describes one serial-numbered DHT22, and every fact in it is a fact about that unit. We ship a package for a model, so the DHT11's two sub-sensors, its procedures and its datasheet figures are stated on classes and reach devices by entailment. Building it found that ssn:implements had been punned since it was introduced — the only subject with that predicate anywhere was the class itself, so no device in any world had ever been said to do anything. A capability is one shared individual and takes owl:hasValue; a sub-sensor is per-unit and takes owl:someValuesFrom, which entails nothing and is enforced by a shape instead.
status: accepted
stage: v1
tags: [vocabulary, sosa, ssn, hardware, inference, owl, reuse]
timestamp: 2026-08-12T00:00:00Z
---

# Context

`vocabulary/dht11/` was asked to become the reference for describing a part — the directory
someone copies when adding a peripheral — starting from the DHT22 description in W3C's SSN
documentation, which we already hold byte-identical as a fixture
(`tests/fixtures/w3c-ssn/dht22.ttl`; see
[their-descriptions-are-our-fixtures](/decisions/their-descriptions-are-our-fixtures.md)).

Reading theirs beside ours, the structural difference is the whole design question:

```turtle
# THEIRS — one unit, serial 4578
<DHT22/4578> a ssn:System ; ssn:hasSubSystem <DHT22/4578#TemperatureSensor> .
<DHT22/4578#TemperatureSensor> a sosa:Sensor ; ssn-system:hasSystemCapability <…#Capability> .

# OURS — a model
dht11:Dht11 rdfs:subClassOf [ owl:onProperty ssn:hasSubSystem ; owl:someValuesFrom dht11:TemperatureSensor ] .
```

Theirs is right for what it is: a data set describing a device someone owns. It is wrong for a
package, because a second DHT22 repeats every line of it. **We distribute a description of a
model and a world names the units**, so the facts a datasheet states belong to the class.

# What was decided

The part is described on the class, once, and reaches devices by entailment — the mechanism from
[what-is-true-of-a-part-is-true-of-every-one-of-them](/decisions/what-is-true-of-a-part-is-true-of-every-one-of-them.md).
Concretely, `dht11:Dht11` now has:

- **two sub-sensor classes.** `dht11:TemperatureSensor` and `dht11:HumiditySensor`, each a
  `sosa:Sensor` and an `ssn:System`. A sensor observes ONE property and this part reports two,
  so the two halves were always there; they had simply never been named as anything but two
  loose sensors in a world.
- **procedures at three levels**, which is the reason to state them rather than let the wiring
  imply them: `onewire:Transaction` is how it is talked to (the protocol package's, referenced),
  `dht11:CombinedRead` is what the whole part does, and `dht11:TemperatureRead` /
  `dht11:HumidityRead` are what each sub-sensor contributes to the one frame.
- **datasheet figures per sub-sensor** — measurement range, accuracy, resolution — while the
  sampling floor stays on the part. That split is physical: the floor is a property of the
  frame, which carries both values, whereas how finely the thermistor resolves has nothing to do
  with the humidity element.

# The defect it found: implements was punned from the start

[a-procedure-belongs-to-whatever-performs-it](/decisions/a-procedure-belongs-to-whatever-performs-it.md)
introduced procedures as `dht11:Dht11 ssn:implements dht11:CombinedRead`. That is punning —
legal RDF that says *the class* implements the procedure — and it entails nothing about a device.
Measured on `world/sensing` before this change:

```
implements: 2
  Dht11  Transaction
  Dht11  CombinedRead
```

**The only subject of `ssn:implements` anywhere was the class itself.** No sensor in any world
had ever been said to do anything. It is the same defect as the punned capability, in the record
directly before this one, introduced two records earlier and missed because a punned triple and
an entailing one read identically. After:

```
implements: 4
  air_sensor_fern    CombinedRead, Transaction
  air_temp_fern      TemperatureRead
  air_humidity_fern  HumidityRead
```

# hasValue entails; someValuesFrom describes

The two restrictions in this package are not stylistic variants, and getting the distinction
wrong is the likeliest way to misuse this as a template:

| | the fact | construct | what happens |
|---|---|---|---|
| capability | every DHT11 shares ONE capability individual — the datasheet's number is the same number | `owl:hasValue` | rule 5 materialises it onto every device |
| sub-sensor | this unit's thermistor is **not** that unit's | `owl:someValuesFrom` | nothing is materialised |

An existential would have to invent an individual per unit — skolemisation, which
`agent/inference.py` deliberately does not do. So the class says every DHT11 has *some*
temperature sensor, the world names which one it is, and **`shapes.ttl` is what refuses a
unit that lacks one**. Without the shape the `someValuesFrom` would be a claim no gate tests:
exactly the entails-nothing-fails-nothing shape this repository keeps finding.

The wiring states which half is which — two triples in `world/sensing/hardware.ttl` — and
everything else follows from the package.

# What is deliberately absent: sosa:observes

Neither sub-sensor states what it observes, and the omission is load-bearing. The property
individual would be `water:AirTemperature`, and `water:` is the **domain** vocabulary — v1 is
plant watering, and `AGENTS.md` is explicit that the domain is a plug-in and the plant/water
language is the example rather than the architecture. A part package importing it would make
this thermistor unusable in a world that is not about plants, which is backwards: the part is
the domain-neutral thing here.

So the line is not *instance versus class*. It is **the part's own facts versus the
installation's**. A DHT11 resolves to 1 °C in every world that will ever use one; what that
degree is a temperature *of* is not the part's business.

# The boundary is unchanged

`society_files` still excludes `hardware.ttl`, so no agent is told `a dht11:Dht11` or
`a dht11:TemperatureSensor`, and none of this reaches an agent's belief base. The entailment
fires in the sovereign, where the vocabulary and the wiring are both loaded. **An agent may know
a part's properties and not its identity** — and now knows more of them without being told any
more than before.

# Seams left open

- **The frame's byte layout is prose.** `dht11:TemperatureRead` says "bytes 2 and 3" in a
  comment. Making that machine-readable is what `mqtt:readingPointer` already does for the
  published JSON, one layer up; nothing needs the wire layout, because no code here speaks
  one-wire — the board does.
- **A second capability under a second condition is sayable and unused.** The humidity span
  differs across revisions of this part, which is why `ssn-system:inCondition` is there rather
  than a number with a caveat. Nothing depends on it yet; battery operation is [#78].
- **Observations do not cite the sub-sensor's procedure.** `sosa:usedProcedure` records the sense
  mode; now that each sub-sensor implements a named read, a temperature observation could cite
  `dht11:TemperatureRead` instead. Deliberately not done here — it changes what is written to
  `:sensed`, and this change writes nothing.
- **No other part has been converted.** The moisture probe and the RGB LED still describe
  themselves the old way, and neither is wrong: a single-property probe IS its sensor, so it has
  no sub-sensors to name. The template is for parts that have parts.
