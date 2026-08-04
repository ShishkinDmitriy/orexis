---
type: Decision
title: Belief-base isolation — making privacy enforced rather than agreed
description: Privacy is now enforced by the store, not by code discipline — per-graph ACLs behind per-agent credentials, with two doors because Jena's access control is read-only.
status: superseded
stage: v1
tags: [privacy, fuseki, isolation, security, seam]
timestamp: 2026-08-03T00:00:00Z
---

> **Superseded** by [where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md).
> The *intent* stands and is now stronger: an agent cannot read another's beliefs. The
> *mechanism* is gone — there is no shared store to be let into, so there are no credentials,
> no access registry, and nothing to enforce. Isolation became structural rather than
> configured. What follows is kept because the reasoning about **why** the graph is the
> boundary is still load-bearing, and because Option B below made a prediction worth
> correcting.

# Context

The architecture says an agent's desire, limits and valuation are **private**, and the code
honours it: `Beliefs` is constructed with one agent id and can reach only that graph, no
module queries another agent's beliefs, and each agent subscribes exactly its own sensor
channels. One process per agent means a peer's valuation is not even in the same address
space — which is what forced the auction to become a protocol.

None of that *was* enforced. `store.py` used a single admin credential for every agent, so
`:beliefs/tomato` was one SPARQL call away from any process that cared to make it — privacy by
construction and convention, not by enforcement. Good enough for a trusted-agent deployment
([trusted-agent-mode](/decisions/trusted-agent-mode.md)); not good enough for the adversarial
society the rest of the design keeps a seam open for.

# The prerequisite, which both options share

**Per-agent credentials.** There was no identity for the store to enforce against — every
agent authenticated as `admin`. Until an agent has its own credential, neither option below
does anything: separate datasets without separate logins are equally readable by anyone who
knows the URL. This was the actual first task, and it pairs naturally with the certificate
already described in [authn-authz-capabilities](/decisions/authn-authz-capabilities.md) —
the cert says who you are, and the store should be one of the things that checks.

# Decision: Option A, built

Taken and implemented. What follows records the shape, and the two things that only became
apparent by building it.

# Option A — per-graph access control, one dataset (chosen)

Jena supports mapping users to graphs in the dataset assembler, so the store itself refuses a
read of a graph you do not own.

