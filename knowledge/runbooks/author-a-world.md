---
type: Runbook
title: Author a world
description: >-
  What to write in `world/<name>/` for a world an agent can boot - the world graph importing its
  domains, the society and deployment of a world with a bus, the state it starts from, each
  agent's desires or wants - and the test beside it that
  proves it does what it was written for. Onboarding and compose come after, for a world that
  runs in containers.
---

# What to write

A directory `world/<name>/`, and in it documents that each say which graph they are
([world](/domain/kernel/world.md)):

1. **`world.ttl`** — `<> a orexis:WorldGraph ; owl:imports <../../domains/…/ontology.ttl>`, then
   the subjects, their [regions](/domain/sensing/region.md), the sensors, devices and systems, and
   the venues. It speaks no MQTT4SSN. In a world with no bus, the one agent goes here too.
2. **`society.ttl`**, for a world with a bus — `<> a orexis:SocietyGraph`, then the agents
   (`a orexis:Agent , mqtt4ssn:Client ; orexis:localId "…" ; orexis:actsFor …`) with the devices
   each `actuation:hasActuator` and the venues each hosts or bids in, the boards as clients and
   what each `mqtt4ssn:hosts`, the one `mqtt4ssn:Broker` every client `mqtt4ssn:isConnectedToBroker`,
   and the topics, their filters, and which sensor `mqtt4ssn:observesTopic` and which device
   `mqtt4ssn:listensToTopic` each one.
3. **`deployment.ttl`, only to pin the broker's port** — `<> a onboarding:DeploymentGraph`, then
   the broker's `schema:url`s, `mqtt://` and `mqtts://`, one host. Leave it out and `orexis-onboard`
   allocates the broker a port free of every other world's, into `infra/installation.derived.ttl`;
   write it when something is flashed with the port, as the terrace's board is. A port another
   world holds is refused. Onboarding reads either to run the broker and to write each agent's
   environment; no agent loads them and no container mounts them.
4. **who each agent is** — `beliefs/<id>.self.ttl`, `<> a orexis:SelfGraph` and the one row
   `:fern_grower a orexis:Self`, for every agent the world states: an agent whose world authored
   none, or two, refuses to boot, and the boot checks this one against the id it is told
   ([self](/domain/kernel/self.md)). Beside that row, any figure the agent holds of itself — its
   patience, a budget, a sensor's limits, its horizon — as a triple about the self; stated in any
   other document it is not read ([stance](/domain/kernel/stance.md)).
5. **`state.ttl`** — `<> a orexis:StateGraph`, where things stand, for a world nothing senses.
6. **what each agent is for** — `<> a planning:DesireGraph` for standing desires, or
   `<> a planning:WantGraph` for a want that is met once; in a world of several agents, one
   document per agent under `beliefs/<id>.ttl`, since every desire a store holds is derived for.
   Every document of a kind that is an agent's own — the state, the desires, the wants — says whose
   beside its kind, `<> orexis:beliefsOf :fern_grower`; the file's name says nothing to any reader.
7. **`hardware.ttl`** — `<> a onboarding:HardwareGraph`, pins and boards, if there are any: read
   by `orexis-firmware`, and a kind no agent declares, so a boot passes over it and no container
   mounts it. A document of a kind no reader declares is refused by `orexis-onboard`.

State ranges, values and lots — picks. Never state a step, a dose or a price paid: those are
the agents' to find.

# Prove it

`world/<name>/tests/test_<name>.py` boots it — `Runtime(boot(WORLD, "<id>"), "<id>")` with a clock
that ticks — runs it and asserts what it was written for: the tower stands, the fern was served.
Run it with `pytest world/<name>`. A world the loader refuses fails here first, with the document
and the reason.

# Run it

To run it in containers, [onboarding](/domain/onboarding/onboarding.md) grants the credentials and
writes the compose file: `orexis-onboard <name>`, then [run-a-world](/runbooks/run-a-world.md). A
world with no bus is onboarded too — its compose file is its agents and nothing of a broker.
