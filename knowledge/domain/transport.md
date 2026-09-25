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

**Not a driver.** A driver is chosen per sensor and answers *how is this device spoken to*; in Agent 0.2.0 the contract it implements (`agent/sensing/driver.py`) is claim, subscriptions, own, cadence and nudge, and no `parse` — bytes to number is sensing's pipeline, and a driver hands sensing the bytes and the sensor;
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
those mounted in what it acts for, and their topics' patterns are its subscriptions. One class,
`Mqtt`, over a client the container connected: it answers sensing's driver contract, `open`
subscribes what the world implies, and `handle` is the listener, one call of sensing's `received`
per sensor of the agent's whose pattern matches the message's topic, `received` reading the codec,
the pointer and the scaling off the sensor's own binding. The driver sets no callback: a message
arrives on the client's network thread, and the container enqueues it for the one executing thread.
The broker's address and the agent's credentials stay in the environment, and no host or port is
read off the world. The words
`MessageBus`, `readingTopic`, `commandTopic`, `Channel`, `publishesOn` and `listensOn` are the 0.1.0
package's, and 0.2.0 speaks none of them.
