---
type: Runbook
title: Author a world
description: >-
  What to write in `world/<name>/` for a world an agent can boot - the world graph importing its
  domains, the state it starts from, each agent's desires or wants - and the test beside it that
  proves it does what it was written for. Onboarding and compose come after, for a world that
  runs in containers.
---

# What to write

A directory `world/<name>/`, and in it documents that each say which graph they are
([world](/domain/kernel/world.md)):

1. **`world.ttl`** — `<> a orexis:WorldGraph ; owl:imports <../../domains/…/ontology.ttl>`, then
   the agents (`a orexis:Agent ; orexis:localId "…" ; orexis:actsFor …`), the subjects, their
   [regions](/domain/sensing/region.md), the devices each agent `actuation:hasActuator`, the sensors
   and the topics in MQTT4SSN's words, and the venues who hosts and bids in.
2. **`state.ttl`** — `<> a orexis:StateGraph`, where things stand, for a world nothing senses.
3. **what each agent is for** — `<> a planning:DesireGraph` for standing desires, or
   `<> a planning:WantGraph` for a want that is met once; in a world of several agents, one
   document per agent under `beliefs/<id>.ttl`, since every desire a store holds is derived for.
4. **`hardware.ttl`** — `<> a onboarding:HardwareGraph`, pins and boards, if there are any: read
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

For a world of devices or several agents, [onboarding](/domain/onboarding/onboarding.md) grants the
credentials and writes the compose file: `orexis-onboard <name>`, then
[run-a-world](/runbooks/run-a-world.md).
