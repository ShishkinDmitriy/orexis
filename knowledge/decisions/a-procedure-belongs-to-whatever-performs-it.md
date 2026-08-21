---
type: Decision
title: A procedure belongs to whatever performs it, and procedures distribute down the hosting chain
description: Procedures were declared only as sense modes, on sensors, so a board's own doing — publishing, driving a line, keeping time — was stated nowhere and a part's combined read was explained as a transport economy instead. Each system now implements what it can actually do, and the ESP32 became an ssn:System rather than a Platform alone in order to be able to do anything at all. The frame's first prediction was a defect nobody had reported: one physical read was being stamped three times, which #88's own evidence had recorded as two points 25 ms apart without noticing.
status: accepted
stage: v1
tags: [sensing, sosa-ssn, hardware, provenance, reuse]
timestamp: 2026-08-12T00:00:00Z
---

# Context

Aligning with SOSA/SSN brought one procedure term into the vocabulary and stopped there. A
sense mode became a `sosa:Procedure` — correctly, since *who holds the clock* is a workflow
specifying how to make an Observation — and the three members were typed as Procedures beside
`sensing:SenseMode`. Nothing else in the graph was said to have a procedure.

That left a chain of hardware in which only the last link could do anything. A world says a
board hosts a part, and the part has two channels:

```
esp32_fern  (sosa:Platform)
  └─ sosa:hosts → air_sensor_fern  (ssn:System)
       └─ ssn:hasSubSystem → air_temp_fern, air_humidity_fern  (sosa:Sensor)
```

Ask what each of those does and the graph answers only for the leaves, and only about their
clock. It does not say that the board holds a credential and publishes, nor that the part is
talked to over a single line, nor that the part produces both its values at once. Each of those
is a fact about a specific thing in that chain, and each was living somewhere else — in prose,
in firmware, or in an assumption in the reading path.

The last of them had gone wrong. `dht11:TempHumidityPeripheral` explained its single message as a
transport economy: *the board publishes once because it is one MQTT client with one credential.*
True, and not the reason. That explanation would equally justify batching two unrelated readings
into one message, and the reading path had been written as though it did.

# Decision

**A procedure is declared by whatever performs it, and the hosting chain is the axis along
which they distribute.** Each system implements what it can actually do, and no more:

| thing | procedure | where it lives | linked by `ssn:implements`? |
|---|---|---|---|
| the part | `onewire:Transaction` — one line, both directions in turn | `packages/bus/onewire` | **yes**, on `dht11:Dht11` |
| the part | `dht11:CombinedRead` — one request, two values, one instant | `packages/part/dht11` | **yes**, on `dht11:Dht11` |
| the board | `mqtt:Publishing` — connect as a principal, send on a channel | `transports/mqtt` | **named, not yet linked** — see the seam |
| the board | the clock | `packages/capability/sensing` — **already there**, as the sense modes | no: `sensing:senseMode`, and deliberately |
| a channel | — | `world.ttl` says what it observes and nothing about how | — |

**Both "yes" rows were written on the class, and that entailed nothing about any device.** The
triples above are `dht11:Dht11 ssn:implements …`, which says the *class* implements the procedure
— punning, the same defect the capability had, and it meant the only subject of `ssn:implements`
anywhere was `dht11:Dht11` itself. No sensor in any world had been said to do anything. They are
`owl:hasValue` restrictions now, and the last row is filled in: each channel implements its share
of the frame. See
[a-part-is-described-once-and-fitted-many-times](/decisions/a-part-is-described-once-and-fitted-many-times.md).

The last column is the honest part. Two of the five are asserted, one is named without an
implementer because the graph cannot yet say who publishes, and one deliberately keeps a
different predicate. Naming a procedure and linking it are separate acts, and conflating them is
how a vocabulary acquires triples nobody can defend.

Three consequences follow, and each is the answer to a question that looked separate.

**The ESP32 is an `ssn:System` as well as a `sosa:Platform`.** `ssn:implements` has `ssn:System`
as its domain, so a board that is only a Platform cannot be said to do anything — and every
board here publishes. The two classes answer different questions, `hosts` versus `implements`,
and SSN declares no disjointness anywhere; the W3C's own `PCBBoard1` is typed both. The
vocabulary had already recorded typing it as a Platform alone as *our simplification, not a rule
the vocabulary imposes*. This is where the simplification stopped being free.

