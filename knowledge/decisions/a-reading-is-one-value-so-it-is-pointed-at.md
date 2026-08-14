---
type: Decision
title: A reading is one value, so it is pointed at rather than queried
description: Where a sensor's value sits in a payload is a JSON Pointer (RFC 6901), which identifies exactly one value — not a JSONPath (RFC 9535), which returns a nodelist and would need a collapse rule invented on top of it. Absent means /value, so no existing sensor states one. Getting a value off the wire is three stages — codec, pointer, calibration — and only the middle one is built here; the outer two became packages in bytes-become-a-quantity-in-stages, which also renamed the third.
status: accepted
stage: v1
tags: [sensing, transports, payload, reuse, ubiquitous-language]
timestamp: 2026-08-10T00:00:00Z
---

# Context

A KY-015 was soldered to `esp32_fern`, declared in `world/sensing/hardware.ttl`, wired correctly,
and silent. The board had been reading it on every wake and printing it to a serial line nobody
watches, with a comment explaining why it could go no further: one device reports two properties,
a sensor observes one, and the runtime took one reading per message.

Two things assumed one property per device, and both were small:

- `SensingModule.handle` returned after the **first** sensor whose driver owned the topic, so a
  second sensor on that channel never saw a message — silently, because the topic *had* been
  handled and nothing upstream complained;
- `MqttDriver.parse` hardcoded `doc["value"]` and took no sensor, so there was nothing to
  distinguish two sensors reading one payload even once both could see it.

# Decision — the world says which value, as a JSON Pointer

`mqtt:readingPointer` on a sensor. **Absent means `/value`**, which is what every single-property
board here already publishes, so no existing sensor states one and no world changed except the one
that gained sensors.

**RFC 6901** (April 2013, Standards Track) *"defines a string syntax for identifying a specific
value"* — singular. That is exactly what a reading is: one sensor, one property, one number.
Nesting is `/a/b`, an array element is `/a/0`, and the escapes are `~1` for `/` and `~0` for `~`,
decoded in that order.

## Why not JSONPath

**RFC 9535** (February 2024, Standards Track) is the other obvious candidate and is a query
language: a JSONPath expression *"selects zero or more nodes and outputs these nodes as a
nodelist."* Wiring that to a reading means deciding what to do when a query returns two values, or
none — take the first? refuse? — and **that rule would be ours, invented on top of a standard and
then defended forever.** Borrowing a standard to get its semantics and then overriding them is
worse than not borrowing it.

Pointer also costs nothing to implement: the resolution is a loop over `/`-separated tokens and two
ordered replacements, so there is no dependency. The escape order is the one real trap and has its
own test — decoded the other way round, a literal `~01` resolves to `/` instead of `~1` and selects
a field nobody asked for.

## A pointer that misses records nothing

Refused, never defaulted. A pointer that finds no value means the world states something the device
does not send, and answering `0.0` would write that into the belief base as a measurement. The
warning names the sensor and the pointer, because on a shared payload *"unreadable payload on
&lt;topic&gt;"* cannot say which of three sensors found nothing — and one sensor missing its field
while its neighbours read fine is the exact failure a shared message makes possible.

The firmware does the same from its end: a DHT that does not answer omits its fields rather than
sending zero. `0.0 C` is a plausible number in a way silence is not.

# Three stages, and this is the middle one

Getting a quantity off a wire is not one step:

```
bytes ──[codec]──▶ document ──[pointer]──▶ raw value ──[scaling]──▶ quantity
```

