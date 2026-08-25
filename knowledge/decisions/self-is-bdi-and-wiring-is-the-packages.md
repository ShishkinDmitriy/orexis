---
type: Decision
title: Self is what an agent is, and what it is wired to is each package's to load
description: >-
  `agent/world.py` loaded every package's wiring into one `Self` — sensors, actuators, venues,
  each by that package's words, in SPARQL the #334 ratchet could not see. A kernel that loads
  packages should know no probe, no valve and no venue. `Self` keeps what an agent IS — its
  id, its capabilities, whom it acts for — and each package loads what it is wired to from its
  own `wiring.py`, with the dataclass and the query that were the kernel's, one directory
  over. The transport's bus stays in the kernel for now, because the kernel still holds the
  MQTT connection.
status: accepted
timestamp: 2026-08-27T12:00:00Z
---

# What was true before

`load_self` built a `Self` with `sensors`, `actuators`, `markets` and `hosted_markets`, and to
do it the kernel walked `sensing:polls`, `sensing:monitors`, `sensing:senseMode`,
`codec:decodedBy`, `scaling:scaledBy`, `actuation:hasActuator`, `market:bidsIn`,
`market:hosts` and a dozen `mqtt:` topics — some forty package words, every one of them in a
prefixed query string where [the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md)'s
scan could not see it. The kernel knew what a sensor, a valve and a venue were, and each
package read its own wiring off the kernel's record of it.

# What is decided

**`Self` is what an agent IS**: `uri`, `agent_id`, `capabilities`, `acts_for`. BDI structure —
the one identifier a process is handed, and what the graph says of it.

**What it is wired to is each package's.** `Sensor` and `sensors_of` in
`packages/capability/sensing/wiring.py`; `Actuator`, `actuators_of` and `actuator_for` in
actuation's; `Market`, `bidding_markets_of`, `hosted_markets_of`, `participants` and
`allocation_ceilings` in the market's. The dataclasses and the queries are the ones the kernel
had; each module loads its own at construction (`self.sensors`, `self.actuators`,
`self.markets`), and the event topic sensing announces on is sensing's to look up too.

**The kernel's one remaining reader is metrics**, which lists the sensors expected to report
and reads them off whichever modules keep a `sensors` attribute — by attribute, because the
kernel names no sensor, and noted as the seam it is.

**Tests get a composite the kernel deliberately lacks.** `conftest.load_wired` is `load_self`
plus every package's wiring, and `wired_sensors(agent)` and its siblings reach the module's
loaders, so a test says `wired_sensors(fern)[0].reading_topic` where it said
`fern.me.sensors[0].reading_topic`.

# What stays, and why

- ~~**The bus.**~~ Closed by [the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md). `MessageBus` and `load_bus` were still the kernel's, and `mqtt:` was the one
  package namespace `world.py` still names, because the kernel still opens the MQTT
  connection itself (`runtime.py`). The day the transport package owns the connection, the
  bus goes with it.
- **`Self.can`.** Which capabilities an agent holds is what genesis derived onto it — its own
  row.

# Seams left open

- **The ratchet still cannot see prefixed names.** This change removed the largest body of
  them; #344 is the check that would keep them from returning.
- **`metrics.sensors_seen` reads a module attribute.** A `reports()`-shaped contribution from
  sensing would be the honest form; the figure is sensing's ("the board has never been heard
  from"), and the reporter is the kernel's only because it writes the series.
