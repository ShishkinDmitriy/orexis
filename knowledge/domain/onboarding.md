---
type: Process
title: Onboarding — a ratified world, granted the means to run
description: The phase between genesis and a running society. What it grants, why every grant is derived from the wiring rather than decided here, why it is not birth, and why its code lives outside the agent's package.
---

# What it is

**Genesis ends with a world. It does not end with a society.** A world says what exists and how
it is wired, and that is a complete description of nothing running. Between it and a first
`podman compose up` sits a phase that had no name here until it was given one:

```
nothing ─genesis→ world ─onboarding→ credentials + config ─up→ (birth, if never born) running
```

**Onboarding** is the moment an agent stops being a description and acquires the means to act:
an account of its own on the series store, a credential of its own on the bus, and a container
to run in. That is what the word means for a person joining anything — not deciding what they
may do, which was settled earlier, but handing them the keys that let them do it.

```bash
orexis-onboard <world>
```

# What it grants

| tool | grants | derived from |
|---|---|---|
| `orexis-influx` | a bucket per agent, and a token that opens only it | who the agents are |
| `orexis-mqtt` | a credential per principal, the broker ACL, **and a certificate per agent** | what each agent is wired to |
| `orexis-compose` | the roster, as services | the roster, and who actuates |
| `orexis-dashboards` | a Grafana folder per world: what was measured, and how the agents are | what each agent observes, and the roster |
| `orexis-firmware` | a board's `config.h` | the broker, the ids and topics, the pins, the calibration, the credential |

