---
type: Process
title: Onboarding
description: >-
  The phase between a ratified world and a society that can be started - a bucket and a token per
  agent, where the world has a bus a broker credential per principal and the ACL derived from the
  wiring, a compose file, the dashboards, and a board's config. Every grant is read off the world
  as an agent boots it, so re-running it is safe and adding an agent is the whole of deploying one.
---

# What it grants

`orexis-onboard <world>` runs the four that make a society startable, each where the world has
what it serves; each stays callable alone, since rotating one service's credentials should not
touch another's.

| command | grants |
|---|---|
| `orexis-influx` | per agent, a history bucket, and a metrics bucket where the world is monitored, in the store serving each purpose, each with a token that opens only it, in a credential file named for its purpose |
| `orexis-mqtt` | where the world has a bus, a credential per principal on the broker, a certificate per agent, and the ACL derived from the wiring — then reloads the broker, so connected agents keep their sessions |
| `orexis-compose` | `world/<name>/compose.yaml`: one container per agent, the world mounted beside the domains, the series store's address as environment keyed by purpose, and where the world has a bus the broker's service, its address, and each agent's broker credential and certificate; an agent that finishes is not restarted |
| `orexis-dashboards` | a Grafana folder for the world: what its agents observe, and where the world is monitored a health dashboard, a row per package that reports and the agent a variable |

`orexis-firmware <world>` writes a board's `config.h` from the same documents: the broker's port off
the `schema:url` on the world's `mqtt4ssn:Broker`, asserted or allocated, the topics in the
society graph's MQTT4SSN words, the pins from the world's hardware graph, the credential
`orexis-mqtt` minted.

**A step runs where the world has what it serves.** History is every agent's, so every world is
granted it, and metrics are where the world says it is monitored. The **bus** is a broker the
world's society names — a premise read off the world, an ASK over its public graphs in `PREMISES`
of `onboarding/reading.py`, the shape the runtime gives a package's. A world naming none — hanoi,
the courier, the tower — is onboarded without the MQTT step, which says in one line that it was
skipped, and its compose file holds its agents and nothing of a bus; `orexis-mqtt` run on it grants
nothing and says so. `broker` still refuses an address such a world does not have, so the tools ask
the premise and never it. Until they did, every tool asked `broker`, and a world with no bus could
be neither onboarded nor run in a container.

**Whether an agent is restarted is read off the agent.** The [runtime](/domain/kernel/runtime.md)
lets an agent finish that holds no desire and that no transport reaches, so `orexis-compose` boots
each agent from the documents as its container would (`lasts` in `onboarding/reading.py`) and asks
the runtime's two questions of it. One that lasts is written `restart: unless-stopped`; one that
finishes — hanoi's, the courier's, the tower's mover — `restart: "no"`, since restarted it would
find nothing to pursue and exit again, over and over. Per agent and not per world, because a
desire is in an agent's own graphs.

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
reader declares. Its own read of a world passes over onboarding's kinds before reading them, and
says so at DEBUG; a kind no reader declares is still said at INFO where it is passed over.

# Why it lives outside the agent

`orexis-influx` holds the admin token that opens every bucket, which no agent may ever hold. The
surest guarantee is that the code using it is absent from the image: `onboarding/` sits beside
`agent/`, the Containerfile does not copy it, a layout test fails if it ever does, and
`lint-imports` holds the direction — onboarding may import the agent, never the reverse.
