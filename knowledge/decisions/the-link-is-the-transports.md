---
type: Decision
title: The link is the transport's — the kernel knows it meets its society somewhere, and never that the somewhere is a broker
description: >-
  The runtime held a paho client, asked the world for `mqtt:MessageBus`, read the MQTT
  credential off the environment and watched paho's private thread — the last package words
  the kernel spoke, held by the ratchet as debt. Decided: how an agent reaches its society is
  a kernel CONTRACT, `agent.link.Link`, and the transport package implements it and finds its
  own bus in the world in its own vocabulary; the kernel hands over three callbacks and speaks
  in channels. A link is not a driver — one is how the agent reaches everyone, the other how
  sensing reaches one device — and one package may ship both.
status: accepted
timestamp: 2026-08-25T18:00:00Z
---

# What was true before

[the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md) reached zero
everywhere but here. `agent/world.py` asked the world for `mqtt:MessageBus`, its host and its
two ports, before any package's Python had loaded; `agent/runtime.py` built a `paho` client,
read `MQTT_USERNAME`, `MQTT_PASSWORD` and the certificate paths off the environment, set TLS,
subscribed and published; `agent/watchdog.py` reached for paho's private `_thread` to tell a
corpse from a stale flag; `agent/metrics.py` reported `mqtt_connected`; and
`ag:SimulatedDeviceShape` said what makes a stand-in *reachable* in `mqtt:onBus` and
`mqtt:readingTopic`. The transport package, `packages/transport/mqtt/`, held only the
DRIVER — how sensing reaches one device over a topic — and nothing about how the agent
reaches its society at all. The ratchet listed the six references as its fifth kind, with
"the transport answering *where is the bus* itself" as what would remove them.

The sovereign asked for an abstraction at the agent's level.

# What is decided

**The kernel knows that an agent meets its society somewhere, speaks to it in named
channels, and needs to know whether the link is up. It knows nothing else.** That is
`agent.link.Link`: `where(query)` — find this transport's link in the world the query answers
about, in the transport's own words, or None; `connect(on_up, on_down, on_message)`;
`subscribe(channel)`; `publish(channel, payload, retain)`; `alive()` — a pulse, or None where
the transport cannot see its own machinery; `stop()`. The runtime holds a `Link` and hands it
three callbacks. `link_for(query)` asks every transport loaded and refuses none or two: a world
that states no meeting place is one nobody can join, and two are a routing question nothing
here decides.

**The transport implements it, and owns everything it used to lend the kernel.** `MqttLink` in
`packages/transport/mqtt/link.py`: the `mqtt:MessageBus` query, the password door and the
certificate door, the environment names the credential arrives under, paho itself, and the
private thread the pulse reads. `PROVIDES = (MqttDriver, MqttLink)` — the loader finds a link
as it finds a driver, by what the class can do (`where` against `claims`), and nothing lists
either.

**Reachable is the transport's word.** "One device, one stand-in" stays a kernel shape; "a
stand-in must be reachable like a real device — on a bus, or sharing a reading topic" is
`mqtt:SimulatedDeviceReachableShape`, in the package whose words it is in.

**A link is not a driver.** `agent.driver.Driver` is chosen per sensor and answers *how is this
device spoken to*; a link is chosen per world and answers *how does this agent reach
everyone*. They meet in one package because MQTT happens to be both, and nothing requires
that: a transport could ship a driver for a wired sensor and no link at all.

# What did not change

- **Channel names.** A channel is a string the society agrees on; `agent/sovereign.py`'s topic
  shape is a naming convention, not a transport, and the ACL generator reads it on the other
  side. What carries a channel is the link's business.
- **The ACL and the credentials.** `orexis-mqtt` still mints one credential per principal and
  the broker still enforces the ACL — [series-and-bus-isolation](/decisions/series-and-bus-isolation.md)
  is untouched; only the reader of the credential moved.
- **The watchdog's rule.** A corpse is believed over a stale flag
  ([a-dead-session-is-resigned-not-endured](/decisions/a-dead-session-is-resigned-not-endured.md));
  it now asks the link for the pulse rather than paho, and a link that cannot say degrades the
  check to never-true exactly as a renamed paho attribute did.
- **The health series.** `mqtt_connected` and `mqtt_reconnects` are `link_connected` and
  `link_reconnects`: the kernel counts, and what it counts is a link.

# Seams left open

- **Two transports, one world.** `link_for` refuses two answers. A society that meets on two
  buses, or on a bus and something else, needs routing — which channel goes where — and that
  is a world fact nothing states yet (`mqtt:onBus` is the beginning of it, on the device side).
- **The credential names are the transport's, and the compose generator writes them.**
  `onboarding/compose.py` knows to set `MQTT_USERNAME`; a second transport would need
  onboarding to ask the transport what its agents must be handed, the way it asks packages for
  everything else.
- **The simulated valve and the simulated devices speak paho directly.** They are stand-ins,
  not agents, and hold no link; whether they should is the simulation package's question.
