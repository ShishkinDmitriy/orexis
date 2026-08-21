---
type: Decision
title: What is true of a part is true of every one of them, and OWL already says so
description: A datasheet fact was written on dht11:Dht11 and entailed nothing about any DHT11, because a class-level triple is punning. It is an owl:hasValue restriction now and the closure materialises it, so the sovereign observes the capability on the device the wiring declares without anyone writing it there. Describing at class level was the idea and plain OWL was enough for it — a metamodel is for saying things ABOUT a classification, and this says something about members. What does not change is the boundary: an agent is never given `a dht11:Dht11`, so the entailment stops at the sovereign, and an agent may know a part's properties and not its identity.
status: accepted
stage: v1
tags: [vocabulary, inference, hardware, reuse, owl, boundary]
timestamp: 2026-08-12T00:00:00Z
---

# Context

[a-board-says-what-it-can-honour](a-board-says-what-it-can-honour.md) put a DHT11's two-second
sampling period on the class, with the right reason: *every* DHT11 has it, unlike `probe:rawDry`
which is measured per probe in the pot it sits in. It was written as

```turtle
dht11:Dht11 ssn-system:hasSystemCapability [ a ssn-system:SystemCapability ; … ] .
```

which is **punning** — treating a class as an individual. Legal RDF, and it says the *class*
`dht11:Dht11` has a sampling capability. It entails nothing whatever about a DHT11 you can hold.

