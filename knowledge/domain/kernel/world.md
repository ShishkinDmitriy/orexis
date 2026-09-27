---
type: Domain Concept
title: World
term: http://example.org/orexis#WorldGraph
description: >-
  A directory of documents under `world/<name>/`, each saying which graph it is and so who reads
  it: the world graph with its subjects, sensors and systems, importing the domains it speaks; the
  society of its principals and their wiring; the state it starts from; the desires or wants each
  agent holds; and, apart, the hardware and — where the world pins it — where its broker listens,
  which onboarding reads and no agent needs. One world per agent, mounted; its tests live beside it.
---

# What it is

A **world** is an instance a [domain](/domain/kernel/domain.md) poses: this tower, this terrace, this
allotment of two growers and a supplier. It is documents and nothing else, and each document says
what it is with `<> a <a graph kind>` on its own IRI, or, in TriG, of each graph it names:

| document | kind | holds | read by |
|---|---|---|---|
| `world.ttl` | `orexis:WorldGraph` | the subjects and their ranges, the sensors, devices and systems, the venues — and `owl:imports` of the domains it speaks; in a world with no bus, its agent too | every agent, the simulator, and onboarding |
| `society.ttl` | `orexis:SocietyGraph` | the agents and what each acts for, the client each is, the broker as what clients connect to, the topics, their filters, and which device speaks on which | every agent, the simulator, and onboarding |
| `deployment.ttl` | `onboarding:DeploymentGraph` | where the broker listens, its `schema:url`s — only where the world pins them | onboarding alone |
| `state.ttl` | `orexis:StateGraph` | where things stand at the start, for a world nothing senses | the agent |
| `wants.ttl`, `desires.ttl` | `planning:WantGraph`, `planning:DesireGraph` | what an agent is to bring about, once or for good | the agent |
| `beliefs/<id>.ttl` | any agent-owned kind | one agent's own documents, in a world of several | that agent alone |
| `hardware.ttl` | `onboarding:HardwareGraph` | pins, parts and boards | `orexis-firmware` alone |

The file's NAME is for eyes; the kind in the document is what the loader reads. Seven ship:
`hanoi`, `courier` and `tower` plan and exit; `greenhouse` doses and heats; `allotment` trades
water on a market; `sensing` and `terrace` observe.

# Who reads which kind

**A kind says who reads the document, and every reader loads only the kinds it reads**
([a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md)). An
agent's boot passes over a kind its T-Box does not put beneath `orexis:Graph`, so what an agent
is not given is kept from it by default, not by a list of files left out; the same kind decides
which documents `orexis-compose` mounts into a container. A misspelled kind would be passed over
just as quietly, so `orexis-onboard` refuses a world holding a graph no reader declares.

A **society graph** holds the principals and how they reach one another, in MQTT4SSN's words —
every one of them a world with a bus states, since its world graph speaks none. The agents read it
and so does the simulator, which plays the devices on their topics; `orexis-mqtt` derives the ACL
from it. It is the kernel's kind: the boot finds who the agent is there, and reads off it — and
off the world graph — the premises that decide which [packages](/domain/kernel/package.md) the
agent loads, before any of them is. A broker is named here only as what
clients are connected to. Where it listens is a [deployment](/domain/onboarding/deployment.md)
graph, onboarding's kind, which the agent's T-Box cannot name, so no agent's boot holds its address
and no container mounts the document. A world may assert it there, and a world that does not is
allocated a port by the installation, which alone sees which ports every world holds.

A world with no bus — hanoi, courier, tower — has no society graph, and its one agent stays in the
world graph beside what it acts on.

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
