---
type: Decision
title: A part is described once and fitted many times, so the description belongs to the model
description: W3C's SSN example describes one serial-numbered DHT22, and every fact in it is a fact about that unit. We ship a package for a model, so the DHT11's two sub-sensors, its procedures and its datasheet figures are stated on classes and reach devices by entailment. Building it found that ssn:implements had been punned since it was introduced — the only subject with that predicate anywhere was the class itself, so no device in any world had ever been said to do anything. A capability is one shared individual and takes owl:hasValue; a sub-sensor is per-unit and takes owl:someValuesFrom, which entails nothing and is enforced by a shape instead.
status: accepted
timestamp: 2026-08-12T00:00:00Z
---

> **Current statement: [model-and-unit](/domain/model-and-unit.md).** This record is one
> application of a principle four of them share; the domain concept states the principle
> and the mechanism once.

# Context

`packages/part/dht11/` was asked to become the reference for describing a part — the directory
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
  `dht11:HumidityRead` are what each sub-sensor contributes to the one frame, linked to it by
  `dcterms:hasPart` — see below.
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

# Linking the three procedures, and the word that would have been wrong

Named separately, `dht11:TemperatureRead` reads like a procedure someone could ask the part to
perform. It is not, and the relation between the three had to say so.

**SOSA and SSN relate a Procedure to nothing.** All 44 object properties across `sosa:`, `ssn:`
and `ssn-system:` were enumerated before reaching outside them; the nearest is
`ssn:hasSubSystem`, which is System to System. So this link comes from outside those
vocabularies whatever it is.

`dcterms:hasPart`, then — standard generic mereology, declaring **no domain and no range**, so
applying it to procedures borrows nothing and constrains nothing. Its definition is *"included
either physically or logically in the described resource"*, and logically is the case here.

```turtle
dht11:CombinedRead dcterms:hasPart dht11:TemperatureRead , dht11:HumidityRead .
```

**P-Plan was the alternative, and it was rejected on semantics rather than for want of a term.**
It has the properties SOSA lacks — `p-plan:isSubPlanOfPlan` (Plan to Plan),
`p-plan:isDecomposedAsPlan`, `p-plan:isStepOfPlan` — so "nothing anywhere relates one procedure
to another" would be wrong. What rules it out is what those properties MEAN: P-Plan models a plan
as ordered steps, `p-plan:isPrecededBy` among them, and a sub-plan is something executed as part
of executing the larger one. Adopting it would also mean typing every `sosa:Procedure` here as a
`p-plan:Plan`, and so a `prov:Plan`, importing a plan-execution metamodel to state one part-whole
fact.

`dcterms:hasPart` is the right choice *because* it is semantically weaker. It says inclusion and
stops, where every plan vocabulary says inclusion **and** execution.

**Deliberately not a step, a call or an invocation**, and this is the part worth carrying to the
next composite part. Performing the combined read *constitutes* performing both halves; neither
can be performed alone, because there is one 40-bit frame and no way to ask for a piece of it. A
step relation asserts separability — which is the same error as explaining the shared message by
transport economy, corrected in
[a-procedure-belongs-to-whatever-performs-it](/decisions/a-procedure-belongs-to-whatever-performs-it.md),
arriving by a different route. Part-whole is true; invocation is not.

The payoff is a query that joins the two axes: a device `ssn:implements` the whole conversation
by entailment, and `dcterms:hasPart` reaches what that conversation produced.

# Do the restriction and the shape work together?

In one direction only, and it is worth knowing which. `agent/validate.py` calls pyshacl with
`inference="none"` on the flattened public graphs — so **SHACL understands no OWL whatever**. What
reaches it is whatever the closure already materialised, as ordinary triples it cannot tell from
asserted ones.

Measured on `world/sensing`, with a probe shape requiring `ssn:implements` — a property no world
asserts, so entailment is its only possible source:

| the vocabulary says | what SHACL sees |
|---|---|
| `owl:hasValue` restriction | **the fact** — rule 5 materialised it; conforms |
| the same fact as a class-level pun | **nothing** — probe fails, "SHACL cannot see it" |
| `owl:someValuesFrom` restriction | **nothing** — and a DHT11 with no temperature sensor at all conforms |

So the two are complementary rather than overlapping, and the bridge between them is exactly one
construct wide: **`owl:hasValue` is the only OWL a shape can act on here**, because it is the only
one the closure turns into ground triples. Everything else in OWL is documentation as far as
validation is concerned.

That is the whole reason `ag:Dht11StructureShape` exists and is not redundant with the
`someValuesFrom` above it. The OWL states the structure for a reader and for any reasoner someone
later points at these files; the shape is what makes a world that omits it fail. Deleting either
leaves something true and unenforced — which, on the last line of that table, is a DHT11 with no
sensors passing every gate.

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
- **Observations cannot cite the sub-sensor's procedure, and this is structural rather than a
  choice.** This seam first read "deliberately not done"; measured, it is not available to be
  done. An agent's container is mounted the society alone, and `dht11:` is in
  `HARDWARE_NAMESPACES` — `tests/test_layout.py` fails if a society names it. Building a belief
  base from exactly what a container gets:

  ```
  part type known?          Device, sosa:Sensor, ssn:System     (no dht11:TemperatureSensor)
  read procedure reachable? NOTHING
  sense mode?               sensing:ScheduledProcedure
  ```

  So the read procedure is unreachable from where the observation is written, and projecting it
  into the society the way the sampling floor is projected is barred by that same invariant.

  Underneath it is a question this record does not settle: an observation in `:sensed` says
  `sosa:madeBySensor <sensor>` and `sosa:usedProcedure <the agent's sense mode>`, attributing the
  act to the sensor and the method to the agent's clock. Either the observation is the sensor's
  act — and then the procedure should be the read, which the agent cannot name — or it is the
  agent's act of recording, and `madeBySensor` is provenance of the value rather than of the act.
  W3C's example takes the first reading. Ours has never said which it takes.
- **The plant side now has a counterpart.** `packages/plant/zamioculcas/` describes a species the
  same way for the same reason — see
  [a-species-is-described-once-and-planted-many-times](/decisions/a-species-is-described-once-and-planted-many-times.md).
- **No other part has been converted.** The moisture probe and the RGB LED still describe
  themselves the old way, and neither is wrong: a single-property probe IS its sensor, so it has
  no sub-sensors to name. The template is for parts that have parts.
- **The datasheet figures turned out to be a deployment gate nobody runs.** The day a terrace
  deployment was proposed, the DHT11's own ontology answered why it could not go: a
  `MeasurementRange` of 0–50 °C and 20–90 %RH is a part that cannot report a frost or a fog,
  stated at the class since the package was written. Fitness for a place is therefore already
  graph-visible — `packages/part/bme280/` was added as the outdoor-worthy counterpart, on this
  record's template — and the check is WRITTEN now
  ([#111](https://github.com/ShishkinDmitriy/orexis/issues/111), closed): a deployment states
  its site's ambient envelope in the same Condition idiom the parts speak, and
  `sensing:DeployedWithinItsRangeShape` refuses a world whose instrument cannot contain it —
  the DHT11 passes the windowsill and refuses the terrace, from its own datasheet figures, at
  orexis-validate time. The seam that remains is UNITS: an envelope in an alien unit is skipped
  rather than compared, a documented choice with its own test.
