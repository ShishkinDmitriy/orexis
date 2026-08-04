---
type: Decision
title: Where the belief base lives — one store, one per world, or one per agent
description: Graph-level ACLs are assembled at startup, so authorising a new agent or world costs a Fuseki restart. Three ways out, measured rather than argued; plus what an agent should do when the world changes under it, and why validating beliefs belongs in the agent rather than in an admin tool.
status: proposed
stage: v1
tags: [belief-base, fuseki, isolation, acl, memory, validation, world-version]
timestamp: 2026-08-04T00:00:00Z
---

# Context

[belief-base-isolation](/decisions/belief-base-isolation.md) put per-agent read isolation in
the store: each agent authenticates as itself and Fuseki's graph-level access control means
another agent's beliefs come back empty. [world](/domain/world.md) then gave each world its own
dataset, so worlds cannot overwrite each other.

Both rest on Fuseki's `access:SecurityRegistry`, and it is **assembled at startup**. Apache's
own documentation is explicit: *"Changing the security setup requires a server restart."* So
authorising a new principal costs a restart, and today that restart hits every world at once.

Four levels were tested against the running system, because the answer was not obvious:

| level | mechanism | dynamic? | evidence |
|---|---|---|---|
| named graph | SPARQL / Graph Store Protocol | **yes** | `PUT` → 201, readable at once |
| credential | Shiro passwd file | **yes** | user added to the mounted file authenticated with no restart |
| dataset | `POST /$/datasets?dbName=…&dbType=…` | **yes** | created, queried and deleted a dataset live |
| ACL registry | assembler | **no** | an authenticated user absent from the registry saw 0 triples of its own graph; a listed one saw 28 |

Only the registry is static — and the live-dataset API takes a *type name*, not an assembler,
so there is no way to add an access-controlled dataset through it. That single fact is the
whole of the problem.

**A grant may name a graph that does not exist yet.** Verified: `fern` holds a grant for
`:sensed` in `ds-society`, that graph is empty, and the query returns 200. This is what makes
option 2 below possible.

# What it costs today, measured

| | |
|---|---|
| Fuseki resident | **237 MB** |
| one agent container | **40 MB** |
| Pi total / available | 16 GB / 10.5 GB |
| one SELECT over a 28-triple graph | **15 ms** (almost entirely HTTP + JVM) |
| agent startup store reads | ~110 ms |

Latency is not a consideration at this scale and should not drive the decision: an agent does
one UPDATE per reading and one query per bid, against a store that is otherwise idle. Memory
is the real currency on a Pi, and it is what separates the options.

# The options

## 1. Keep one Fuseki, one dataset per world (today)

Restart on every new principal, and it hits every world. 237 MB flat.

## 2. Pre-authorise agents the world declares but has not born

A registry entry may name a graph that does not exist, and both credentials and graphs can be
added live. So if a world *declares* an agent, its ACL can be in place before the agent is ever
born — and birth then costs no restart at all: write the credential, write the beliefs graph,
start the container.

This lands exactly on the [lifecycle](/domain/agent.md): **the world declaring an agent** is a
ratified fact and may cost a restart, because ratification is rare and sovereign; **birth** and
**start** are dynamic. It does not fix adding a *world*.

## 3. One Fuseki per world

A new world is a new container; nothing existing restarts or notices. `agora-acl` becomes
per-world again. Costs **237 MB × worlds** — 711 MB for three, on 10.5 GB available. Affordable,
and the only option whose cost grows with something you add deliberately and rarely.

## 4. World as prototype: one embedded store per agent

Each agent holds one self-contained store — the world as of the version it booted with, plus
its own beliefs. Nothing is shared at runtime.

The count is highest and the machinery is lowest, because it stops being a *server*:
`pyoxigraph` is a library, like SQLite. No port, no process, no container, and **no ACL
anywhere** — an agent's store contains only what it may see, so isolation is structural rather
than enforced. Estimated single-digit MB per agent on top of the existing 40 MB, and it scales
with agents rather than worlds.

Two things make this more attractive than it first looks:

- **SHACL is not a blocker.** It never runs in the store — `agora-validate` fetches graphs over
  GSP and runs `pyshacl` in Python. A store without SHACL costs nothing.