- **Keeps one dataset**, which matters more than it looks: the derivation rules
  (each capability's `rules.ru`) read `GRAPH <world>` and `GRAPH <ontology>` in a single update, and SHACL
  targets ask questions spanning world, T-Box and beliefs at once. Both require one dataset.
- Enforcement lands exactly where the convention currently is, with no change to how agents
  query.
- Cost: an assembler rewrite, per-agent credentials, and a Fuseki image that exposes the
  configuration (see below).

# Option B — a dataset per agent

*(Rejected here; a stronger form of it was later built. See the correction at the end.)*

Blunter, and it buys isolation at the price of the thing that makes the belief base coherent.

- **Cross-dataset queries do not exist.** `validate.py` already fetches graph-by-graph over
  HTTP so it would survive, but the derivation rules would not — they would have to move to
  client-side read-modify-write, losing the property that derivation is stated in the same
  language as everything else.
- Cost is real but not prohibitive at this scale: each TDB dataset carries its own indexes,
  node table and journal. Measured on the Pi, Fuseki sits at ~444 MB serving one dataset on a
  16.7 GB box — a handful of agents is comfortable, fifty would not be. An in-memory dataset
  per agent is nearly free and, since beliefs are re-seedable from `genesis/`, may be
  durable enough.
- **Rule if this is ever taken: world and ontology stay together in one dataset.** Only
  per-agent beliefs may move out.

# The two surprises

**Jena's data access control is read-only.** An `access:AccessControlledDataset` rejects
every write with `405` — there is an `AccessCtl_DenyUpdate` in the jar. Since every agent
writes its own readings into `:sensed`, a single secured dataset would have stopped the
society dead. The resolution is **two doors over one store**:

- `/ds` — secured. An agent authenticates as itself and reads the ontology, the world,
  `:sensed`, and its own beliefs. Another agent's beliefs come back **empty** — Jena filters
  rather than refusing, so the failure looks like absence, which is why the missing-belief
  error message matters.
- `/ds-rw` — the plain store. `update` is open to every agent, `data` and `sparql` are
  admin-only, which is what seeding and validation need.

So **reads are enforced and writes are not**: an agent could still write into another's
graph, because Jena cannot scope writes per graph. That is the integrity-of-self-report
assumption [trusted-agent-mode](/decisions/trusted-agent-mode.md) already accepts explicitly.
The gap that was actually open — *reading* someone else's mind — is closed.

**Admin is not in the registry.** The `urn:jena:accessAllGraphs` token did not grant
everything in this build, and rather than fight it, admin simply has no entry on the secured
door and reads through the plain one. This is arguably the better shape anyway: the secured
door exists to constrain agents, and admin is not one.

# What the current deployment needed

No image change was needed after all — the `secoresearch/fuseki` image already ships
`org.apache.jena.fuseki.access`, and runs **Fuseki Main**, which takes a `--config`. It is
now pointed at our own assembler with `FUSEKI_BASE` moved aside so the image's built-in
single-dataset config does not also load. (No official Jena image publishes an arm64 build,
so this mattered.) The store is now **TDB2** rather than the image's TDB1.

One deployment wrinkle: the credential file is `0600` and owned by the host user, which the
container's own user cannot read. The service runs as `user: "0:0"` — under rootless podman
container-root maps to the invoking user, so the secrets stay unreadable to everyone else on
the host and no host privilege is gained.

# The ACL is derived, like everything else

Who exists — and therefore who needs a credential and which graphs they may read — is stated
in `genesis/world.ttl`. Hand-maintaining a second list inside a Fuseki config would be exactly
the drift this architecture exists to remove, so `agora-acl` **generates** the assembler from
the world, and each agent's credential is created once and kept in `keys/fuseki/` beside the
signing keys. Add a plant to the world, re-run `agora-acl`, restart Fuseki: it is authorised.

An agent process reads its own credential and connects as itself. If the credential is
missing it falls back to admin **and says so loudly**, because that is precisely the
difference between enforced and assumed privacy.

# Fixed alongside

**Fuseki now has a volume.** Its database previously lived in the container's writable layer,
so recreating the container destroyed the belief base. It is all re-seedable from `genesis/`
except `:sensed`, but for a system whose configuration *is* the triplestore that was a
surprising thing for the compose file not to say.

**`get_graph` never sent credentials** — a latent bug that could not surface while everything
was anonymous, and broke validation the moment reads required identity.

# The correction, in hindsight

Option B was rejected mainly on this: *"the derivation rules would not survive — they would
have to move to client-side read-modify-write, losing the property that derivation is stated in
the same language as everything else."*

**That was wrong**, and only became clear by building the thing it warned against. The
prediction assumed beliefs would be split *out* of a shared dataset, leaving rules to span
stores. What was actually built gives each agent a **complete** dataset — the T-Box, the whole
world, and its own beliefs — so `rules.ru` runs unchanged, in SPARQL, inside every agent. The
rules never needed to span agents; they only ever needed the world and the vocabulary together,
and Option B's own rule ("world and ontology stay together") is satisfied in every store rather
than in one.

Two other estimates here were pessimistic. Fuseki was measured at 237 MB rather than ~444 MB,
and a per-agent embedded store turned out to be single-digit MB because it is a library rather
than a server — the option was costed as "a dataset per agent *in Fuseki*", which is a much
more expensive thing than a dataset per agent.

What the rejection got right: cross-dataset queries do not exist. That is still true, and it is
why validation had to move into the agent rather than stay central.

# What this still does not buy

- **Writes are not scoped.** See above; consistent with trusted-agent mode, but it means an
  adversarial society needs more than this.
- **MQTT is still open.** The store is now enforced; the bus is not. Any process that can
  reach the broker can subscribe `sensors/#` and watch every reading, and there is no
  per-agent MQTT credential. Closing that is the obvious next piece, and the reason the
  privacy story is *better* rather than *finished*.
- **`:sensed` is still one shared graph**, readable by every agent. Splitting it per subject
  is now cheap — the registry generator would just emit `:sensed/<subject>` — but it is a
  change to what the graph layout means, so it is left as its own step.
