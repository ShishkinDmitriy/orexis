---
type: Decision
title: A name does not expire, and an address did — three times
description: ag:lanAddress held a DHCP lease and its own comment called it "a fact with an expiry date". It expired three times; the third silently took the bench off the air for a day, because the board went on dialling an address that was no longer the Pi and the broker logged nothing, since nothing arrived. The term is ag:lanHost now and the world states raspberry.local. No firmware code changed — mqtt.setServer has always taken a name — and ESP32's lwIP resolves .local because the framework sets CONFIG_LWIP_DNS_SUPPORT_MDNS_QUERIES.
status: accepted
stage: v1
tags: [world, deployment, firmware, network, hardware]
timestamp: 2026-08-12T00:00:00Z
---

# What happened

The bench stopped reporting and nothing said so. The agent's last reading was 03:23; it was found
seventeen hours later, by looking.

```
.130:1884   unreachable      <- what the board's config.h dialled
.133:1884   OPEN             <- where the broker actually was
```

The Pi's DHCP lease had moved for the third time — `.126`, then `.130`, then `.133`. The board
opened TCP to an address that is no longer this machine, failed with a bare "connection failed",
and **the broker logged nothing at all, because nothing arrived**. Every other participant was
unaffected: agents reach the broker on loopback via `mqtt:brokerHost`, and only a board off-host
uses this fact.

The old term's own comment had predicted it — *"It is also a DHCP lease unless the router is told
otherwise, which makes it a fact with an expiry date"* — and named the remedy as a DHCP
reservation. A reservation makes the lease stop moving. It does not make the world stop caring
whether it does, and the reservation was never made.

# What was decided

**`ag:lanAddress` is `ag:lanHost`, and a world states a name.**

```turtle
ag:raspberry a ag:ComputeHost ; ag:lanHost "raspberry.local" .
```

A name does not expire. Nothing in a world can be true about an address a router is free to
reassign, so the rename is not cosmetic — it is the difference between a fact and a guess with a
half-life. It also matches `mqtt:brokerHost`, which has always held a *host* rather than an
address.

**No firmware code changed.** `mqtt.setServer(MQTT_HOST, MQTT_PORT)` has always taken a name;
`config.h` is generated, and it only ever held an address because the world stated one. The
generator now writes `raspberry.local:1884`, and the build was proved rather than assumed —
`pio run` links and produces an image, 59.3% of flash.

**`.local` resolves from the board**, checked rather than hoped: the framework this project builds
against sets `CONFIG_LWIP_DNS_SUPPORT_MDNS_QUERIES`, so `WiFi.hostByName` answers `.local` through
lwIP, and `avahi-daemon` is already running on the Pi that serves it. Both `raspberry.local` and
the router's own `raspberry.speedport.ip` resolve to the same address today.

**The router's domain is the fallback and not the default.** It works over ordinary unicast DNS
and needs no multicast, which makes it the thing to reach for if a network blocks mDNS — but it
couples a world to a brand of router, and a world should not know what the router is called.

An address remains a legal value. Some networks have no name service, and stating one there is
choosing to own the consequence.

# Seams left open

- **The board has not been flashed.** The image is built and correct; no ESP32 was connected. Until
  it is, the bench is still dialling `.130` and still silent.
- **The DHCP reservation is still worth making.** This removes the world's dependence on the lease;
  it does not stop the lease moving, and something else on that network may care.
- **Nothing notices a silent sensor.** Seventeen hours passed with no reading and no complaint.
  That is [#53](https://github.com/ShishkinDmitriy/agora/issues/53), and this is the first time it
  has actually cost something.
