---
type: Process
title: Onboarding
description: >-
  The phase between a ratified world and a society that can be started - a bucket and a token per
  agent, a broker credential per principal and the ACL derived from the wiring, a compose file,
  the dashboards, and a board's config. Every grant is read off the world as an agent boots it,
  so re-running it is safe and adding an agent is the whole of deploying one.
---

# What it grants

`orexis-onboard <world>` runs the four that make a society startable; each stays callable alone,
since rotating one service's credentials should not touch another's.

| command | grants |
|---|---|
| `orexis-influx` | a bucket per agent on the series store, and a token that opens only it |
| `orexis-mqtt` | a credential per principal on the broker, and the ACL derived from the wiring — then reloads the broker, so connected agents keep their sessions |
| `orexis-compose` | `world/<name>/compose.yaml`: one container per agent, the world mounted beside the domains, the broker's address as environment |
| `orexis-dashboards` | a Grafana folder for the world, from what its agents observe |

`orexis-firmware <world>` writes a board's `config.h` from the same documents: the broker's port off
the `schema:url` on the world's `mqtt4ssn:Broker`, the topics in MQTT4SSN's words, the pins from
`hardware.ttl`, the credential `orexis-mqtt` minted.

# Nothing here decides

The ACL is the wiring: an agent reads the topics of every sensor hosted by what it acts for and
writes the topic its devices listen to; a board writes what its sensors publish on. That is the
same set the MQTT member subscribes to and publishes on, so if the two ever differ an agent fails to
connect — which is the point of deriving it. The roster is the world's `orexis:Agent`s. The world is
read as the [runtime](/domain/kernel/runtime.md) boots it, so onboarding refuses a world whose documents
will not load.

# Why it lives outside the agent

`orexis-influx` holds the admin token that opens every bucket, which no agent may ever hold. The
surest guarantee is that the code using it is absent from the image: `onboarding/` sits beside
`agent/`, the Containerfile does not copy it, a layout test fails if it ever does, and
`lint-imports` holds the direction — onboarding may import the agent, never the reverse.
