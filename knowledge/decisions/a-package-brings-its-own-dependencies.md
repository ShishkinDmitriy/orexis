---
type: Decision
title: A package brings its own dependencies in a file beside it, and each agent's image holds only what it runs
status: accepted
timestamp: 2026-11-01T14:00:00Z
description: >-
  The sovereign's ruling of 2026-11-01 - the core has a minimal set of dependencies, a package may bring
  its own, and each agent has its own image. The distribution's dependencies are the kernel's alone,
  pyoxigraph and rdflib; a package that imports a library says so in a dependencies.txt beside its
  ontology, which the pyproject reads as the package's extra, named for its directory, and a package with
  none is the core's. tests/test_projects.py holds the core to the kernel's imports and each file to its
  unit's, both ways. orexis-compose gives each agent an image of its own, holding the kernel, the packages
  it loads and those their code imports, and the libraries those bring, and mounts the same entries, so a
  container holds no code its agent does not run. Refused - a pyproject and a distribution per package,
  one image carrying every library and every package, and the standard library alone as a rule.
---

> **Amended, 2026-11-09.** The agent is the binary, so a package brings its libraries in its `Cargo.toml` and an image is a feature set.
> The argument below stands; the `dependencies.txt` files, the extras they fed and `agent.tree.kept` went with the Python agent.

# The question

Every agent's image installed one list: `pyoxigraph`, `rdflib`, `pyparsing`, `paho-mqtt`,
`influxdb-client`, `cryptography` and `python-dotenv` — the MQTT client in an agent on no bus, and onboarding's
own libraries in every agent — and copied the whole of `crates/`, so an observer's container held the planner.
Telegram, email, HTTP and the model client had been written on the standard library so as to add nothing, which
was a habit and no rule. The sovereign asked for a core with a minimal set, a package allowed to bring its own,
and then an image of its own for each agent.

# What was decided

**The core is the kernel's.** The distribution's `dependencies` are what `agent/*.py` imports — the store's
engine and rdflib — and nothing else.

**A package says what it brings in a file beside it**, `dependencies.txt` next to its ontology, and the root
pyproject reads each such file as the package's extra, named for its directory: `crates/orexis-transport-mqtt/` is
`orexis[transport-mqtt]`, `crates/orexis-belief/` is `orexis[belief]`. A package with no file is the core's and brings
nothing. Three units beside the packages do the same: the kernel's series writer, `series.dependencies.txt`
beside `series.py`, whose client is imported only where a store is named; the simulator; and onboarding, which
runs every package's code and so carries belief's. `dev.dependencies.txt` carries every extra, so a developer's
environment and CI run every test. `tests/test_projects.py` holds the core to the kernel's imports, each file to
what its unit imports beyond the core, both ways, and a file to the place beside its unit.

**Each agent has an image of its own, holding only what it runs.** `orexis-compose` reads which packages an
agent loads, closes them over the packages their code imports (`agent.tree.closed`: planning runs belief's
transition machine, so a planner holds belief), and writes the agent's service a build of its own,
`orexis-<world>-<agent>:local`, handed those packages and the extras they bring, the series writer's where the
installation serves a store. The `Containerfile` builds in two stages: the first runs `python -m agent.tree`,
the standard library alone, to lay out the kernel, the packages named and the domains, with the dependency
files of what the image holds; the second installs those extras and copies that layout. An observer's
container holds no planning code and an agent on no bus no MQTT client. The simulator has an image of its own
the same way, holding the packages its code imports.

**A code change still needs only a restart.** A service mounts what its image keeps, entry by entry
(`agent.tree.kept`) — the kernel's modules, `history/`, `metrics/`, a family's own files and the agent's
packages — and `tests/test_layout.py` holds every committed service's mounts to it.

**What is missing is refused by name.** A role whose package the image does not hold stops the boot saying so,
and a loaded package whose library the install lacks names the extra that brings it, rather than a
`ModuleNotFoundError` from inside a member's `connect`. The kernel spells the roles it names, since the
prefixes it finds are only the packages present.

# What was refused

- **A pyproject and a distribution per package.** The sovereign weighed it, a package with its own
  `pyproject.toml` installable alone, and took the file beside the package instead: the tree stays one
  distribution, one version and one install, and 0.1.0's twenty-five distributions are what that alternative
  was before it was retired ([one-tree-and-one-mechanic](/decisions/one-tree-and-one-mechanic.md)). The trigger
  for revisiting is a package wanted outside this tree, installed into someone else's agent.
- **One image carrying every library and every package.** It was the arrangement, and it is what the ruling
  refuses: each agent holding code its roles never run, and every image growing with every package anyone adds.
- **An image per set of extras, shared.** Built first in #1045 and replaced the same day: agents loading the
  same packages share the build cache all the same, so a tag of its own costs a step and names the container's
  image for what it is.
- **The standard library alone, as a rule.** It keeps a thin HTTP member to one `urllib` call, and stays the
  habit for those; as a rule it would forbid a wire, a serial line or a vision library.

# Seams left open

- **System packages.** A dependency file carries Python distributions; a transport over a serial line or I2C
  may need a device node or a system library, which no extra installs.
- **Versions.** The files pin lower bounds as the core does; no lock file holds an image to one resolution.
