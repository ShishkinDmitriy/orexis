---
type: Decision
title: The kernel has no mailbox — reaching the society is a capability the fact of a bus grants
description: >-
  The runtime held a paho client, a loop that handed every message to every module, a
  `subscriptions`/`handle`/`publish` contract on `Module`, a watchdog on the session and the
  session's figures in the health series — the last package words the kernel spoke, and
  behind them a concept that is not BDI at all. Decided: how an agent reaches its society is a
  capability like any other, with interchangeable implementations, granted to every agent by
  the fact of a bus in the world; the transport's module holds the connection, the delivery
  loop and the watchdog, and speaks to the rest of the agent through the choir alone. A
  first cut kept a `Link` contract in the kernel; the sovereign asked why the core should know
  about transport at all, and it should not.
status: accepted
timestamp: 2026-08-25T20:00:00Z
---

# What was true before

[the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md) reached zero
everywhere but the bus. `agent_old/world.py` asked the world for `mqtt:MessageBus`; `agent_old/runtime.py`
built a paho client, read the MQTT credential off the environment, subscribed to what every
module's `subscriptions()` returned and offered every message to every module's `handle()`;
`agent/watchdog.py` reached for paho's private thread; `agent_old/metrics.py` reported
`mqtt_connected`; and `Module` carried `subscriptions`, `handle` and `publish` as kernel
hooks. The transport package held only a DRIVER — how sensing reaches one device.

A first cut (`Link`, `link_for`) moved the vocabulary out and left the concept in: the kernel
still believed it had a connection, channels and a pulse. The sovereign's question — *why
should the core know about transport?* — has one honest answer. A BDI engine perceives and
acts through capabilities; how bytes move is a capability, and [rule 2](/domain/capability.md)
already says what that means: a named ability with interchangeable implementations, granted
by the fact that makes it meaningful.

# What is decided

**Reaching the society is a capability, and the fact of a bus grants it.** `mqtt:Linking`, a
`orexis:Capability`, derived by the transport's own `rules.ru` for every agent in a world that
states an `mqtt:MessageBus` — as a polled sensor grants Subscribing. There is no choosing: an
agent in a society that meets on a broker is on the broker. It is found as every capability is
(`PROVIDES`, `registry_for`), and the loader's ownership map covers a transport's namespace as
it covers a capability's.

**The transport's module holds everything the kernel used to.** `packages/orexis-transport-mqtt/module.py`:
the `mqtt:MessageBus` query, the two doors and the credential's environment names, paho, the
delivery loop, the session's figures (`link_connected`, `link_reconnects`, through
`reports()`), and the watchdog — `packages/orexis-transport-mqtt/watchdog.py`, the same rule
[a-dead-session-is-resigned-not-endured](/decisions/a-dead-session-is-resigned-not-endured.md)
states, now beside the session it watches.

**It speaks to the rest of the agent through the choir.** Three hooks, the transport's to
state and any module's to answer:

| hook | asked by | meaning |
|---|---|---|
| `subscriptions()` | the transport, once the session is up | which channels do you need |
| `handle(channel, payload)` | the transport, per message | take this if it is yours; nobody taking it is logged |
| `send(channel, payload, retain)` | `Module.publish`, told | carry this to the society |

`Module` keeps `publish` as a convenience that tells `send`; it defines nothing else about
messaging. The runtime builds the mind, loads the modules, starts them, waits for a signal,
and never learns a message exists.

**Reachable is the transport's word.** "One device, one stand-in" stays a kernel shape;
"reachable — on a bus, or sharing a reading topic" left for the transport. (AMENDED: it is
`sim:StandInReachableShape` now. Reachable is still the transport's WORD, but the rule is the
simulation's — a stand-in nothing can reach is a stand-in for nothing — and filing it under the
transport meant replacing the transport would delete it in silence. See
[a-shape-belongs-to-the-vocabulary-it-checks](/decisions/a-shape-belongs-to-the-vocabulary-it-checks.md).)

# What did not change

- **Channel names** — strings the society agrees on; the sovereign channel's topic shape (reporting's, since [metrics-are-an-aspect](/decisions/metrics-are-an-aspect.md)) is a
  naming convention read by the ACL generator too, not a transport.
- **The ACL and the credentials** — `orexis-mqtt` mints them as before; only their reader
  moved. [series-and-bus-isolation](/decisions/series-and-bus-isolation.md) is untouched.
- **The watchdog's rule** — a corpse over a stale flag, a bound from `orexis:resignAfterS`, a
  resignation through SIGTERM. Its home moved; its text did not.
- **Every other module's `subscriptions` and `handle`** — unchanged in body; only who calls
  them changed.

# Seams left open

- **Two transports, one world.** `registry_for` would grant both; nothing routes a channel
  to one of them. `mqtt:onBus` is the beginning of that fact, on the device side.
- **Onboarding knows the transport's credential names.** `onboarding/compose.py` sets
  `MQTT_USERNAME`; a second transport would need onboarding to ask the transport what its
  agents must be handed.
- **The simulated valve and devices speak paho directly.** They are stand-ins, not agents,
  and hold no module; whether they should is the simulation package's question.
- **Start order.** Modules start in package order and the transport connects in `start()`;
  a module publishing before the session is up relies on paho queueing QoS 1 — exactly as
  the runtime always did, and now stated.
