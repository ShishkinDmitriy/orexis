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
| `orexis-influx` | a history bucket per agent on the series store, and a token that opens only it, in a credential file named for its purpose |
| `orexis-mqtt` | a credential per principal on the broker, and the ACL derived from the wiring — then reloads the broker, so connected agents keep their sessions |
| `orexis-compose` | `world/<name>/compose.yaml`: one container per agent, the world mounted beside the domains, the broker's address and the series store's as environment, the store's keyed by purpose |
| `orexis-dashboards` | a Grafana folder for the world, from what its agents observe |

`orexis-firmware <world>` writes a board's `config.h` from the same documents: the broker's port off
the `schema:url` on the world's `mqtt4ssn:Broker`, asserted or allocated, the topics in the
society graph's MQTT4SSN words, the pins from the world's hardware graph, the credential
`orexis-mqtt` minted.

**Derived before it is rendered.** `orexis-onboard` first completes what the documents leave out:
a broker whose world asserts no url is allocated one by the installation, into a derived
[deployment](/domain/onboarding/deployment.md) graph, and the four above only format what is
asserted and derived — none computes a port. The series store's address comes from the
installation (`infra/installation.ttl`) too, and `orexis-infra-compose` writes the shared services'
own compose file from it, alongside `orexis-infra-certs` and apart from onboarding.

**One broker, one address.** The compose file and the config are each handed a single address, so
a world stating a second `mqtt4ssn:Broker`, or one broker whose urls disagree on a host or on a
scheme's port, is refused and named rather than merged (`broker` in `onboarding/mqtt.py`).
How several would reach an agent is the first seam of
[a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md).

# Nothing here decides

The ACL is the wiring: an agent reads the topics of every sensor hosted by what it acts for and
writes the topic its devices listen to; a board writes what its sensors publish on. That is the
same set the MQTT member subscribes to and publishes on, so if the two ever differ an agent fails to
connect — which is the point of deriving it. The roster is the world's `orexis:Agent`s. The one
choice made here is a port no world asserted, and it is made once: the allocation is kept, so
re-running changes nothing, and a sovereign who cares asserts the port instead. The world is
read as the [runtime](/domain/kernel/runtime.md) boots it, so onboarding refuses a world whose documents
will not load.

# What it reads that no agent does

Onboarding reads a world as the runtime boots it, and then the kinds no agent reads, declared in
a vocabulary of onboarding's own (`onboarding/ontology.ttl`, read by `onboarding/reading.py`) so
that the agent never names them and the import direction holds. The
[deployment](/domain/onboarding/deployment.md) graph is one. The **hardware graph** is the other:
the boards, pins, parts and wire colours `orexis-firmware` interpolates into a `config.h`, which
`hardware.ttl` says it is. The graph has a kind; the parts inside it stay untyped, since a
vocabulary one string-filling reader uses checks nothing.

An agent's boot passes over both, and `orexis-compose` mounts a document into a container only
where the agent's own vocabulary declares its kind — so the hardware is in no agent's store and
no container's filesystem, and nothing names the file. Every reader passing over what it does not
declare makes a misspelled kind silent everywhere, so `orexis-onboard` checks every graph a world
holds against every reader's vocabulary first, and grants nothing to a world holding one no
reader declares.

# Why it lives outside the agent

`orexis-influx` holds the admin token that opens every bucket, which no agent may ever hold. The
surest guarantee is that the code using it is absent from the image: `onboarding/` sits beside
`agent/`, the Containerfile does not copy it, a layout test fails if it ever does, and
`lint-imports` holds the direction — onboarding may import the agent, never the reverse.
