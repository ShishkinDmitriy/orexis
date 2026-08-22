---
type: Domain Concept
title: Model and unit — a thing is described once, and every one of them inherits it
term: http://example.org/agora#DeviceModel
description: One principle behind four decision records. A part, a species and a firmware are all
  MODELS; the things in a world are UNITS of them. What the datasheet says is stated once on the
  class and reaches every unit by entailment, never by repetition. `owl:hasValue` for what units
  SHARE, `owl:someValuesFrom` plus a shape for what each unit has its OWN of — and a bare
  class-level triple for neither, because that is punning and entails nothing.
---

# The principle

A **model** is a kind of thing the project ships a package for: a DHT11, a Zamioculcas, a
firmware image. A **unit** is one of them in a world: the probe on this board, the pot on that
shelf, the ESP32 running that image.

**What is true of the model is stated once, on the class, and reaches every unit by entailment.**
Nobody writes a datasheet figure onto a device, and no world repeats one. Planting a Zamioculcas
is one triple; fitting a DHT11 is one triple.

This is the same move in four places, which is why it is worth stating once:

| the model | its units | the record |
|---|---|---|
| a **part** — `dht11:Dht11` | the probes wired into a world | [a-part-is-described-once-and-fitted-many-times](/decisions/a-part-is-described-once-and-fitted-many-times.md) |
| a part's **datasheet facts** | the same, and this is where the mechanism was settled | [what-is-true-of-a-part-is-true-of-every-one-of-them](/decisions/what-is-true-of-a-part-is-true-of-every-one-of-them.md) |
| a **species** — `zamioculcas:Zamioculcas` | the pots planted with it | [a-species-is-described-once-and-planted-many-times](/decisions/a-species-is-described-once-and-planted-many-times.md) |
| a **firmware** image | the boards flashed with it | [a-firmware-describes-itself](/decisions/a-firmware-describes-itself.md) |

# The three ways to say it, and only one of them works

## A bare class-level triple is punning, and entails nothing

```turtle
dht11:Dht11 ssn-system:hasSystemCapability dht11:ContinuousOperationCapability .  # WRONG
```

Legal RDF. It says the **class** has the capability, which entails nothing whatever about a DHT11
you can hold. It was written this way, and nothing read it — the only subject with that predicate
anywhere was the class itself, so no device in any world had been said to do anything.

## `owl:hasValue` — for what every unit SHARES

```turtle
dht11:Dht11 rdfs:subClassOf
    [ a owl:Restriction ; owl:onProperty ssn-system:hasSystemCapability ;
      owl:hasValue dht11:ContinuousOperationCapability ] .
```

The class goes **under** a restriction rather than being handed the property. This says *every
instance* has it, which is what a datasheet means. The capability is one individual every DHT11
shares — the datasheet's number is the same number — so it can be named, and `owl:hasValue`
requires a named individual.

`agent/inference.py` materialises exactly this, into the world's entailed graph, and it is the
only OWL construct the closure carries.

## `owl:someValuesFrom` plus a shape — for what each unit has its OWN of

```turtle
dht11:Dht11 rdfs:subClassOf
    [ a owl:Restriction ; owl:onProperty sosa:hasSubSystem ;
      owl:someValuesFrom dht11:TemperatureSensor ] .
```

A sub-sensor is **not** shared: this DHT11's thermistor is not that one's. What the class can say
is that every unit has *some* temperature sensor; the individual is minted by whoever names the
unit. An existential entails nothing you can query, so **a shape enforces it instead**.

That is not a gap in the closure. It is the difference between a fact about the model and a fact
about each unit, and the two need different tools.

# What the closure does and does not do

`agent/inference.py` materialises entailments into the store at genesis, once, and validation runs
with inference **off** against that same graph. So:

- **Ask what a thing IS. Do not walk a subclass path.** `?d a ag:DesireGraph` reads the closure.
  Six queries once carried `rdfs:subClassOf*` by hand for twenty-five declared axioms;
  `tests/test_inference.py` refuses a seventh.
- If the closure does not cover your case, **widen `agent/inference.py`** rather than working
  around it. The same test fails if pyshacl ever entails something the closure does not.
- Only `owl:hasValue` is carried. `owl:someValuesFrom` is deliberately not — see above — and
  cardinality is a shape's job, which pyshacl already does.

See [one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md).

# Where the boundary sits

**A model is described by its package; a unit is described by its world.** The package says what a
DHT11 is; the world says which one is wired where. An agent is never given `a dht11:Dht11`, so an
agent may know a part's properties and not its identity — the rule that code names T-Box terms
and never instances survives this whole mechanism intact.

Two consequences worth knowing:

- **What a channel OBSERVES stays out of a part.** That would import the domain vocabulary into a
  part package, and a DHT11 is a DHT11 whether or not anything here wants to know about soil.
- **Only the connecting device is typed** by a firmware. A bare microcontroller would inherit a
  sense mode with no channel to serve it, and simulated devices are never typed at all.

# Related

[their-descriptions-are-our-fixtures](/decisions/their-descriptions-are-our-fixtures.md) — what a
standard's own device description is missing, measured rather than argued: exactly the four facts
a vendor could not know, which is the part/deployment boundary.
[a-board-is-a-platform](/decisions/a-board-is-a-platform.md) and
[a-procedure-belongs-to-whatever-performs-it](/decisions/a-procedure-belongs-to-whatever-performs-it.md)
— what hosts what, and which of them performs what.
