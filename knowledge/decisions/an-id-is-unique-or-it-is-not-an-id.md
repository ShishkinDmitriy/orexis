---
type: Decision
title: An id is unique or it is not an id, and the boot identifier stays the short name
description: >-
  Two agents could share an `ag:localId` and every world still validated — SHACL's `sh:maxCount
  1` is cardinality per agent, not uniqueness across them — so `load_self` would hand whichever
  matched first a self assembled from both nodes' capabilities. Refused now at genesis and again
  at boot. The alternative was to hand each process its node IRI instead, making ambiguity
  unrepresentable; it is turned down because the short id is the wire name in forty-seven places
  and would have to stay, leaving two identifiers in circulation where there is one.
status: accepted
timestamp: 2026-08-29T00:00:00Z
---

# What was possible

`ag:AgentShape` states `sh:minCount 1 ; sh:maxCount 1` on `ag:localId`. That is cardinality **per
agent** — each has exactly one id — and SHACL has no cross-node uniqueness constraint, so nothing
anywhere compared two agents' ids. A world with two `:fern` nodes validated.

`load_self` then interpolated the id into a literal match and took `rows[0]`. Rows arrive one per
(agent × capability), so the result was the first node's URI and subject **holding both agents'
capabilities** — a false self that reports nothing wrong.

# What is decided

**Refused twice, at both ends of the same fact.**

`orexis-validate` asks it where the world is entire (`ids_are_unique`), which is the only vantage
from which the question exists — an agent's own boot check is focused on its own node and could
never see the collision. And `load_self` raises rather than choosing, for a volume built before
the gate existed or a world amended past it.

**Which is where this project puts such errors**: loudly at startup rather than quietly at 3am.

# Why not the URI

The stronger-sounding option is to hand each process its own node IRI, so ambiguity becomes
unrepresentable rather than checked. It is refused for a reason that only appears when you count:

**The id is the wire name in forty-seven places** — the broker principal and its ACL lines, the
Influx bucket and its token, the container, the secrets directory, the volume, and the IRIs of an
agent's own private graphs. None of those can take a URI. So the short name would stay, the URI
would join it, and a process would be handed one identifier while everything it touches used the
other — two names for one thing, which is the confusion
[a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md) was written to end,
reappearing at the identity layer.

It also costs 158 test call sites that build an agent by short name, and any helper that resolved
short-to-URI for them would reintroduce exactly the ambiguity the change was for.

**What the URI would genuinely have bought is smaller than it looks.** A URI names its world, so
mounting the wrong world would fail rather than silently find another world's `fern`. That case
is real — and it is closed from the other side, because a world is mounted alone and an id that
matches nothing already raises.

# What is not closed

**Uniqueness is checked, not structural.** Two worlds may each hold a `fern`, which is correct —
they are different societies and never meet — but nothing prevents a `world.ttl` from being
amended between validation and a boot. The boot-side refusal is what covers that gap, and it
covers it by failing rather than by making the state impossible.
