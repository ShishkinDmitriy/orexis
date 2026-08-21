---
type: Decision
title: A stream is a thing, and the encoding is its rather than its sensors'
description: >-
  A channel is derived from the topics devices already state, one node per distinct topic,
  with an IRI minted as a function of that string — because `$given` excludes the derived
  graph, so two packages can only agree on a node by computing it independently. The codec
  moves off the sensor onto the stream, which closes a hole that was really open: one device
  on a shared topic claiming CBOR while its neighbours claimed nothing validated clean on main
  and is refused now. Moving the credential to the board did not follow, and the reason is a
  collision worth reading.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

[the-wire-is-ours-and-it-has-two-levels](the-wire-is-ours-and-it-has-two-levels.md) said the
encoding belongs to the stream and left the stream undeclared: *"`mqtt:readingTopic` is still a
literal, and until a stream is a thing the shape that would refuse two encodings on one has
nothing to target."*

This builds it.

# Decision — one node per distinct topic, minted from the topic

`transports/mqtt/rules.ru` derives an `mqtt:Channel` for every topic a device states, and
`mqtt:publishesOn` / `mqtt:listensOn` for who sends and who receives on it. An author restates
nothing: the topics were already there, and the node is the conclusion drawn from them.

Measured, because grouping is the whole point: `sensing` derives **two** channels used by three
sensors each — one board publishing once and listening once. `society` and `simulation` derive
twelve apiece, one per topic, with no platform between them.

## The IRI is a function of the topic, and that is forced rather than chosen

`$given` is public **minus** the derived graph, so a rule may never read another rule's
conclusions — the invariant `genesis.substitute` exists to hold. Which means
`codecs/json/rules.ru` cannot see the node `transports/mqtt/rules.ru` mints. It computes the same
expression from the same topic instead, and the two name the same node because **arithmetic
agrees, not because one ran first**.

That rules out the alternatives rather than merely losing to them. A blank node gives two
solutions two nodes, and the sensors sharing a stream stop sharing it. A counter needs an order,
and nothing here is ordered.

`ENCODE_FOR_URI` rather than a prettier slug: replacing `/` with `.` would collide with a topic
containing a literal `.`, and a collision here would silently **merge two streams**. A derived
node has to be stable and distinct; nothing looks one up by name, which is the same argument
`review/summary.py` makes for minting a summary's IRI from a subject URI.

## Direction is on the relation, not on the channel

A stream is one thing however many parties read it. Putting read/write into the identity would
split one topic into two nodes the moment a device both sent and listened on it — and the
direction is already a property of the *use*, which is why `Principal.grants` has been a set of
`(read|write, topic)` pairs since [series-and-bus-isolation](series-and-bus-isolation.md).

# The hole was real, and the first measurement of it was not

`codec:decodedBy` moved from the sensor to the channel. Three sensors sharing a topic carried
three copies of one fact with nothing comparing them; now the stream carries it once and
`codec:ChannelIsDecodedByExactlyOneShape` refuses a second.

**Silence is a claim, not an absence.** A device that states nothing is stating JSON — the
default is a fact this package asserts, not a gap. So a stream carrying one device that says CBOR
and another that says nothing has *two* claims on it and the world is refused. That reading is
deliberate: two devices disagreeing about the format of one stream is the error, however quietly
one of them disagrees.

**The methodological part is worth more than the fix.** The hole had been reported as measured,
and the measurement was wrong twice over:

- the probe mutated `ag:air_temp_fern` in the **society** world, where no such sensor exists, so
  it asserted a triple about nothing and observed that nothing happened;
- re-running the rules over a store `genesis_store` had **already derived once**, without
  clearing the derived graph, leaves the old conclusion beside the new one — so a sensor showed
  two codecs and the shape fired for a reason that had nothing to do with the change.

Cleared and re-derived against the world that actually shares a topic, the result is
**ACCEPTED on `main`, REFUSED here**. The hole was real; the evidence for it had not been. A
derivation test that does not clear before recomputing is asserting the union of two answers, and
`test_capabilities._world_with_push_sensor` carries the same warning for the same reason.

## Three tests were rewritten, not relaxed

They encoded the sensor as bearer, which this change invalidates on purpose. One of them asserted
that a probe could take CBOR while its neighbours on the same wire stayed JSON — **it was
asserting the defect**. It now states the premise on every device of the stream, and the
disagreement it used to permit has a test of its own.

The count of derived `codec:decodedBy` in `sensing` falls from three to two, which is the change
stated as a number: three sensors, two streams.

# What did not happen: the credential stayed where it was

[#81](https://github.com/ShishkinDmitriy/agora/issues/81) — the ESP32 authenticating as its own
soil probe while its own credential sits unused — was attempted here and **reverted**, because it
collides with a property this project already holds.

`tests/test_isolation.py::test_two_worlds_that_share_a_device_share_its_credential` asserts that
`world/sensing` and `world/society` share device principals, *"so one flashed board works in
either"*. A device credential is deliberately not world-scoped, and that is
[series-and-bus-isolation](series-and-bus-isolation.md)'s doing.

Moving `mqtt:onBus` onto the board makes `sensing`'s only device principal `esp32_fern`, while
`society` — which states no hardware and therefore no board — keeps three sensor principals. The
intersection becomes empty and a board flashed for one world cannot authenticate in the other.

Both positions are right, which is what makes it a collision rather than a bug:

- **the wire record's**: the thing that connects is the principal, and a peripheral that connects
  to nothing should not hold a credential;
- **the isolation record's**: a device credential names a device, not a deployment, so the same
  board serves either world.

They only conflict because the two worlds now disagree about *what the device is* — a board
carrying three sensors in one, three independent sensors in the other. That divergence arrived
with [a-board-is-a-platform](a-board-is-a-platform.md) and nothing has decided whether it is a
modelling accident or a real difference between a wired world and a simulated one. Deciding it is
the prerequisite for #81, and it is not a decision to take inside a change about streams.

# Consequences

- **The wire is now two levels in the graph, not only in prose.** A stream is a node; what it
  carries is one encoding; the shape says so.
- **The encoding reaches where a sensor could not.** A command channel has no sensor, so a
  sensor-borne encoding could never describe what an agent *publishes* to a board — the path
  `codec:Json.encode()` was written for and nothing has reached.
- **Nothing on the wire moved.** Broker grants are byte-identical to `main` across all three
  worlds and the compose files regenerate unchanged, which is the evidence that this was a
  modelling change and not a deployment one.

# Seams left open

- **#81 is blocked on a question, not on effort**: whether `sensing` and `society` describing the
  same board differently is a difference worth having. Until that is answered the ESP32 keeps
  authenticating as its probe and keeps a second credential with no grants.
- **`_aimed_with` still compares topic strings.** It could ask the channel now, in every world
  rather than only the wired one — [#78](https://github.com/ShishkinDmitriy/agora/issues/78) —
  and was left alone because the wake policy it implements is the subject of that issue and
  changing both at once would make neither reviewable.
- **A channel is derived by the MQTT package**, so the class lives with the transport whose
  topics are its premise. A REST binding would derive its own from URLs, and the day that exists
  is the day `mqtt:Channel` is worth hoisting to the kernel.
- **`ag:Principal` was not built.** The wire record names it and nothing declares it; with the
  credential move reverted there was nothing for it to bear that `mqtt:onBus` does not already say.
