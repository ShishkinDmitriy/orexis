---
type: Decision
title: Physical, procedural, and the wire — and only the last one is ours
description: A codec and a credential are facts about a connection, not about a board, so they belong to the principal rather than the platform. SOSA gives the physical decomposition and SSN the procedural one, and neither says anything about transmission — that axis is the project's own. Which means a simulated world correctly has no platforms at all, and the question that blocked moving the codec dissolves rather than needing an answer.
status: accepted
stage: v1
tags: [sensing, platform, transport, vocabulary, reuse, ubiquitous-language]
timestamp: 2026-08-11T00:00:00Z
---

# Context

[a-board-is-a-platform](a-board-is-a-platform.md) projected the physical decomposition into the
society and then stalled. The codec was supposed to move from each sensor onto the board that
sends the message, closing a measured hole — two sensors on one stream with two different
encodings validates clean today. It could not: `society` and `simulation` state no wiring at all,
so they have six sensors and **no platform between them**, and deriving the codec onto a platform
would leave every one of those sensors without one.

That was recorded as an unanswered question — *what is a platform in a world with no stated
hardware?* — with a simulated device being a container and containers not obviously being
physical hosts.

**The question was the wrong one.** It only arose because a fact about a *connection* was being
hung on a node that exists for a different reason.

# The three axes, and which of them is ours

| axis | what it groups | vocabulary |
|---|---|---|
| **physical** | what is mounted on what — which things share a rail, a wake, a radio | `sosa:Platform`, `sosa:hosts` |
| **procedural** | what implements what | `ssn:System`, `ssn:hasSubSystem` |
| **communication** | one credential, one connection, **one message** | **ours** |

The third is ours because nobody standardises it. The SSN specification has **no guidance** on
how hosting or sub-system composition affects the way observations are communicated — checked,
not assumed. That is deliberate: SOSA and SSN model the world and the instruments, not the wire.

So the relation between the axes is **constraint, not determination**. Physical decomposition
tells you what *could* share a message: one radio can only send one at a time. What *does* share
one is a fact about the binding, and a board with one radio could publish on three topics without
contradicting anything physical. That is why the topic question in
[#51](https://github.com/ShishkinDmitriy/agora/issues/51) was not derivable from the hardware and
had to be settled against the credential model instead.

# Decision — a communication fact belongs to the principal

**`ag:Principal`** — the thing that holds one credential and one connection — bears the codec, the
bus and the encoding of what it sends. It is derived from `ag:onBus`, which every world already
states, so this is a name for something that exists rather than a new requirement on an author.

The concept is not new either. `onboarding/mqtt.py` has carried it since
[series-and-bus-isolation](series-and-bus-isolation.md):

```python
class Principal:
    """One thing that may connect, and everything it may say or hear."""
```

It was in the code and absent from the graph, which is why nothing could be derived onto it.

## A simulated world has no platforms, and that is correct

Nothing is mounted on anything in `simulation`. There is no board, no rail, no wake — the devices
are containers, and a container hosts nothing in SOSA's sense. Giving those worlds platforms to
satisfy a shape would have been inventing a physical fact to carry a logical one.

They have principals, because every world has principals. So the codec can move in all three
worlds without any of them gaining a platform, and the shape can finally ask the question worth
asking: **one stream, one encoding** — because the stream is the principal's.

## What SOSA and SSN do say about software

Checked, because the alternative was to assume it. The specification supports virtual and
simulated entities explicitly, and names it as a correction to earlier versions:

> The initial SSN has been criticized for its partially inconsistent handling of virtual sensors
> (including software and simulations)… The new SSN and SOSA address this issue by allowing all
> major classes to be virtual.

`sosa:Sensor` is *"Device, agent (including humans), **or software (simulation)** involved in, or
implementing, a Procedure"*, and it is **declared a subclass of `ssn:System`**. `sosa:Platform` is
**not** a subclass of `ssn:System` — they are separate classes — and its examples are all things
with a location: *"a post, buoy, vehicle, ship, aircraft, satellite, cell-phone, human or
animal."*

So a simulated device grouping its sensors would be an `ssn:System` with `ssn:hasSubSystem`,
needing nothing invented, since a sensor is already a System. **Not adopted**, because nothing
needs it: no code cares that a simulated device implements two sensing procedures rather than
being two things that happen to run together. It is recorded so the next person reaching for a
grouping there knows which one is right, and knows it is a modelling choice rather than a gap.

# The cut is right, and the current model gets it wrong

The strongest evidence is a defect this makes nameable. `firmware/moisture-sensor/include/config.h`:

```c
#define MQTT_USER "moisture_sensor_fern"
```

**The ESP32 authenticates to the broker as one of its own peripherals**, while `ag:esp32_fern`
holds a credential with zero grants that nothing ever uses. Both facts are on `main` today and
predate all of this.

It is not a naming quibble. The ACL is keyed on the username, so the board's grants are filed
under a probe's name; a second peripheral that publishes would have no principled place to put
its topics; and revoking the probe would silence the board. One connection, two principals, and
the firmware uses the wrong one.

Under this record the answer is not a matter of taste: the board connects, so the board is the
principal, and its sensors' topics are its grants.

# Consequences

- **The blocker dissolves rather than resolving.** Moving the codec needs no answer to *what is a
  platform without hardware*, because a platform was never the right bearer.
- **The platform layer keeps its own work.** Physical decomposition is what
  [#59](https://github.com/ShishkinDmitriy/agora/issues/59) needs for a board's honourable
  interval range, and what gives the DHT11's two channels a parent. It is not diminished by not
  carrying the wire.
- **[#78](https://github.com/ShishkinDmitriy/agora/issues/78) gets a bearer too.** A wake is one
  connection waking, so `_aimed_with` comparing command-topic strings could ask the principal
  instead — in every world, not only the wired one.
- **A third kind of node joins the model**, after the agent and the sensor. Worth watching that it
  stays what it says: the thing that connects, not a general-purpose grouping to hang facts on
  because it happens to be convenient.

# Seams left open

- **Nothing is built.** This record is the design; `ag:Principal` does not exist yet, the codec has
  not moved, and the hole it would close is still open.
- **The firmware's identity is wrong and unfixed.** Filed rather than folded in, because changing
  which principal a board connects as rewrites its credential and its ACL — the regression class
  that [#62](https://github.com/ShishkinDmitriy/agora/pull/62) belongs to — and needs a reflash to
  match.
- **The procedural axis stays unadopted.** `ssn:System` and `ssn:hasSubSystem` are the right terms
  the day something needs them, and `ag:senseMode`'s values are `sosa:Procedure`s by definition —
  a cheap alignment that belongs with whatever next touches
  [who-holds-the-clock](who-holds-the-clock.md).
- **A principal is assumed to send one message.** It is one connection, which is not the same
  thing: a client may publish on several topics, and `_aimed_with` already groups by command topic
  rather than by client. Whether a principal needs sub-channels is undecided and nothing yet
  forces it.
