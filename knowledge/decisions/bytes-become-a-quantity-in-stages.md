---
type: Decision
title: Bytes become a quantity in stages, and each stage is borne by the binding
description: The codec and the calibration become package trees beside transports, each a family whose serving member is DERIVED onto the sensor at genesis rather than searched for at boot. The pointer stays a function, because RFC 6901 works over any tree. The trees are one mechanism split by bearer, not by importance — a capability is derived onto an agent, these onto a binding. Calibration is also where a number acquires a unit, so the three sensors now state QUDT IRIs, borrowed and not imported. Identity stays identity and no number moved.
status: accepted
stage: v1
tags: [sensing, codecs, calibration, units, capabilities, packages]
timestamp: 2026-08-10T00:00:00Z
---

# Context

[a-reading-is-one-value-so-it-is-pointed-at](a-reading-is-one-value-so-it-is-pointed-at.md) named
three stages and built one:

```
bytes ──[codec]──▶ document ──[pointer]──▶ raw value ──[calibration]──▶ quantity
```

It deferred both outer stages on rule 2's test — nothing but JSON existed, and the board already
scaled — and that reasoning was sound at the time. What changed it was not a second format
arriving. It was noticing that **both defaults were already being chosen, and neither choice was
written down anywhere a query could reach.**

- JSON was selected by `json.loads` sitting inside `MqttDriver.parse`, which fused two independent
  facts: how a device is *reached* and what its bytes *mean*. A society could speak MQTT and send
  CBOR, or Modbus and send JSON.
- The calibration was selected by there being no calibration — the firmware scales counts to a
  fraction before publishing, so the remaining step is the identity function. That is not a missing
  stage, it is a stage set to identity, and the difference is the whole reason to name it.

**A family whose one member is picked by an unstated default is not a deferred decision. It is an
unrecorded one.** That is the trigger this record acted on.

# Decision — two families, one function, and a package tree each

`agent/codecs/json/` and `agent/scalings/identity/`, beside `agent/transports/`. Each declares
its family and three members, of which one is implemented:

| | family | implemented | declared |
|---|---|---|---|
| codec | `codec:Encoding` | `codec:Json` | `codec:Cbor`, `codec:Kaitai` |
| scaling | `scaling:Scaling` | `scaling:Identity` | `scaling:Linear`, `scaling:TwoPoint` |

**The pointer stays a function** and moved to `agent/pointer.py`. RFC 6901 works over any tree, so a
pointer written against JSON keeps meaning the same thing over CBOR and over a struct a binary
parser produced — nothing about it varies with either neighbour. By rule 2, where nothing could
differ you have a function, and a function indifferent to both neighbours belongs inside neither.
That indifference is also what made deferring the other two cost nothing.

`codec:Kaitai` is the member worth declaring even unbuilt, because it is the case that looks like it
would break the design and does not: a Kaitai spec yields a **tree**, so `ag:readingPointer`
addresses into it unchanged. A binary format lands in a codec and no other stage moves.

# Why *scaling* and not *calibration*

The last stage was called **calibration** first, and that was wrong — it took a word that names
something else, and something this project intends to build.

Standard usage separates them, and so should we:

| | what it is |
|---|---|
| **calibration** | the **procedure** that establishes the relation between raw output and the measured quantity — hold the probe in air, then in water, record the endpoints — and the numbers it yields |
| **scaling** | applying those numbers to every reading afterwards |

