---
type: Decision
title: Where the belief base lives — the world is files, beliefs are the agent's own
description: A shared triplestore couples worlds that are supposed to be independent — adding the 21st forces a restart of the other 20. Decision: the world becomes TTL files an agent loads at start, beliefs live in a persistent store inside each agent, no shared store survives, and validation moves into the agent.
status: accepted
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

**It must be persistent.** Oxigraph offers an in-memory store and a RocksDB-backed one; only
the second is admissible. Beliefs that vanished on restart would make every start a partial
re-birth, resetting the agent to whatever the sovereign last authored — the exact collapse
[agent](/domain/agent.md) §Lifecycle exists to prevent. Start and stop are pause and resume, so
revision has to survive them or a belief is configuration again. In practice: a RocksDB store on
a per-agent named volume, which `agora-compose` can emit as one line per service.

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

# Persistence is the default, and an exception must be declared

**Beliefs survive restarts. That is a requirement, not a property of whichever store wins.**
Any option that cannot offer it is disqualified rather than cheaper.

There is a plausible exception — a short-lived agent spawned for one task, whose opinions are
not worth keeping — but it is an **optimisation**, and the rule this architecture already
follows applies: state it in the world and let the runtime derive the consequence. An ephemeral
belief store would be a declared property of an agent in `world/<world>/world.ttl`, the way
`ag:senseMode` declares a device's nature, and the default in its absence is durable. Nothing
should be ephemeral because of how it happened to be deployed.

This is not yet modelled and should not be until there is a real short-lived agent to model it
for.

# Built

Implemented. Fuseki, `agora-seed`, `agora-acl`, the store credentials and the access registry
are gone; `infra/fuseki/` no longer exists. Three things only became clear by building it:

- **The derivation rules survived unchanged**, which the earlier rejection of "a dataset per
  agent" predicted they would not (see
  [belief-base-isolation](/decisions/belief-base-isolation.md)). That prediction assumed
  beliefs split *out* of a shared dataset; each agent instead holds a **complete** one, so
  `rules.ru` runs in SPARQL inside every agent exactly as written. Load + derive measures 4 ms.
- **An agent validating itself has to scope the focus.** A capability shape targets every agent
  the world declares, but an agent holds only its own beliefs — so without `focus_nodes`, fern
  reported tomato as missing a band it was never entitled to see. Scoped, it asks the question
  it can actually answer: *am I* what my capabilities require me to be.
- **The store is exclusively locked by its owner.** Nothing outside an agent can open its
  belief base, including an operator on the host. That is the isolation working, and also the
  price: you cannot inspect a running agent's beliefs, only ask it.

# A defect this exposed

Writing a triple into a beliefs graph and then restarting the compose project removed it. The
likely cause — **unverified at the time of writing** — is that restarting the project also
re-runs the `seed` service, which PUTs each beliefs graph wholesale.

If so it is worse than the seam already recorded under [genesis](/decisions/genesis.md): not
"re-seeding is an unintended re-birth" but **"restarting the society is an unintended
re-birth"**, and it would hold for any store, Fuseki or embedded alike.

The principled fix is not to change how anyone restarts, but to make birth do what its name
says: **write an agent's beliefs only if it has none**, and require an explicit act to reset an
agent that already exists. **Done** — an agent is born on its first boot and logs `born`;
verified that a restart logs only validation and startup, and that its RocksDB volume
persists. Discarding a belief base now takes `down -v`, which is meant to look deliberate.

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

# Decision — option 4

**The world becomes TTL files. Beliefs live inside each agent. No shared store survives.**

The argument that decided it is not memory and not latency — it is **coupling**. A shared
Fuseki means adding the 21st world restarts the other 20. [world](/domain/world.md) isolated
worlds at the data level and then left them joined at the config level, which makes that
isolation partly cosmetic: two worlds that cannot see each other's data can still take each
other down.

And worlds are *already* frequent. Not three plants and a barrel, but versions of a world,
simulations, variants under test. Multi-world was built to be used that way, and an option whose
cost is paid by every existing world each time you add one cannot support it.

Options 2 and 3 were both rejected for the same reason. Pre-authorising (2) removes the restart
for agents but leaves worlds coupled. Per-world Fuseki (3) decouples them but pays 237 MB each —
4.7 GB at twenty worlds, to run twenty JVMs whose only job is to keep a few hundred triples
apart.

## What it looks like

| | before | after |
|---|---|---|
| world, T-Box | Fuseki, ACL'd | **TTL files**, loaded at start |
| beliefs | Fuseki, ACL'd | persistent store inside the agent |
| `:sensed` | Fuseki, readable by all | inside the agent |
| Fuseki | 237 MB | **gone** |
| store credentials, ACL registry | generated, restart to change | **gone** |
| restart to add a world or agent | yes | **never** |

The world and the T-Box are already authored as TTL. Genesis stops needing a store at all: it
ratifies files, and an agent loads them. Isolation stops being enforced and becomes structural —
an agent's store contains only what it may see, so there is nothing to enforce.

The store must be **persistent and volume-backed** (see above); an in-memory store would make
every start a partial re-birth.

## Validation moves into the agent

Decided with it, and it would have been right regardless. The **public world** is validated
centrally against the ratified files. An **agent's own beliefs** are validated by that agent at
startup, against the shapes for the capabilities it derived, and it refuses to run if they do
not hold.

This is what makes a distributed belief base viable — the check sits where the data is — but its
better justification is independent: it happens before the agent acts rather than when an
operator remembers to run a command, and refusing to start is not self-report.

## Influx is a separate hole, and not a blocker

Checked while deciding: **every agent holds the admin Influx token and can read every subject's
entire history.** One bucket, one token, handed to all containers. So `fern` cannot read
`tomato`'s beliefs but can read its complete moisture series — exactly the raw state the
band-only MQTT disclosure exists to withhold.

Influx 2.x permissions are per **bucket**, not per tag, so isolation means one bucket per agent
and a token scoped to it. Verified working: a scoped token read its own bucket and was denied
`sensors`. Generatable from the world, the way store credentials are today.

Deliberately **not** part of this change — it is independent, it applies to the current design
too, and it deserves its own decision.

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
