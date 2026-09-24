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
