---
type: Decision
title: A package brings its own dependencies as an extra, and an agent's image installs the extras of the packages it loads
status: accepted
timestamp: 2026-11-01T14:00:00Z
description: >-
  The sovereign's ruling of 2026-11-01 - the core has a minimal set of dependencies, and a package may
  bring its own. The distribution's dependencies are the kernel's alone, pyoxigraph and rdflib; a package
  of agent/ that imports a library declares it as an extra named for its directory, transport-mqtt for
  paho, belief for pyparsing, as do the series writer, the simulator and onboarding. tests/test_projects.py
  holds the core to the kernel's imports and each extra to its unit's, both ways. orexis-compose builds
  each agent's image with the extras of every package it loads and every package those import, tagged by
  them, and the runtime refuses a loaded package whose library is missing by naming the extra. Refused - a
  distribution per package, one image carrying every library, and the standard library alone as a rule.
---

# The question

Every agent's image installed one list: `pyoxigraph`, `rdflib`, `pyparsing`, `paho-mqtt`,
`influxdb-client`, `cryptography` and `python-dotenv`. The MQTT client was in the container of an agent
on no bus, and `cryptography` and `python-dotenv`, imported by onboarding alone, in every agent's. Telegram,
email, HTTP and the model client had been written on the standard library so as to add nothing, which was a
habit and no rule. The sovereign asked for something structural: a core with a minimal set, and a package
allowed to bring its own.

# What was decided

**The core is the kernel's.** The distribution's `dependencies` are what `agent/*.py` imports — the
store's engine and rdflib — and nothing else.

**A package brings a library as an extra named for its directory**: `transport/mqtt` is
`orexis[transport-mqtt]`, `belief` is `orexis[belief]`. Three units beside the packages do the same: the
kernel's series writer, `series`, which imports its client only where a store is named; the simulator; and
onboarding, which runs every package's code and so carries belief's. `dev` carries every extra, so a
developer's environment and CI run every test. `tests/test_projects.py` holds the core to the kernel's
imports and each extra to what its unit imports beyond the core, both ways, so an extra cannot outlive its
last import or a package import what it does not declare.

**An agent's image installs what its packages bring, and nothing else.** `orexis-compose` reads which
packages an agent loads, closes them over the packages their code imports — planning runs belief's
transition machine, so a planner carries belief's extra — adds the series writer's where the installation
serves a store, and writes the service's build with those extras, its image tagged by them. Two agents
loading the same packages share an image; the terrace runs `orexis:local-belief.series.transport-mqtt`,
hanoi `orexis:local-belief.series`. The `Containerfile` takes them as `EXTRAS`.

**A library missing is refused by name.** A loaded package whose library the install lacks stops the boot
saying which extra brings it, rather than a `ModuleNotFoundError` from inside a member's `connect`.

# What was refused

- **A distribution per package**, each directory its own `pyproject.toml`. It is the most separate, and it
  would turn one tree into twenty-odd projects to version and install together, which is what 0.1.0 had
  and retired ([one-tree-and-one-mechanic](/decisions/one-tree-and-one-mechanic.md)). An extra is the
  packaging standard's own way for one distribution to carry optional parts.
- **One image carrying every library.** It was the arrangement, and it is what the ruling refuses: each
  agent holding code its roles never run, and the image growing with every package anyone adds.
- **The standard library alone, as a rule.** It keeps a thin HTTP member to one `urllib` call, and it stays
  the habit for those; as a rule it would forbid a wire, a serial line or a vision library, which need
  what the standard library has not.

# Seams left open

- **System packages.** An extra carries Python distributions; a transport over a serial line or I2C may
  need a device node or a system library, which no extra installs.
- **Versions.** Extras pin lower bounds as the core does; no lock file holds an image to one resolution.
