---
type: Domain Concept
title: World
term: http://example.org/orexis#WorldGraph
description: >-
  A directory of documents under `world/<name>/`, each saying which graph it is: the world graph
  with its agents, subjects and topology, importing the domains it speaks; the state it starts
  from; the desires or wants each agent holds; and, apart, the hardware no agent is given. One
  world per agent, mounted; its tests live beside it.
---

# What it is

A **world** is an instance a [domain](/domain/kernel/domain.md) poses: this tower, this terrace, this
allotment of two growers and a supplier. It is documents and nothing else, and each document says
what it is with `<> a <a graph kind>` on its own IRI, or, in TriG, of each graph it names:

| document | kind | holds |
|---|---|---|
| `world.ttl` | `orexis:WorldGraph` | the agents and what each acts for, the individuals, the wiring — and `owl:imports` of the domains it speaks |
| `state.ttl` | `orexis:StateGraph` | where things stand at the start, for a world nothing senses |
| `wants.ttl`, `desires.ttl` | `planning:WantGraph`, `planning:DesireGraph` | what an agent is to bring about, once or for good |
| `beliefs/<id>.ttl` | any agent-owned kind | one agent's own documents, in a world of several |
| `hardware.ttl` | `orexis:PublicGraph` | pins, parts and boards — read by the operator's tools, never mounted into an agent |

The file's NAME is for eyes; the kind in the document is what the loader reads. Seven ship:
`hanoi`, `courier` and `tower` plan and exit; `greenhouse` doses and heats; `allotment` trades
water on a market; `sensing` and `terrace` observe.

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
