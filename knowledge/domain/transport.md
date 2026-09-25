---
type: Capability
title: Transport
term: http://example.org/orexis/mqtt#Linking
description: >-
  How an agent reaches its society — a capability granted to every agent by the fact of a
  bus in the world, held by a module that owns the connection, the delivery loop and the
  watchdog, and speaks to the rest of the agent through three choir hooks: `subscriptions`,
  `handle`, `send`. The kernel has no mailbox. MQTT is the member that ships; a driver, how
  sensing reaches one device, is a different thing the same package may also hold.
---

# What it is

`packages/orexis-transport-mqtt/module.py` — `mqtt:Linking`, derived for every agent by the fact of
an `mqtt:MessageBus` in the world ([the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md)).
It finds the bus in its own words, opens the session with the credential `orexis-mqtt`
minted, subscribes to whatever the other modules ask for, offers every arriving message to
all of them, sends what any of them tells it to, watches its own session and resigns when it
is dead ([a-dead-session-is-resigned-not-endured](/decisions/a-dead-session-is-resigned-not-endured.md)),
and reports `link_connected` and `link_reconnects` into the health series.

# The hooks

| | |
|---|---|
| `subscriptions()` | asked of every module once the session is up — which [channels](/domain/channel.md) it needs |
| `handle(channel, payload)` | every message, to every module; nobody taking it is logged, because a topic disagreement looks exactly like a device that never speaks |
| `send(channel, payload, retain)` | what `Module.publish` tells, and this module carries |

# What it is not

**Not a driver.** A driver is chosen per sensor and answers *how is this device spoken to*; in Agent 0.2.0 the contract a transport implements is the family's own, `Transport` at `agent/transport/transport.py` — claim, open, handle, cadence, nudge, a step's command (`actuate`) and a document to a peer (`tell`), and no `parse` — bytes to number is sensing's pipeline, a transport hands sensing's `received` the bytes and the sensor, and sensing knows no transport;
this is chosen per world and answers *how does this agent reach everyone*. MQTT is both, in
one package; a wired transport could be a driver alone.

**Not the kernel's.** The runtime builds the mind, loads the modules, starts them and waits
for a signal. It never learns a message exists.

# In Agent 0.2.0, the MQTT transport speaks MQTT4SSN and declares nothing of its own

`agent/transport/mqtt/` adopts MQTT4SSN as it stands — the ontology that extends SSN and SOSA with
the MQTT protocol in the OASIS specification's own terms, vendored under `tests/fixtures/vocabularies/`
— the way the belief package adopted SHACL's rules. A board is a `mqtt4ssn:Client` that
`mqtt4ssn:hosts` its sensors and `mqtt4ssn:isConnectedToBroker` a `mqtt4ssn:Broker`; a sensor
`mqtt4ssn:observesTopic` the `mqtt4ssn:Topic` it publishes on; a board that takes commands
`mqtt4ssn:listensToTopic` another; and a topic is named only by the `mqtt4ssn:TopicFilter`s that
`mqtt4ssn:matchesTopic` it, each with its `mqtt4ssn:hasFilterPattern`, since a topic name is itself a
valid filter. The agent is a client too, and what it listens to is never authored: its sensors are
those mounted in what it acts for, and their topics' patterns are its subscriptions, beside the
topic it `mqtt4ssn:listensToTopic` itself, where a peer's document arrives for speech's `heard`. One class,
`Mqtt`, answering the family's `Transport` contract at `agent/transport/transport.py`: `connect`
brings it up from the environment — the broker's address, the agent's credential and its
certificate in this transport's own variables, refusing to guess either, with paho imported there
and nowhere else in the agent — `open` subscribes what the world implies, and `handle` is the
listener, one call of sensing's `received` per sensor of the agent's whose pattern matches the
message's topic, `received` reading the codec, the pointer and the scaling off the sensor's own
binding. A message arrives on the client's network thread, so `connect` hands it to the
container's `deliver`, which enqueues it for the one executing thread. No host or port is read off
the world; 0.1.0 read the bus's off the world as the one piece of infrastructure everyone must
agree on, and MQTT4SSN has `hasHostAddress` on a Broker, so that is a choice open to reversal.

**A seam, not a debt.** The member is not yet a distribution of its own with paho as its
dependency: the root declares paho because the runtime's own tree imports it through the member, and
`tests/test_projects.py` holds the root's list to its own trees' imports both ways, so paho leaves
the root only when the transport carries it. Whether the 0.2.0 packages become distributions, and
under what module names given that 0.1.0 abandoned a shared import root for flat top-level
modules, is genesis 0.2.0's question. The words
`MessageBus`, `readingTopic`, `commandTopic`, `Channel`, `publishesOn` and `listensOn` are the 0.1.0
package's, and 0.2.0 speaks none of them.
