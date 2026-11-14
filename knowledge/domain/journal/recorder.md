---
type: Role
title: Recorder
term: http://example.org/orexis/journal#Recorder
description: >-
  An agent that keeps a journal of what happened to it - the role whose package is `orexis-journal/`. Where the self
  graph declares it, every event the agent's packages say and every activity they end is written down as it happens;
  where it declares none, the packages say the same things and nobody keeps them. It changes nothing the agent plans
  or does.
---

# Who plays it

An agent is a **recorder** where its self graph says it [plays](/domain/kernel/role.md) a `journal:Recorder`, and the
boot loads `orexis-journal/` for that and for nothing else. Every world shipped here declares it of every agent, since
the [history view](/domain/onboarding/history-view.md), an agent's account of its season and a chat asking what
happened all read what a recorder kept.

# What it does

The package is started before every other the agent loads, so what they say as they start is heard. It hears the
agent's [events](/domain/kernel/event.md) and writes the [journal](/domain/kernel/journal.md): each event that states
triples as an entry in its package's words, and each [activity](/domain/kernel/activity.md) as it ends. What the role is
linked to decides which of the two crates that keep house for the journal are started with it:
`orexis-journal-oxigraph/`, which takes what lasts to the [archive](/domain/journal/archive.md) the role names, and
`orexis-journal-otlp/`, which ships the activities to the [tracer](/domain/journal/tracer.md) the role names. A role
naming neither keeps the journal in memory for its window, and runs nothing else. The agent's log
is kept there too, with what the boot said before the role was read.

# What it is not

**A part of the kernel, or known to any package.** A package says an event and may state triples for it; whether
anybody writes them down is not its business, and no crate but the binary names `orexis-journal/`.

**Something a plan reads.** The first ruling refused this role for that reason, a role being a belief and a journal
changing no plan, and every agent kept a journal. It was overruled on 2026-11-13: a package is loaded for a role and
for nothing else, and one kept by every agent whatever it plays was the one exception
([the-journal-is-the-agents-flight-recorder](/decisions/the-journal-is-the-agents-flight-recorder.md)). The cost that
record named stands: an agent whose self graph forgets the role has no journal on the day one is wanted, and a boot
that fails before the self graph is read is journaled by nobody.