So `scaling:TwoPoint` **consumes** a calibration; it is not one. A calibration is obtained once
and then held; a scaling runs on every message. Naming the stage *calibration* would have left
the procedure — [#26](https://github.com/ShishkinDmitriy/agora/issues/26)'s calibration mode,
where an agent walks someone through the dry and wet references — with no word of its own, in a
project that keeps one word per concept.

*Scaling* is also the standard word for the operation. In data acquisition, scaling raw counts to
**engineering units** is exactly this stage: 730 counts become 0.17 of full scale. One
imprecision, stated rather than hidden: a lookup-table member is not strictly scaling, and the
field calls it that anyway.

The rename happened before this record was ever merged, which is the only reason it cost a
`sed` rather than a migration — the same timing that made
[bid-matching-is-the-word](bid-matching-is-the-word.md) cheap. A term of art is only clear
relative to the vocabulary it lands in, and here the vocabulary that mattered was not the
literature's but **the user's plans**: a word can be free in the codebase and already spoken for
in the design.

# The trees are one mechanism split by bearer

This is the half worth reading, and it is the first time the project has said out loud why
`transports/` was never under `capabilities/`.

**Rule 2 defines a capability as a named ability with interchangeable implementations, and says
nothing about who bears it.** By that definition a codec family is a capability. It is simply not
something an *agent* has. What differs is the bearer, and the predicate follows from it:

| tree | borne by | conclusion |
|---|---|---|
| `capabilities/` | an agent | `ag:hasCapability` on the agent |
| `transports/`, `codecs/`, `scalings/` | a binding | a predicate on the **sensor** |

The reason is not convention. An agent's capability is about what it **is**, which is a fact the
world should hold and validate. A binding's is about what a device **speaks**, which only the
device can say and which no world should have to restate for it.

An earlier draft of this change said the second row was "selected at runtime", and that was wrong.
Nothing here is discovered at runtime: a board's protocol, its wire format and its curve are all
hardware, stated in the world, and known before anything starts.

# So it is derived at genesis, exactly like a capability

The world states a **premise**; `rules.ru` writes the **conclusion** into the derived graph:

| premise, stated | conclusion, derived |
|---|---|
| `codec:encoding` | `codec:decodedBy` |
| `scaling:curve` | `scaling:scaledBy` |

Two predicates rather than one, because collapsing them would let a world state its own conclusion —
the same discipline that keeps `ag:hasCapability` out of `world.ttl`. And `codec_for(sensor)` is now
a lookup of the derived term against `PROVIDES`, exactly as `agent.provider(family)` is for a
capability. Nothing searches.

**What deriving buys, against a `claims()` search at boot.** The first cut of this had each class
answer a claim test at startup, mirroring how a transport picks a driver. Three things that cost:

- a world could name a codec no build implements and `agora-validate` would pass — you found out
  from a log line after the society was up;
- nothing could inspect a sensor's pipeline, because it existed only as the outcome of a Python
  loop over whichever classes a build imported;
- which member won depended on `PROVIDES` iteration order, which guarantees nothing.

It also puts the **default in the graph**. Every sensor in every world was already decoded as JSON
by a flag on a class — true, load-bearing, and unreadable by anything. It is a triple now.

## Explicit beats default, structurally

The two rules per package are disjoint by `FILTER NOT EXISTS`: a sensor either states a premise or
does not. There is no ordering left to get wrong, which is what the Python version could never
promise.

And a shape checks there is exactly one answer. Verified by mutation — two codecs on one sensor, a
sensor with none, and a stated encoding that is not a member of the family are each refused with
their own message, **before a society starts** rather than at the first message.

What the shapes deliberately do **not** refuse is a member that is declared and unimplemented.
`codec:Cbor` holds exactly the position `ag:Polling` and `ag:Consulting` do: the vocabulary says the
seam exists, the build reports at startup that it cannot fill it, and refusing the world instead
would make declaring a seam impossible.

# Scaling is where a number acquires a unit

The half that is not arithmetic, and the one that bites first.

A raw value is a bare number; a **quantity** is a number with a unit. Since
[#51](https://github.com/ShishkinDmitriy/agora/issues/51) one store holds soil moisture `0.183`,
air humidity `0.46` and air temperature `21.4` — three numbers in two dimensions, two of which look
identical. The convention lived in prose, in `vocabulary/water`: *"the whole private valuation is
denominated in soil moisture."*

`scaling:quantityUnit` states it instead, with **QUDT** IRIs as objects — `unit:UNITLESS` for
the two fractions, `unit:DEG_C` for the temperature. SOSA deliberately defines no units and names
QUDT as one of the vocabularies to reach for, so it is the standard companion to what is already in
use here.

**Borrowed, not imported**, exactly as [settlement-speaks-rea](settlement-speaks-rea.md) decided for
ValueFlows: the IRIs are referenced, nothing of QUDT is loaded, and `agent/inference.py`'s
hand-materialised closure gains no axioms to cover. `unit:` sits in the kernel prefix list in
`agent/store.py` rather than in the calibration package, because an external vocabulary is not a
package's to bind — one that could rebind `unit:` could quietly redirect every unit in the society.

**Nothing was converted and no number moved.** Identity stays identity. This declares what the
numbers already meant, which is what turns [#26](https://github.com/ShishkinDmitriy/agora/issues/26)
into a conversion between *stated* units rather than a guess.

# Consequences

- **Adding a format or a curve is adding a directory**, and the rule that names the default belongs
  to the package that claims it. A society whose boards all spoke CBOR would move the default by
  adding a package, not by editing a kernel.
- **A sensor's pipeline is queryable.** Which codec and which calibration serve it are triples in
  `graph/world/derived`, alongside every other conclusion genesis reached.
- **`scaling:Identity` is the honest name for what runs**, and it says something true about the
  deployment: the scaling happens on the board, in C, where changing it means reflashing. The
  moment #26 moves it, a curve stops being a compiled constant and becomes a **belief** — one an
  agent may hold within stated bounds and re-pick as a probe drifts, which is worth more than the
  arithmetic suggests.

# Seams left open

- **`transports/` still searches at boot, and it is the same defect.** `MqttDriver.claims()`
  re-decides from `ag:onBus` and `ag:readingTopic` — facts already in the graph — what genesis could
  have written down once. Two of the three binding-borne trees now derive their member and one does
  not. It was left alone deliberately: converting it touches the working read path for every sensor
  in every world, and [#76](https://github.com/ShishkinDmitriy/agora/pull/76) had just changed that
  method. It should move, and this record says so rather than leaving the inconsistency to be
  discovered.
- **A unit is optional.** `world/sensing` states three; the other two worlds state none, and the
  shape is `maxCount 1` rather than `minCount 1` because requiring it would refuse them for a fact
  this change did not set out to backfill. So a reading may still be a bare number.
- **Nothing checks a unit against the property it measures.** A world could state `unit:DEG_C` on a
  soil moisture sensor and everything would validate. The graph would then be confidently wrong,
  which is a different failure from being silent and arguably a worse one.
- **Nothing compares units before comparing numbers.** `ag:bandLow` is a bare decimal and no code
  asks what unit the reading it is compared against is in. Stating units makes that check
  *possible*; it does not perform it.
- **The unit reaches nothing downstream.** `agent/influx_writer.py` tags a reading with its
  property and not its unit, so the series store still cannot say what `21.4` is. Deliberate: #51
  changed the shape of that data once already, and doing it twice in consecutive changes would be
  two migrations where one would do.
- **The codec is only on the READ path.** `agent/runtime.py` serialises every outbound message
  with `json.dumps` — a cadence, an offer, a voucher — so `encode()` is implemented, tested and
  unreached. A society whose boards spoke CBOR would need that path routed through a codec too,
  and it is a wider change than this one because the same publish serves the market. The
  asymmetry is worth naming: a codec that only decodes is half a codec.
- **No second member of either family exists**, so the interchangeability is asserted rather than
  demonstrated. `codec:Cbor` would be the cheapest proof — CBOR decodes to exactly the maps and
  arrays a pointer already walks.