**The clock procedure already existed and a second was not added.** It looked missing — a board
keeps time and nothing said so — but `sensing:ScheduledProcedure` and its two siblings *are*
the clock, differing only in who sets it. What is genuinely wrong is that the clock is the
board's while the fact sits on each sensor the board carries, which is [#96] and [#103], and is
deliberately untouched here.

**`ssn:implements` is the right predicate there and the wrong one for a sense mode.** SSN's is
wider: a system may implement as many procedures as it can perform, and a DHT11 implements two.
`sensing:senseMode` carries `sh:maxCount 1`, because a sensor has exactly one answer to *who
holds the clock* and the capability derivation is guarded on that count. Both predicates stay.

# What it predicted, and was right about

The frame was written to name facts, and it immediately contradicted the code.

If the DHT11's two values are one measurement — one 40-bit frame, produced by one sampling,
neither obtainable without the other — then they happened at one instant, and the record must
say so. The reading path said otherwise. `handle` looped the sensors and each write called
`datetime.now()` for itself, so the gap between two halves of one physical read was however long
the loop took. In the series store nothing was passed for the point's time at all, so InfluxDB
stamped each on receipt: **three clocks for one measurement**, two in the series and a third in
the belief base.

The evidence was already recorded. [#88]'s end-to-end run reported two points 25 ms apart from a
single read and treated it as ordinary. It is not a rounding matter and it is not small; it is a
difference that did not happen, written into the record a person actually looks at.

The claim was checked against the driver our firmware uses rather than taken from a datasheet
summary. Adafruit's library fills a five-byte buffer in one transaction, serves a second call
from that buffer, and refuses to go back to the wire inside `MIN_INTERVAL` — two seconds, the
same figure `dht11:Dht11` already declared as its `ssn-system:Frequency`. So the firmware's two
calls were always one conversation.

**A message is a measurement. One arrival, one instant, however many values it carried.** The
instant is resolved once where the message arrives and carried down to both stores.

**Arrival, not each write, and not the device.** Arrival is the earliest instant this code can
honestly claim to know. The device's own instant would be better and is `sosa:phenomenonTime`,
which is [#101]'s neighbourhood — nothing on the wire carries one today, and inventing one from
arrival minus a cadence would be a guess with a timestamp's authority. What was replaced was not
a guess but a non-answer: three unrelated clock reads, none of which was about the measurement.

# Consequences

Two engines that had never been comparable now are. `sosa:resultTime` in the belief base and the
point's time in the series come from the same variable, so a query joining a dashboard to a
belief compares one instant with itself rather than two clocks that were accidentally close.

`at` is optional at every level. A caller with no message in hand — a test, or some future path
that synthesises a reading — has nothing better than now to offer, and saying so in a default is
better than making every caller invent one.

The corrected explanation is in the vocabulary, not only here. `dht11:TempHumidityPeripheral` now
says the values arrive together because they were *taken* together, and that the credential
merely means nothing has to undo that. A part's comment is where someone adding the next part
will look.

# Seams left open

**The world states reading topics on sensors, so `mqtt:publishesOn` derives onto the sensors and
not the board that actually sends.** Harmless while a board carries one credential and every
sensor on it shares one topic — the strings agree precisely because the board is what they
describe — and wrong the moment anything asks who sent a message. Naming `mqtt:Publishing`
without moving the topic is deliberate: it makes the mismatch nameable, and moving it is the
same edit as [#96] and [#103], which must be made on its own because it changes what grants
sensing's capability.

**Nothing enforces that a declared procedure is implementable.** A part could claim
`onewire:Transaction` with no one-wire pin and no shape would object. A shape could check it,
and the reason not to yet is that one part declares two procedures — a rule generalised from a
single case is a guess about the second.

**`sosa:usedProcedure` on an observation still records the sense mode alone.** An observation
made by a combined read is not marked as one, so nothing downstream can tell that two rows were
one act rather than two that agree. This is the same shortfall as [#98] seen from another side,
and it stays a seam because the fix is to key an observation by more than its subject, which is
that issue's business.

**Permanence is still not recorded, so the board states `sosa:hosts` alone.** Unchanged by this
and restated because it is the neighbouring question: `ssn:hasSubSystem` from board to part
requires knowing the mounting is permanent, and nothing in the graph says whether it is.

[#88]: https://github.com/ShishkinDmitriy/agora/pull/88
[#96]: https://github.com/ShishkinDmitriy/agora/issues/96
[#98]: https://github.com/ShishkinDmitriy/agora/issues/98
[#101]: https://github.com/ShishkinDmitriy/agora/issues/101
[#103]: https://github.com/ShishkinDmitriy/agora/issues/103
