---
type: Decision
title: The wire is ours, and it has two levels — the connection and the stream
description: >-
  A codec and a credential are facts about the wire rather than about a board, but not about
  the same part of it: a credential belongs to the connection and an encoding to the stream,
  because a transport and a codec vary independently — JSON over MQTT or over REST. SOSA gives
  the physical decomposition and SSN the procedural one, and neither says anything about
  transmission, so the wire is the project's own. Which means a simulated world correctly has
  no platforms, and scaling was never a wire fact at all.
status: accepted
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

# Five distinctions, and the wire is two of them

| | question | bearer |
|---|---|---|
| **physical** | what is mounted on what — which things share a rail, a wake, a radio | `sosa:Platform` |
| **procedural** | what implements what | `ssn:System` |
| **transport** | how bytes get here — MQTT, REST, serial | the **principal**: one credential, one connection |
| **encoding** | what those bytes mean — JSON, CBOR, a binary format | the **stream**: one channel, one encoding |
| **measurement** | what the number means | the **sensor**: pointer, scaling, unit |

Two structural decompositions, and three properties bound at three different levels.

**Transport and encoding are orthogonal**, which the first draft of this record got wrong by
calling them one axis. Any codec over any transport: JSON over MQTT, JSON over REST, CBOR over
MQTT. Neither constrains the other, so one name over both hides the fact that they are chosen
separately — the deployment picks the transport, the firmware picks the encoding.

**And scaling is on neither.** It is a fact about the *measurand*, not the message: the same probe
read over a serial cable would need the same curve and the same unit. That is why it derives onto
the sensor and always did, and it means the reading pipeline straddles two worlds rather than
being three stages of one:

```
bytes ─[codec]→ document ─[pointer]→ raw  │  ─[scaling]→ quantity
        the message's                     │    the measurand's
```

The wire is ours because nobody standardises it. The SSN specification has **no guidance** on
how hosting or sub-system composition affects the way observations are communicated — checked,
not assumed. That is deliberate: SOSA and SSN model the world and the instruments, not the wire.

So the relation between the axes is **constraint, not determination**. Physical decomposition
tells you what *could* share a message: one radio can only send one at a time. What *does* share
one is a fact about the binding, and a board with one radio could publish on three topics without
contradicting anything physical. That is why the topic question in
[#51](https://github.com/ShishkinDmitriy/orexis/issues/51) was not derivable from the hardware and
had to be settled against the credential model instead.

# Decision — the credential is the principal's, the encoding is the stream's

**`ag:Principal`** — the thing that holds one credential and one connection — bears the transport
and the bus. It is derived from `mqtt:onBus`, which every world already states, so this is a name
for something that exists rather than a new requirement on an author.

**The encoding is not the principal's.** A principal may hold several streams, and
`moisture_sensor_fern` already holds two: a reading topic it writes and a command topic it reads.
One encoding per *connection* is a claim nobody would defend; one encoding per *stream* is exactly
the thing worth refusing to break. So the codec belongs to the **channel**, and the channel
belongs to a principal.

Deriving the codec onto the principal would be **right by accident** — today one principal happens
to have one reading stream — and wrong by construction. The first draft of this record said
principal, and its own last seam said why that could not be the end of it.

## A channel is a string, which is the same defect one level down

`mqtt:readingTopic` is a literal. The stream it names has no node, so nothing can say *this stream
is JSON* — exactly as nothing could say *these sensors share a wake* before
[a-board-is-a-platform](a-board-is-a-platform.md), and for the same reason: the thing the fact is
about was never declared. `_aimed_with` recovering a group by comparing topic strings is the same
symptom.

The shape of the answer is already visible in the code. `onboarding/mqtt.py` holds
`Principal.grants` as `set[(read|write, topic)]` — **a set of directed channels.** The ACL is not a
list of permissions bolted onto a connection; it is that connection's stream list, written in the
form mosquitto wants. Which makes [#81](https://github.com/ShishkinDmitriy/orexis/issues/81)'s
*"a peripheral's topics roll up into its board's grants"* a consequence rather than a rule.

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
  [#59](https://github.com/ShishkinDmitriy/orexis/issues/59) needs for a board's honourable
  interval range, and what gives the DHT11's two channels a parent. It is not diminished by not
  carrying the wire.
- **[#78](https://github.com/ShishkinDmitriy/orexis/issues/78) gets a bearer too.** A wake is one
  connection waking, so `_aimed_with` comparing command-topic strings could ask the principal
  instead — in every world, not only the wired one.
- **A third kind of node joins the model**, after the agent and the sensor. Worth watching that it
  stays what it says: the thing that connects, not a general-purpose grouping to hang facts on
  because it happens to be convenient.

# Seams left open

- **Half is built.** The channel exists and the codec moved onto it. `ag:Principal` does not:
  moving the credential onto the board collides with a property
  [series-and-bus-isolation](series-and-bus-isolation.md) holds — that one flashed board works in
  either world — and the collision is described in [a-stream-is-a-thing](a-stream-is-a-thing.md)
  rather than resolved.
- **The firmware's identity is wrong and unfixed.** Filed rather than folded in, because changing
  which principal a board connects as rewrites its credential and its ACL — the regression class
  that [#62](https://github.com/ShishkinDmitriy/orexis/pull/62) belongs to — and needs a reflash to
  match.
- **The procedural axis stays unadopted.** `ssn:System` and `ssn:hasSubSystem` are the right terms
  the day something needs them, and `sensing:senseMode`'s values are `sosa:Procedure`s by definition —
  a cheap alignment that belongs with whatever next touches
  [who-holds-the-clock](who-holds-the-clock.md).
- ~~**A channel is not a node yet.**~~ **Built** in
  [a-stream-is-a-thing](a-stream-is-a-thing.md): one node per distinct topic, derived from what
  devices already state, with the encoding on it and a shape refusing a second. The hole this
  record predicted turned out to be real — accepted on `main`, refused now — though the evidence
  first offered for it was not, which that record explains.
