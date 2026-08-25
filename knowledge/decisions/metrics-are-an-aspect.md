---
type: Decision
title: Metrics are an aspect — every package counts its own, the choir is the registry, and reporting is the sink
description: >-
  The kernel's `Metrics` counted readings per sensor, reading age, cadence acks and store
  failures — sensing's numbers in the mind's account — and the series writer sat in the kernel
  beside them. Decided: a package counts what is its own and answers `reports()` and
  `series()` with it; there is no metrics registry because the agent's module list asked
  through the choir already is one; reporting owns the sink and the readings sensing records
  reach it by being told (`record`); the kernel's `Metrics` contributes the mind's own figures
  the same way. The driver contract and the sovereign's channel left the kernel in the same
  change, for the same reason.
status: accepted
timestamp: 2026-08-26T10:00:00Z
---

# What was true before

`agent/metrics.py` was a hub: sensing counted into it (`reading_recorded`, `cadence_acked`,
`sensed_failed`, `influx_failed`), reporting read the per-sensor figures back out of it by name
(`readings`, `reading_age_s`, `sensors_seen`), and it merged every module's `reports()` on the
way. `agent/influx_writer.py` was the sink, constructed twice — once by sensing's
`Observations` to write raw readings, once by reporting to write health — each with the same
credential. Two more of sensing's and reporting's words sat in the kernel for the same
historical reason: `agent/driver.py`, the contract a transport implements *for sensing*, and
`agent/sovereign.py`, the two topic names reporting answers on.

The sovereign asked whether metrics need a shared registry that packages register with, and
whether that is a "shared service" the architecture lacks.

# What is decided

**Metrics are an aspect, and the choir is the registry.** Every module already answers two
hooks: `reports()` — fields on the agent's health point — and `series()` — tagged rows into the
agent's bucket. A module that wants to be seen defines them; nothing registers, nothing lists.
`agent.ask("reports")` and `agent.ask("series")` are the whole of discovery, exactly as they are
for wants (`desires`), for readings (`annotate`, `urgency`) and for the mailbox
(`subscriptions`, `handle`, `send`). A second mechanism for the same shape would be a thing
packages have to know about, which is the coupling a registry was feared to bring.

**A package counts its own.** Sensing's `Observations` keeps readings per sensor, reading age,
the cadence a board acknowledged and the writes the belief base refused, and reports them —
`sensed_write_failures` on the health point, one `agent_sensor_health` row per sensor in the
series. The transport reports its session; the keeper its ledger; review its revisions. The
kernel's `Metrics` shrinks to the mind's own account — uptime, belief-base size, compactions,
world version — and the intention event buffer, which is BDI's story rather than anybody's
counter.

**Reporting is the sink, and it merges.** One writer (`reporting/series.py`), one credential,
one clock. On its tick it takes the kernel's fields, merges every `reports()` answer (last
wins on a collision, and says so), concatenates every `series()` answer, and writes. The raw
readings sensing records reach the same writer by being TOLD — `agent.tell("record", value,
at, **tags)` — so one place knows the series store exists, and an agent with no credential
records nothing and says why once, exactly as before.

**Two neighbours moved on the same argument.** `Driver` is what a transport's driver
implements for sensing, like `Codec` and `Scaling`; it is `packages/capability/sensing/driver.py`.
The sovereign's channel names are what reporting answers on and what onboarding grants; they
are `packages/capability/reporting/sovereign.py`, and onboarding imports them from there.

# What did not change

- **The measurements and the fields.** `agent_health`, `agent_sensor_health`, `agent_desire`,
  the event measurement, and every field name the dashboards and `infra/tests` read. What moved
  is who computes them.
- **Mandatory reporting.** `Storing` is granted to every agent by the fact of being one; an
  agent that cannot report is still an agent, one that cannot record is not.

# Seams left open

- **A collision on a `reports()` key is logged, not refused.** Two modules claiming
  `desires_measured` would be a defect a gate could catch; today reporting keeps the later.
- **`record` reaches whoever answers it.** One module does; a second sink would write every
  reading twice. Choosing is a world fact nothing states.