- **Nothing queries beliefs and world together.** Every query in the codebase targets one named
  graph; the only join is in `validate.py`, in rdflib, after fetching each separately.

What it costs: the belief base stops being one place. That is a genuine reframe of
[belief-base](/domain/belief-base.md), and it puts validation somewhere new — see below.

# When the world changes under a running agent

The world **does** change: genesis is amendable, `ag:versionNumber` exists for exactly this, and
every observation is stamped `ag:underWorldVersion`. But an agent reads the version **once**, in
`Agent.__init__`, and never looks again. So today a world change is invisible until a restart,
and an agent will happily keep stamping readings with a version that is no longer current.

Three ways an agent could behave:

- **Reload in place** — notice a bump, re-read `Self`, start and stop modules as capabilities
  change. Most capable, and by far the most complex: a capability disappearing mid-round is a
  half-finished conversation.
- **Ignore it** — today's behaviour, and it is wrong rather than simple: the stamp becomes a
  lie.
- **Stop.** An agent that learns the world has moved past the version it booted with declines to
  continue and exits; supervision restarts it, and it boots into the new world.

The third fits everything else already decided. Start is cheap and repeatable, restart is not
birth so nothing is lost, and `restart: unless-stopped` already does the work. An agent acting
under a world it no longer knows is the thing to prevent; being briefly absent is not.

# Where validation belongs

`agora-validate` currently reads **every** agent's beliefs as admin. That is the one thing
option 4 breaks — and it is worth asking whether it was in the right place to begin with.

Split it by what is being checked:

- **The public world** — topology, devices, wiring — is validated centrally, once, by whoever
  ratifies it. There is one world and it is public; nothing is distributed about this.
- **An agent's own beliefs** are validated **by that agent, at startup**, against the shapes for
  the capabilities it actually derived — and it refuses to run if they do not hold.

This is better than the central check on its own merits, before any question of where stores
live. It puts the check where the data is; it happens at the moment that matters, rather than
when an operator remembers to run a command; and it is not self-report, because the consequence
is *refusing to start* rather than claiming to be fine.

The residual gap is honest and small: a modified agent could skip its own check — but a modified
agent could ignore the shapes anyway. Belief validation catches misconfiguration, not malice.
Malice is caught where it always was, at [clearing](/domain/clearing.md), which validates what an
agent may *do* rather than what it believes.

# Recommendation

**2 now, 3 if worlds become frequent, 4 only if the belief base is reframed deliberately.**

Pre-authorising (2) removes the restart from the common case — adding an agent — at almost no
cost, and it strengthens the lifecycle story rather than working around it. Per-world Fuseki (3)
is a clean answer to adding worlds, and 237 MB each is affordable, but it buys a rarer case with
real memory. The prototype model (4) is the most elegant and the lightest, and it is the right
answer *if and when* belief revision becomes real — because at that point a shared store holding
private, mutable opinion starts creaking for reasons that have nothing to do with restarts.

Moving validation into the agent is worth doing **regardless of which option wins**, and should
be decided on its own.

# What is not the reason

- **Not performance.** 15 ms per query, an idle store, one UPDATE per reading.
- **Not SHACL.** It runs client-side and always has.
- **Not query capability.** Nothing joins beliefs and world in SPARQL.
- **Not an upstream bug.** Static security is documented, deliberate Jena behaviour; there is no
  fix to wait for. [rdf-abac](https://github.com/telicent-oss/rdf-abac) would remove the restart
  by making policy per-triple and request-time, but that replaces graph-shaped ownership — *the
  graph name IS the trust tier* — with something strictly more expressive than the question
  being asked, and adds a third-party dependency to fix a provisioning inconvenience.

# Seams

- **Nothing stops two worlds with shared devices running at once.** Isolating belief bases does
  not isolate MQTT topics.
- **An agent never re-reads the world.** Until it does something about a version bump, the
  `ag:underWorldVersion` stamp is only as true as the last restart.
- **No store alternative offers graph-level per-user ACL.** [Oxigraph](https://github.com/oxigraph/oxigraph)
  is far lighter and would fit if isolation stopped depending on the store; RDF4J has no
  graph-level ACL; GraphDB's is in paid editions. Fuseki was chosen *for* this feature, and
  leaving it means replacing it with structure.
