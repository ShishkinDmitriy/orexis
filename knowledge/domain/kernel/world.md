---
type: Domain Concept
title: World
term: http://example.org/orexis#WorldGraph
description: >-
  A directory of documents under `world/<name>/`, each saying which graph it is and so who reads
  it: the world graph with its agents, subjects and topology, importing the domains it speaks; the
  state it starts from; the desires or wants each agent holds; and, apart, the hardware and the
  deployment, which onboarding reads and no agent needs. One world per agent, mounted; its tests
  live beside it.
---

# What it is

A **world** is an instance a [domain](/domain/kernel/domain.md) poses: this tower, this terrace, this
allotment of two growers and a supplier. It is documents and nothing else, and each document says
what it is with `<> a <a graph kind>` on its own IRI, or, in TriG, of each graph it names:

| document | kind | holds | read by |
|---|---|---|---|
| `world.ttl` | `orexis:WorldGraph` | the agents and what each acts for, the individuals, the wiring — and `owl:imports` of the domains it speaks | every agent, and onboarding |
| `state.ttl` | `orexis:StateGraph` | where things stand at the start, for a world nothing senses | the agent |
| `wants.ttl`, `desires.ttl` | `planning:WantGraph`, `planning:DesireGraph` | what an agent is to bring about, once or for good | the agent |
| `beliefs/<id>.ttl` | any agent-owned kind | one agent's own documents, in a world of several | that agent alone |
| `hardware.ttl` | `orexis:PublicGraph`, until it is a hardware graph | pins, parts and boards | `orexis-firmware` — and, today, every agent booted from the directory (#820) |

The file's NAME is for eyes; the kind in the document is what the loader reads. Seven ship:
`hanoi`, `courier` and `tower` plan and exit; `greenhouse` doses and heats; `allotment` trades
water on a market; `sensing` and `terrace` observe.

# Who reads which kind

**A kind says who reads the document, and every reader loads only the kinds it reads**
([a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md)). An
agent's boot passes over a kind its T-Box does not know, so what an agent is not given is kept
from it by default, not by a list of files left out.

Two kinds are decided and not yet declared. A **society graph** holds the principals and how
they reach one another — the agents, the client each is, the brokers as what clients are
connected to, the topics and the filters that name them — and is read by the agents and by
`orexis-mqtt`, which derives the ACL from it. It is the kernel's kind, because the boot reads off
it which packages an agent loads, before any of them is loaded. A
[deployment](/domain/onboarding/deployment.md) graph holds what runs and where it answers, and is
onboarding's. Today the world graph holds all three, a broker's address included (#823).

# How it is used

An agent is told its id and given one world, mounted at `/app/world/<name>`; it never learns other
worlds exist. The [runtime](/domain/kernel/runtime.md) boots from the directory, following
`owl:imports` into `domains/`, and a volume it has lived in reads the public documents again at
every boot while keeping the agent's own. [Onboarding](/domain/onboarding/onboarding.md) reads the same
documents to grant each agent its bucket, its broker credential and its container, and writes
`compose.yaml` and `secrets/` beside them.

**There is no default world**: every command takes one and refuses to guess, since a fallback puts
a misconfigured agent on the real one's topics. And **a world is held to what it does by the tests
beside it** — `world/<name>/tests/` boots it from its files and runs it.