So the number had to be written a second time, by hand, onto each sensor in the society, and a test
had to hold the two to agreeing because nothing else could. That is
[#59](https://github.com/ShishkinDmitriy/agora/issues/59), and it was recorded as *"said twice, and
held to agreeing"* — accurate, and one level short of the cause.

# The idea was to describe at class level, and plain OWL was enough for it

The framing that produced this: describe everything **on the class**, taking it that every instance
has what the class has — we simply never declared it by hand. A class `DHT11` is related to a
*kind* of procedure, "temperature reading", and an instance of `DHT11` is understood to have one,
with nobody writing it down.

Reaching for a metamodel to express that is the move worth resisting. A metamodel earns its keep
when you want to say things **about the classification itself** — that this relationship between
two classes is of such-and-such a kind, that it holds with a quantification you can reason over,
that a class is a member of a class of classes. **We want none of that.** We want one thing:

> every instance of this class has this property with this value.

That is `owl:hasValue`, which has been in OWL since 2004:

```turtle
dht11:Dht11 rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty ssn-system:hasSystemCapability ;
    owl:hasValue  dht11:ContinuousOperationCapability ] .
```

Read it as *"a DHT11 is, among other things, one of the things whose
`ssn-system:hasSystemCapability` includes `dht11:ContinuousOperationCapability`."* No metamodel, no
second vocabulary borrowed, no new prefix — `owl:` was already in the kernel's list — and one
SPARQL pattern to materialise. **The general rule this leaves:** reach for a class-of-classes
metamodel when the thing you want to say is about the classification; reach for a class expression
when it is about the members. It is nearly always the second.

## The capability had to be named, and that is not an accident of syntax

`owl:hasValue` takes an **individual**, and a blank node is not one you can name. So the capability
became `dht11:ContinuousOperationCapability` — named for its **condition**, because that is the
axis a second one would differ along. SSN puts *"under the defined Conditions"* into the definition
of `Frequency` itself, so *ten seconds on mains* and *fifteen minutes on battery*
([#78](https://github.com/ShishkinDmitriy/agora/issues/78)) are two capabilities of one device that
would then need telling apart by name. The naming already anticipates the second.

This is the same shape the W3C's own worked DHT22 example takes, which names
`#TemperatureSensorCapability` and its conditions rather than leaving them anonymous. See
[their-descriptions-are-our-fixtures](their-descriptions-are-our-fixtures.md).

**The punned triple is gone, not kept alongside.** Two statements of one fact is what this reduces,
and nothing read the pun: the derivation in `packages/capability/sensing/rules.ru` asks about *sensors*
in the world, never about the class, and the one reader that did walk from the class was the guard
test, which now reads the entailment instead.

# The closure gained a fifth rule, and only this one

`agent/inference.py` materialises what both engines must agree on, because pyoxigraph infers
nothing. Rule 5 is the first OWL construct in it:

```sparql
INSERT { GRAPH <…/world/entailed> { ?x ?p ?v } }
WHERE  { GRAPH <…/world> { ?x a ?class }
         ?class rdfs:subClassOf ?restriction .
         ?restriction a owl:Restriction ; owl:onProperty ?p ; owl:hasValue ?v }
```

Rule 3's shape, and for rule 3's reason: `USING NAMED` keeps the world reachable as itself so an
instance can be insisted on. Rule 1 has already run, so `?class rdfs:subClassOf ?restriction` reads
the transitive closure — a restriction on a superclass reaches the instance too.

**Deliberately just `hasValue`.** It is the only OWL class expression that turns into ground
triples at all. `owl:someValuesFrom` says a value exists without naming one, so there is nothing to
assert; `owl:allValuesFrom` constrains values rather than producing them; cardinality is a shape's
job here and pyshacl already does it. A materialising closure can honour exactly the construct that
materialises.

## One consequence, immediately

A restriction is a class, so `ag:air_sensor_fern a _:restriction` follows from rule 3 — true, and
**unaskable**, because a blank node has no name to put in a query. That is precisely the "true,
useless" category the closure exists to leave out, alongside `every resource is an rdfs:Resource`.
Rules 2 and 3 gained `isIRI(?super)`, which was unnecessary until the vocabulary contained its
first class expression and is load-bearing from now on. See
[one-graph-both-engines-read](one-graph-both-engines-read.md).

# What does not change: an agent may know a part's properties and not its identity

The entailment fires **in the sovereign's graph**, and stops there.

`genesis.world_files` gives the sovereign every `.ttl` in a world — the society *and* `hardware.ttl`
— so it holds `ag:air_sensor_fern a dht11:Dht11` and rule 5 has its premise. `genesis.society_files`
is what an agent is mounted, and it excludes the wiring, so an agent is never told which part it
holds. Rule 5 runs in the agent's store too and finds nothing to fire on, because the class
membership is not there.

**So the society still repeats the number, and it still must.** What changed is where the repetition
comes *from*: it is now a projection of something entailed rather than a second hand-written copy of
something punned, and the guard compares instance to instance.

This is a boundary, not a shortfall. Restated as the rule it actually is:

> **An agent may know a part's properties and not its identity.** Knowing you must not sample faster
> than two seconds does not require knowing you are a DHT11.

That is the same line [where-the-belief-base-lives](where-the-belief-base-lives.md) draws and the
one `test_an_agent_is_given_the_society_and_not_the_hardware` enforces: pins, rails, silkscreen and
part models decide what *can* be built, and once it is built the agent talks to topics. Letting the
part class cross would hand an agent a fact it has no use for and a name it could reason about.

# How much this buys, measured

**Six classes in the vocabulary carry class-level statements, and only one of them wanted this.**
The others are not the same kind of fact, which is the bound worth stating rather than assuming:

| what it says | classes | why a restriction would be wrong or pointless |
|---|---|---|
| what every instance can honour | `dht11:Dht11` | this one — the reader needs it on an instance |
| `mc:modelName`, `wokwi:part`, `wokwi:pin` | `dht11:Dht11`, `esp32:DevKitC`, `probe:CapacitiveMoistureProbe`, `rgbled:RgbLed` | read *as* class facts. `agora-wokwi` and `agora-firmware` hold the class in hand and want the part's drawing, not each instance's copy of it |
| a family's parameter | `sensing:SensingCapability` (`minSleepS`, `maxSleepS`, `reviewWindow`), `ag:BeliefBase` (`maxBytesPerTriple`) | not "true of every instance" — a default the vocabulary states once and readers ask the *family* for |

So the mechanism generalises to every future part with a datasheet, and to nothing else currently
in the tree. That is a small return today and the right one: the alternative was inventing
class-level facts to justify it.

# It found a dead guard, which is the more useful finding

`test_the_society_repeats_every_limit_the_wiring_states` **had asserted nothing since
[PR #95](https://github.com/ShishkinDmitriy/agora/pull/95)**, which renamed `sensing:seconds` to
schema.org's `value`/`unitCode` pair ([one-word-for-one-relation](one-word-for-one-relation.md)).
The guard still asked for the old term, found it nowhere, and passed every run since by having
nothing to compare. Measured on the commit before this one: **zero parts reached an assertion.**

Behind that, a second fault it could never reach: it followed `sosa:hosts` alone, and the same PR
had made the KY-015's channels its `ssn:hasSubSystem` rather than things it hosts
([one-word-for-one-relation](one-word-for-one-relation.md) again). So even a live version would
have compared the wrong subject. **One change broke it twice and neither break was visible**,
because the first hid the second.

The general failure: **every legitimate `continue` in a guard is a way for it to pass by doing
nothing, and total silence looks identical to total success.** The guard now counts its comparisons
and refuses zero — the same move `test_store.py` makes when it asserts its globs are non-empty,
arriving from a different direction. A renamed term empties a scan exactly as a moved file does.

# Consequences

- **A datasheet fact is stated once.** The society's copy is a projection of an entailment rather
  than a parallel assertion, and `agent/inference.py` is where the class-to-instance step lives
  instead of in a test's hand-walk.
- **The guard reads both sides with one query**, because the wiring side no longer needs a hop the
  society side does not.
- **The closure honours one OWL construct**, and the rule for adding another is whether it produces
  ground triples.
- **`isIRI` in rules 2 and 3** — the vocabulary can hold class expressions now, and they must not
  become types.
- **The boundary is stated, not merely observed.** "Properties, not identity" is the sentence to
  cite the next time something wants to reach across it.

# Seams left open

- **The projection into the society is still by hand.** `agora-onboard` could write what the
  sovereign entails onto each sensor a part is composed of, and does not — that is a generator, and
  a generated society file would change what "the world is the files" means. The guard is what
  stands in for it.
- **Only `hasValue`.** Recorded above as a decision rather than a gap: the other class expressions
  have nothing to materialise.
- **A restriction cannot carry a blank node.** The condition and the frequency hanging off
  `dht11:ContinuousOperationCapability` are still anonymous, which is fine while nothing else refers
  to them; a second condition per [#78](https://github.com/ShishkinDmitriy/agora/issues/78) makes
  naming them worth doing.
- **Nothing stops a part class from asserting a value that contradicts its own subclass.** OWL would
  call that unsatisfiable and no reasoner here runs; two restrictions on one property simply both
  materialise.
