---
type: Domain Concept
title: Event
description: >-
  A signal one package gives the others through the runtime that something just happened - a graph
  written, a plan published, a want reached, a step blocked, an intention ended, a command, a
  document said or told. Named in the kernel, routed at once on the one thread, and never stored.
---

# What it is

An event says that something happened, so that whoever listens can act now: planning publishes a
plan and execution adopts it; execution ends an intention and planning plans again; a job writes an
observation and belief revises it. A package `emit`s it and another `listen`s for it through the
[runtime](/domain/kernel/runtime.md), which calls every listener at once, on its one thread, and
knows nothing of what the event means. What a listener writes is itself an event, *a graph written*,
so a write sets off whatever hears its kind (`runtime.on`).

The names are the kernel's (`agent/events.py`), because a [package](/domain/kernel/package.md) may not
name a word of one above it: execution hears a plan planning publishes, and planning an intention
execution ends.

# What it is not

**A fact.** An event is not stored. What happened is in the store — the plan, the intention's
outcome, the graph — and a listener reads it there, so a restart that replays no event loses
nothing. **A call.** The emitter does not know who listens, or whether anyone does
([a-package-starts-itself](/decisions/a-package-starts-itself.md)).