- **codec** — how bytes become a document. JSON is the only one, and nothing here names it.
- **pointer** — which value in that document is this sensor's. **This record.**
- **calibration** — what the raw value means. Today the board publishes an already-scaled
  fraction; moving that work into the agent is
  [#26](https://github.com/ShishkinDmitriy/agora/issues/26).

**Amended.** This record called the third stage a *transducer*; the word is now **calibration**,
because a transducer is the physical device that converts one form of energy to another and this
project's sensors are physical devices. Both outer stages became packages in
[bytes-become-a-quantity-in-stages](bytes-become-a-quantity-in-stages.md), which also found that
the third stage was never missing — it was set to identity, because the firmware scales before it
publishes.

**A pointer is indifferent to both of its neighbours, and that is the strongest argument for the
layering.** It is valid whatever codec produced the document — a Kaitai-parsed binary struct is a
tree you can point into exactly as you point into a parsed JSON object — and it is valid whatever
calibration later consumes the value, because it hands back what the device sent and makes no claim
about what it means. So neither neighbour can invalidate a pointer written today, which is why
deferring both costs nothing.

That is also why **no codec family was built here.** Rule 2's test is whether the *how* could
differ, and at the time nothing but JSON existed, so a family looked like a slot with one member
and no second in sight.

**That was reconsidered rather than triggered**, and the reason is worth recording: what forced it
was not a second format but the discovery that JSON was being *chosen* — by `json.loads` inside the
MQTT driver and a default on a Python class — with the choice written down nowhere. A family whose
one member is picked by an unstated default is not a deferred decision, it is an unrecorded one.
See [bytes-become-a-quantity-in-stages](bytes-become-a-quantity-in-stages.md).

The naming carries the split: a driver's `parse` returns **the raw value the pointer identifies**,
and `ingest` records **what is observed**. Two nameable things with nothing between them yet.

# What one board means for a cadence

Splitting the payload forced a second question. Three sensors now share one command topic, because
there is one board and it sleeps once — and a cadence had been aimed per *sensor*.

Left alone, each sensor would compute its own interval from its own urgency and publish it retained
to the same topic: soil moisture asking for 30 seconds, a thermometer the agent has no stake in
asking for 900, last writer winning, on every message. The board would be aimed by whichever sensor
spoke last.

So **a cadence belongs to the board, not to a property.** The channel is aimed once, the tightest
interval any sensor on it asks for wins, and verdicts merge because they are about different
properties and the device shows all of them. Being wrong in that direction costs a reading; being
wrong the other way costs an agent watching a drying pot on a thermometer's schedule.

# The claim test had to widen, and it was wrong before

`MqttDriver.claims` tested `mqtt:onBus` alone, which contradicted that term's own vocabulary —
*"which bus this resource is reachable on. **Optional while a society has one.**"*

It mattered for a reason that is not about drivers at all: **`mqtt:onBus` is also what mints a broker
credential.** `onboarding/mqtt.py` treats a node declaring it as a principal, so giving the two air
channels an `mqtt:onBus` to satisfy the driver produced two extra device principals — measured, not
predicted — each with a real password written into `world/sensing/secrets/` for a client that never
connects. The board is one MQTT client with one credential; its peripherals are not principals.

So the claim now reads either channel term, and a sensor that states where it publishes is claimed
without being made a principal. The ACL is byte-identical across all three worlds.

# Consequences

- **The fern agent reads three properties off one board**, and all three survive in `:sensed` at
  once — which is what finally exercises keying an observation by subject *and* property on real
  hardware rather than in a temporary directory.
- **Humidity is a fraction**, so it lands in the same 0–1 range as soil moisture and inside the
  bands agents hold. Nothing in the number says which it is; only the property does. That hazard
  was named when observations were re-keyed and is now live.
- **The payload grew and the channel did not.** No new topic, no new credential, no new grant.
- **One message turned out to be one measurement, and the code did not treat it as one.** The
  three values were pointed at correctly and then stamped one at a time as each was written, so
  a single physical read left three different instants in the record. Why they are simultaneous
  is a fact about the part rather than about the transport, which is what
  [a-procedure-belongs-to-whatever-performs-it](a-procedure-belongs-to-whatever-performs-it.md)
  set out to state and found by stating.

# Seams left open

- ~~**No codec family.**~~ **Closed**, though not by the trigger this seam named. No non-JSON
  device arrived; what arrived was the realisation that the default was a fact nothing could read.
  `codec:Json` is now derived onto every sensor at genesis. See
  [bytes-become-a-quantity-in-stages](bytes-become-a-quantity-in-stages.md).
- **Nothing checks a pointer against what a device sends.** A world may state `/humidty` and
  validate perfectly; the agent warns at runtime, once per message, forever. A shape cannot catch
  it because the payload is not in the graph. **Narrowed**: a pointer is now exercised against a
  real payload from a real device in `world/simulation`, so a pointer that matches nothing shows
  up in a world that runs — see
  [a-stand-in-reports-what-its-world-says-it-does](a-stand-in-reports-what-its-world-says-it-does.md).
  A world nobody brings up is still unguarded.
- **The tightest cadence wins, and nothing says a sensor may be exempt.** A board carrying one
  urgent property and five indifferent ones reads all six at the urgent rate.
- ~~**`world/society` still reads only moisture** from the same board.~~ **Moot**: `world/society`
  was a near-duplicate of `world/simulation` and has been removed. The property it illustrated
  survives — extra fields in a payload are ignored rather than refused, which is what lets one
  flashed board serve a world that reads three values and a world that reads one.
