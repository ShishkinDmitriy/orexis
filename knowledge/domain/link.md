---
type: Component
title: Link
description: >-
  How an agent reaches its society: the kernel contract a transport package implements —
  find the meeting place in the world in your own words, connect with three callbacks, speak
  in named channels, say whether you are alive. The runtime holds one and knows nothing of
  brokers; `packages/transport/mqtt/link.py` is the one that ships. Not a driver, which is how
  sensing reaches one device.
---

# What it is

`agent/link.py` — the contract:

| | |
|---|---|
| `where(query)` | this transport's link in the world the query answers about, or None — asked of every transport loaded, and exactly one must answer |
| `connect(on_up, on_down, on_message)` | open it; the runtime's three callbacks are the whole of what it hands over |
| `subscribe(channel)`, `publish(channel, payload, retain)` | speak in named [channels](/domain/channel.md) — strings the society agrees on |
| `alive()` | a pulse for the watchdog, or None where the transport cannot see its own machinery |
| `stop()` | close it |

`MqttLink` implements it: the `mqtt:MessageBus` the world states, the password and
certificate doors, the environment names the credential arrives under, paho, and paho's loop
thread as the pulse. It is found through `PROVIDES`, beside the same package's driver.

# What it is not

**Not a [driver](/domain/sensing.md).** A driver is chosen per sensor — *how is this device
spoken to* — and grants nothing; a link is chosen per world — *how does this agent reach
everyone*. MQTT ships both, and a wired transport could ship a driver alone.

**Not the meeting place.** The bus is a fact in the world, stated in the transport's
vocabulary; the link is the code that reaches it. The kernel never learns what the fact is
called ([the-link-is-the-transports](/decisions/the-link-is-the-transports.md)).