`orexis-onboard` runs the first four, after `orexis-validate` — which itself begins with the
LINK step (#210): every project-namespace IRI the loaded packages reference must be declared
by some loaded ontology, or the world is refused naming the dangling term. A reference to a
term nobody declares matches nothing, and an empty result is not an error — the linker is
what makes that silence a gate instead of a hazard. They remain separately callable,
because rotating one service's credentials should not touch the other's.

`orexis-firmware` is deliberately **not** in the umbrella. It writes into a firmware project rather
than granting anything, and it is only useful when a board is in front of you — onboarding a world
should not touch a source tree you are about to build from.

# Nothing here decides anything

Every grant is **derived** from wiring the sovereign already ratified. That is not an
implementation detail — it is what makes onboarding a single command rather than a checklist,
and what makes re-running it safe. Adding an agent to a world and running it again is the whole
of onboarding that agent; there is no list to keep in step, because there is no list.

It is the same move [world-graph](/decisions/world-graph.md) makes everywhere else: the model is
the single source, and anything that could drift from it is computed instead of written down.

Validation comes first for a reason worth stating. Onboarding a world that does not hold
together mints real credentials for agents that will then refuse to start, and leaves them lying
around — so `orexis-onboard` refuses rather than grants.

# Two ways to prove who you are, one way to be authorised

Agents connect on `mqtt:brokerTlsPort` with a **client certificate**; boards connect on
`mqtt:brokerPort` with a **password**. Same bus, same topics, and — this is the point — the same
generated ACL. Mosquitto's `use_identity_as_username true` takes the certificate's CN as the
username, and `orexis-mqtt` issues each agent a certificate whose CN *is* the world-qualified
username it already derived. So a certificate is a different way of proving who you are, not a
different notion of who you are, and there is no second mapping to drift.

**Boards are excluded deliberately.** A sensor deep-sleeps and wakes for seconds; a TLS handshake
on every wake costs radio time and battery on the most constrained thing in the system, which is
also the thing already failing at −76 dBm. The password door stays open for them.

**A broker per world, which is what makes the rest simple.** Mosquitto costs about 2 MB, so
running one per world is nearly free — and it removes more than it adds. Each broker's ACL
derives from *one* world's wiring instead of every provisioned world at once; each trusts exactly
one certificate authority instead of a bundle reassembled whenever a world appears; and a new
world disturbs nothing, because it brings its own. The ports come from that world's own
`mqtt:MessageBus`, which the model already stated — no new vocabulary was needed, they had simply
all said 1883 because there was one broker.

It also makes the isolation **structural rather than enforced**, which is the rule the belief
base already follows. Measured: a `sensing` certificate presented to `society`'s broker is
refused, and accepted by its own. No ACL is consulted to achieve that — the two societies have no
process in common.

The old arrangement is worth remembering as the thing this replaced: one broker, a `passwd` and
an ACL spanning every world (the code called it "the operator's view by necessity"), a trust
bundle concatenating every authority, and a restart — dropping every connected agent — whenever
a world was born.

**A CA per world, and an installation CA for shared services.** Two worlds are two societies: a
certificate issued by one must not authenticate into the other, the same argument that gives each
world its own signing keys. The broker's own identity belongs to neither — it serves every world
— so it is signed by an installation CA, and issuing it is a **separate command with a separate
lifecycle**, `orexis-broker-cert`. Infra may be deployed at another time on another host by
someone holding none of these worlds; onboarding a world must not require write access to it. The
only thing crossing that line is one public file per world, its `ca.crt`.

## The dashboard is generated too, and lands in shared infra

A dashboard listing agents by hand is a second list to drift, and it had already drifted: the one
shipped here queried a bucket named `sensors`, which has not existed since each agent got one of
its own. It is derived now — a panel per watcher, against the bucket `orexis-influx` actually
created.

Two dashboards, not one: `orexis.json` is what the plants are doing, `health.json` is whether the
society reporting it is still working — see [agent-metrics](/domain/agent-metrics.md). They are
separate because a flat-zero write-failure count next to a moisture curve reads as noise until
the moment it is the only thing that matters.

Its output goes to `infra/grafana/dashboards/<world>/`, which is the one exception to
*nothing in `infra/` is world-specific*, and the exception is the point: **Grafana is the only
service that legitimately spans worlds.** It is the operator's view of every society at once,
which is why it holds a read token across all buckets — splitting it per world would defeat what
it is for. The alternative, mounting each world's directory into it, would hand a network-facing
service read access to every world's private keys.

## A board is told the same things the agents are

`orexis-firmware` generates a board's `config.h` from the world: the broker and port from
`mqtt:MessageBus`, the ids and topics from the society, the pin and the calibration from the stand,
the credential from `orexis-mqtt`, the cadence bounds from the ontology. Every one of those was
already written down; the header was a second copy, and the expensive kind — correcting it means
retrieving the board.

**Two routes to one broker.** An agent reaches it at `mqtt:brokerHost`, which is loopback and must
be: agents are host-networked and every member has to agree on one name. A board on the wifi
cannot use that name, so it is given the `ag:lanHost` of whichever host runs the broker. That
is a fact about the network rather than about the society, which is why it hangs off the
ComputeHost and not the bus — and it is what the hand-written headers had been quietly working
around.

**What is deliberately not generated** is anything that is a property of the code rather than the
deployment: retry counts, the listen window, the fallback cadence. The line is the one drawn
everywhere else here — if changing it changes what this board IS, it comes from the world; if it
changes how the firmware behaves, it is code, and it lives in the source with a default.

## Two operational facts worth knowing

**SIGHUP does not reload TLS material.** Mosquitto rereads `password_file` and `acl_file` on a
reload, but not `cafile`, `certfile` or `keyfile`. This used to mean a new world forced a restart
of the shared broker; with one broker per world it no longer costs anything, because a new world
starts its own. It still applies to rotating a world's own authority.

**An unreadable key fails silently.** The broker binds the TLS port, negotiates no cipher, and
logs nothing; every client reports only "connection lost". `entrypoint.sh` re-owns the key to the
broker's user at 0600 while it is still root, because mosquitto opens it *after* dropping
privileges — the tempting alternative, publishing it world-readable, puts a private key where
every host user can read it.

# It is not birth

The two are adjacent and are opposites, which is exactly why conflating them is easy.

| | onboarding | birth |
|---|---|---|
| done **to** an agent, from outside | done **by** an agent, on itself |
| by the sovereign, on the operator's host | inside the agent's own container, nobody watching |
| grants what the world already implies | authors what the agent believes |
| **repeatable** — re-run it freely | **once**; a second birth discards who the agent became |
| a token, a credential, a service | a belief base |

An agent can be onboarded a hundred times and remain the same agent. It can be born only once.
See the lifecycle table in [agent](/domain/agent.md).

# Why its code lives outside the agent's package

`onboarding/` is a package of its own, installed separately, and **not** in the agent image.

The reason is the admin token. `orexis-influx` reads it from `infra/secrets/`, and it opens every
bucket in the store — it is the one credential no agent may ever hold. The belief base is
private to its agent because nothing else can reach it, and the same argument applies here: the
surest way for an agent never to hold the admin token is for the code that uses it to be absent
from the image entirely.

That the agent image copies `backend/` wholesale is what forces the split to be a directory
rather than a naming convention. Code is not a credential and shipping it granted nothing on its
own — but `compose.py` already mounts the world **file by file** so an agent cannot read its
neighbours' opening beliefs, and it would be odd to take that care and then ship every agent the
tool that mints credentials for all of them.

## The line the split follows

Not by file, because three modules serve both sides. By **who calls it**:

| stays in `orexis` (the agent runs it) | moved to `onboarding` (only the sovereign runs it) |
|---|---|
| `genesis.open_belief_base`, `current_world` — an agent builds its belief base at boot | |
| `validate.validate_agent` — an agent checks *itself* and refuses to start | `validate_world` — does this world hold together *at all*, before anything starts |
| `signing.sign`, `load_private`, `verify_command` — an actuator co-signs and a device checks | `create_keypair` — minting a society's keys |

The last row is the sharpest. An actuator **loads** the two keys mounted into its container and
can do nothing else with them; an agent that could *mint* a society's keys could sign for that
society — authorise a match it never won, and validate its own claim. Same argument as the
admin token, one level down.

`conforms` and `graph_from` are public in `orexis.validate` because both checks run the same
machinery over the same graphs. Two ways to decide whether beliefs hold would be one too many.

See [series-and-bus-isolation](/decisions/series-and-bus-isolation.md).

# Seams left open

- **Nothing revokes.** Removing an agent from a world stops it being granted anything on the
  next run, but its existing bucket, token and credential remain until removed by hand.
- **`--rotate` is the one destructive option.** It replaces credentials that are in use, so
  anything holding an old one is locked out until restarted with the new. There is no staged
  rotation.
- **Certificates expire; passwords did not.** That is a new failure mode: an agent whose certificate lapsed stops connecting and looks
  exactly like a process that went quiet. Re-running `orexis-onboard` reissues anything within 30
  days of expiry, so the routine cure is the routine command — but nothing warns you first.
- **A board belongs to one world.** Its credential lives in `world/<w>/secrets/`, like an
  agent's, because a board is flashed with one host and port and so connects to exactly one
  world's broker. A board serving two worlds holds two credentials and is re-flashed to move —
  it was already being re-flashed with that world's port. This was the last secret spanning
  worlds; nothing in `infra/` is world-specific any more.
- **A board is configured but still flashed by hand.** `orexis-firmware <world>` writes its
  `config.h` from the world, so nothing in it is typed twice — but getting it onto the board is
  still `pio run -t upload` with the board in front of you. That is the remaining manual step,
  and it is hardware's nature rather than a gap here.
