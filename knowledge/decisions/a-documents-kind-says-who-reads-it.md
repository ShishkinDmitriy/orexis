---
type: Decision
title: A document's kind says who reads it, and every reader loads only the kinds it reads
description: >-
  A world is self-describing documents, each stating its graph's kind, and the kind now says who
  reads it - the agent, onboarding, the firmware generator. Every reader loads the kinds it reads
  and passes over the rest, the agent's boot included, so need-to-know is structural rather than a
  list of file names kept out. Seven consequences follow from the one idea - packages loaded by a
  premise read off the world, a transport connection per broker, a series store per purpose,
  history contributed by the package that decides each thing, metrics as each package's selects,
  and the shared services stated in an installation document. Supersedes metrics-are-an-aspect.
status: accepted
timestamp: 2026-09-27T12:00:00Z
---

# What was true (measured 2026-09-27, on main at 90e5b00b)

**The boot reads everything.** `documents()` in `agent/runtime.py` takes the kernel's T-Box, every
package's documents by `rglob`, and every document in the world's directory. Hanoi's mover, which
senses nothing, predicts nothing and has no bus, reads eleven documents before its imports, and
four of them are for things it never does: sensing's ontology and its three rules, prediction's
ontology, and the MQTT transport's. The runtime imports sensing, prediction, speech and execution
modules at its head whatever the world, and the MQTT driver imports sensing's `received` and
speech's `heard` at its own. The transport alone is chosen by what the world says
(`_transport_of`).

**The hardware reaches the agents.** Both `hardware.ttl` files, terrace's and sensing's, say
`<> a orexis:PublicGraph`. Booted from its directory, the terrace agent holds the terrace's 116
hardware quads as public knowledge and sensing's fern holds 147. A container holds none only
because `onboarding/compose.py` leaves a file NAMED `hardware.ttl` unmounted (`HARDWARE_FILES`).
The cause is one level down: every onboarding tool reads the world through the agent's own boot
(`world_of`), so whatever `orexis-firmware` needed had to be a kind the agent knows, and
need-to-know fell to an exclusion list keyed on a file name — which "a document says which graph
it is, and the file's name is for eyes" refuses everywhere else.

**Every agent loads its broker's address and none reads it.** Each of the four worlds with a bus
states one `mqtt4ssn:Broker` and its `schema:url`s in its world graph, beside the agents, their
clients, the topics and the subjects — the allotment's holds three agents and 42 lines of MQTT4SSN
in one graph. `broker()` in `onboarding/mqtt.py` reads every url on every broker, keeps the first
host and a port per scheme, and refuses nothing.

**The series is one property's shape, and the runtime chooses what goes in.** `agent/series.py`
writes every observation as measurement `soil_moisture`; the terrace's test pins its air
temperature (14.5), humidity and pressure there. The runtime hands the sink each observation graph
sensing wrote, so history is what the runtime chose — observations — and no step taken has ever
reached a panel. 0.2.0 writes no metrics at all: the choir that
[metrics-are-an-aspect](/decisions/metrics-are-an-aspect.md) used as its registry went with 0.1.0.

# What is decided

**A document's kind says who reads it, and every reader — the agent's boot included — loads only
the kinds it reads.** A world is a set of self-describing documents, each saying `<> a <Kind>` as
it already does; today the only kinds are the agent's. Every reader gets kinds of its own:

| kind | holds | read by | declared by |
|---|---|---|---|
| world, state | subjects, sensors, systems, the puzzle, where things stand | the agent | the kernel, as today |
| desires, wants | what an agent pursues | the agent it is for | planning, as today |
| society | the agents, the client each is, the brokers as what clients connect to, topics, filters | the agents; `orexis-mqtt` for the ACL; the simulator | the kernel |
| deployment | brokers' addresses, series stores, containers, images | onboarding alone | onboarding |
| hardware | boards, pins, parts, wire colours | `orexis-firmware` alone | onboarding |

The words are defined in [world](/domain/kernel/world.md), [deployment](/domain/onboarding/deployment.md)
and [onboarding](/domain/onboarding/onboarding.md). The terms are the implementing change's to
spell — `orexis:SocietyGraph` beneath `orexis:PublicGraph`, and `onboarding:DeploymentGraph` and
`onboarding:HardwareGraph` in onboarding's first vocabulary document are the obvious ones — but
the OWNERS are decided, and each has a reason:

- **The society is the kernel's** because the boot reads off it which packages to load, before
  any optional package is loaded; a kind declared by the transport would be unknown at the moment
  it is needed.
- **Deployment and hardware are onboarding's** so that the agent never names them, which keeps
  `lint-imports`' direction — onboarding may import agent, never the reverse — and makes the
  agent's ignorance of them structural: its T-Box cannot say what they are.

What follows is seven cases of the one idea.

## 1. The boot loads a kind it knows and passes over the rest

A document whose kind the agent's T-Box does not declare is not read. Need-to-know is the default,
not an exclusion list: a new kind of document reaches no agent until an agent's vocabulary says
what it is, where an exclusion list gives a new file to every agent until someone remembers to
list it. The hardware principle stands as it was written — the GRAPH gets a kind, and the parts
inside stay untyped, since a vocabulary one string-filling reader uses checks nothing.

Onboarding reads the world as an agent boots it and then its own kinds, rather than borrowing the
agent's boot whole, which is what made the hardware public in the first place.

*One addition, not in the conversation that decided this:* passing over an unknown kind makes a
misspelled kind silent. It is silent today in effect — an unknown kind in a world is put in as
the agent's own graph and no reader asks for it — but the new rule would make it the rule. So
onboarding, which knows every reader's vocabulary, refuses a document that no reader reads, the
way it already refuses a world whose documents will not load.

## 2. Packages are derived, not all loaded

Belief, planning and execution are the mind and are always loaded; the ruling that the container
builds the mind for every agent ([a-layer-is-a-package-and-need-loads-it](/decisions/a-layer-is-a-package-and-need-loads-it.md))
survives. Every other package is loaded — its documents read and its modules imported — when a
premise read off the world holds:

| package | premise |
|---|---|
| sensing | a sensor hosted by what the agent acts for |
| prediction | a `prediction:Drift` declared by a domain the world imports |
| speech | the agent `mqtt4ssn:listensToTopic` a topic, or an action it may take has an `execution:Saying` operation |
| transport | as today: a sensor it claims, or a topic the agent listens to |

*Two rows were narrowed when the premises were built, and where a premise is stated was settled
then too: see the amendment below (#824).*

**Refused: the agent's own file declaring its packages.** It is a second source of truth beside
the world, and it can be wrong in the other direction — a sensor stated with no package to read it,
or a package declared for a sensor since removed — with nothing to say which of the two is right.

**Said honestly: derivation does not protect against a wrong world.** A world that forgets a
sensor's host loses sensing as surely as a mistaken declaration would. What derivation buys is
that nothing is loaded that no fact asked for, and one source rather than two.

The precedent is 0.1.0's: a capability granted by its premise
([capability-packages](/decisions/capability-packages.md),
[self-review-is-a-capability](/decisions/0.1.0/self-review-is-a-capability.md),
[an-amendment-endows-what-it-grants](/decisions/an-amendment-endows-what-it-grants.md)). **This
does not revive the `Capability` page type.** What returns is the premise; what does not is a
family of interchangeable members, which the type's definition requires — sensing, prediction and
speech have one implementation each, and only the transport is a family. A package loaded by a
premise is still a [package](/domain/kernel/package.md). The type has had no page since the
dictionary was filed by package, and a type with no member is one to fold back (#828).

## 3. A transport connection per broker, found through the clients

A transport does two jobs, agent to device and agent to agent, and the two may be on different
brokers. MQTT4SSN says (checked against the vendored copy): a `mqtt4ssn:Client`
`mqtt4ssn:isConnectedToBroker` a `mqtt4ssn:Broker`, the property is not functional, and **no
property relates a topic to a broker** — of the eleven properties touching `Broker`, none has a
topic at either end. So a topic's broker is found through the clients on it: a sensor's topic is
on the broker its board is connected to, and a peer's inbox on the broker the listening peer is
connected to. The agent opens one connection per broker it shares with something it needs,
derived, and declares no word of its own.

The kinds make the address principle structural. The broker as a rendezvous is in the society
graph; its `schema:url` is in the deployment graph, which the agent does not load, so an agent
reading its own broker's address off the world is no longer a discipline to keep but a thing it
cannot do. What is left open is only how several addresses are TOLD — the first seam below.

**Nothing is filed to build this yet.** All four worlds with a bus state one broker; the latent
defect was `broker()` merging several without a word, and it refuses them now (#821).

## 4. A series store per purpose: history and metrics

A broker is agreed on by everyone connected to it, so it is named in a world; a series store has
one writer and nobody to agree with, so it is not a world fact
([series-and-bus-isolation](/decisions/series-and-bus-isolation.md) already argued this for a
bucket). Its PURPOSES, history and metrics, are concepts the code may name
([series](/domain/kernel/series.md)), so the environment is keyed by purpose —
`INFLUX_HISTORY_*`, `INFLUX_METRICS_*` — and may point both at one instance by coincidence.
`orexis-influx` mints one credential file per purpose. A sink is loaded as a derived package is,
and its premise is the one read off the environment rather than the world, because a store is
deployment: the environment names a store for its purpose.

**If the agent ever reads its history** — to learn a drift, say — that store is a source, it
arrives through sensing and a transport like any testimony, and it is no longer a sink.

## 5. History is contributed by the package that decides each thing

Sensing contributes an observation when `received` writes the `sosa:Observation` — one point per
property, measured under the property's own name. Execution contributes a step taken when `drain`
writes the `execution:Act`, and its outcome, landed or failed, at the landing verdict, with the
action, the want and the values. The sink is beneath both and knows nothing of what it writes.
This replaces the runtime handing the sink each observation graph: the runtime was deciding what
counts as history, which is a decision it does not own, and it decided observations only.

## 6. Metrics come back as each package's selects

0.2.0's health is mostly rows already: a plan's `planning:Exhausted`, the weighings a pass wrote,
an intention whose `execution:outcome` is failed, `sensing:silentSince`, a revision whose
`belief:settled` is false. A package ships its metric selects in its own documents, in a kind of
their own that is **not public** — read by the metrics sink alone, so a select never crosses into
a possible world — and the sink runs every one it finds by kind, each pass
([a-reader-states-the-kinds-it-reads](/decisions/a-reader-states-the-kinds-it-reads.md)). No
registry lists them. Only a pass's duration, the store's size and uptime are the runtime's own
figures.

## 7. The shared services are an installation document

The shared series store lives in `infra/compose.yaml` and `infra/.env` today. By rule 3 — nothing
in `infra/` is world-specific, and no world may know that the others exist — the shared services
are described by an installation document under `infra/` whose kind is deployment, and each
world's broker by that world's own deployment graph — amended below: a world may, and one that
does not is allocated its port by the installation. `orexis-compose` already derives the agents'
services from the roster (`onboarding/compose.py`); with brokers, stores and images in documents,
the rest of a compose file is derivable too.

**Tokens and secrets never enter any graph.** The store persists in a volume, a possible world
copies every public graph, and speech builds the documents it sends a peer from the store; a
secret in any of them is a secret one select from leaving. A deployment graph says where, never
what may be done there.

## Amended 2026-09-27: a port no world asserts is the installation's to allocate (#827)

Each of the four worlds with a bus stated its own broker's urls, on 1884, 1888, 1889 and 1890, and
they missed each other only because whoever wrote each world knew which ports the others had
taken — coordination a world is not allowed to have, since it may not know that the others exist.
A port is unique across the host, and only the installation sees the host.

**Asserted wins, derived completes.** A world may still assert its broker's urls, and is told
exactly those; the terrace does, since its board is flashed with 1888. A world that asserts none
is allocated them by the installation: `infra/installation.ttl` states a pool
(`onboarding:allocatesFrom`), and a broker is given the lowest slot at which every url of the pool,
raised by the slot, is free of everything asserted, everything allocated and the installation's
own services. What was allocated is a derived deployment graph, `infra/installation.derived.ttl`,
committed and read back with `orexis:arrivedBy orexis:Derived`. The sensing world asserts nothing
now and is allocated the 1884 and 8884 it asserted before, so its board needs no reflashing.

**Derived TTL is the middle layer.** The compose file, the broker's config, an agent's
environment and a board's `config.h` only format what the asserted and derived graphs say; none
computes a port, and every allocation is a line a reviewer reads in a diff. A test holds the
committed derivation to a fresh one. `onboarding/derived.py` writes and reads such graphs and knows
nothing of ports, since #836 derives topic names into the same layer. The allocation is Python and
not a SPARQL rule, because it is a search that remembers, which a rule over this engine does badly;
a derivation that is a join would be a rule, writing the same kind of graph.

**What is refused is a collision**, never resolved: two brokers on one host and port, asserted or
allocated, or a broker on a service's port — named, and nothing written. A world asserting the port
already allocated to another is refused rather than moving the other, which may be a board in a pot.

**Refused: a world stating its own port, always** — this change's first cut, and the extended
issue's wording. It would move the terrace's pinned port into the installation, and make the
installation a list of every world to keep in step with the worlds. **Refused: allocating afresh
each run**, by a world's position among the rest: a world whose name sorts first would take
1884 and move the sensing world's board. So the derivation remembers — an allocation kept for as
long as its broker exists and asserts nothing — and, since its own output is then one of its
inputs, a kept allocation must be one slot of the pool, or the document was edited and is refused.

This is how rule 3 and the installation naming worlds stand together. The derived graph names
every broker it allocates, because the installation is the one reader that sees every world
anyway; a world names nothing of the installation, and `broker` asks it about the one broker the
world's own society names, so no world is told another's address.

**The host stays in the url.** Every address is a `schema:url` — asserted, allocated, or the
pool's — the one address word every reader reads, so an installation split over two machines needs
no second word, and a clash is one host and one port, never the port alone.

**`infra/compose.yaml` is derived** from the installation by `orexis-infra-compose`: the images,
the ports and the organisation are the document's, how each service runs is the template's, and a
test holds the committed file to the rendering. The seam this record left for it is closed.

## Amended 2026-09-27: the premises as built, and where they are stated (#824)

Each premise was checked against what its package's callers read, and two rows of §2's table
changed:

- **Prediction needs a sensor of the agent's as well as a drift.** `predict` is asked of a sensor
  that has just reported, and moves nothing without one; on a drift alone, the allotment's
  supplier — which senses nothing, in a world importing climate — would have loaded it for nothing.
- **The transport's sensor is the agent's own**, hosted by what it acts for, which is what the
  member subscribes to; "a sensor it claims" was any sensor in the world that published on a
  topic. `claims` itself is gone: its one caller imported the member to ask it, which is the
  import a premise exists to decide.

Sensing and speech stand as written. Speech reads nothing of the world — `heard` reads a peer's
document and `said` the agent's own — so its premise is its callers' needs, the transport's
listening and execution's saying.

**Where a premise is stated: the runtime, as an ASK per package** (`PREMISES` in
`agent/runtime.py`), over the world's public graphs with the agent bound, T-Box terms only, so
rule 1 holds. **Refused: each package's own document stating its premise**, read before the
package is. It reads as the more self-describing choice, and it fails on speech first: speech's
premise is in execution's words, which its layout test refuses it as the layer above, and in the
transport's, whose imports the same test refuses. A premise is about who CALLS a package, and the
caller — the runtime, the one file every layout test exempts as the container — is where its
words may all be spoken. It fails a second time on the Python: what a premise decides is an
`import` the runtime makes, so a premise in a document would have the runtime identify which
package held, by an instance in a document or by a path, to decide what to import.

**The order problem is met by reading the premises of the kernel's and the mind's kinds alone.**
The boot puts the kernel, the mind and the world in, closes the catalogue, finds the agent, asks
the premises, and only then reads the documents of the packages that held, closing the vocabulary
again and taking a second look at a world graph passed over for a kind only such a package
declares. A premise naming a package's word — `prediction:Drift` — matches the IRI with no
vocabulary behind it, so climate's drifts are read whether prediction is loaded or not. With no
agent, `world_of` reads every package, since the operator's tools read every reader's vocabulary.

Measured on Hanoi's mover, before and after: sensing's ontology and its three rules, prediction's
ontology and the MQTT transport's were in its store and are not; prediction, sensing and speech
were imported at boot, and the MQTT driver by `main`, and none of the four is now, run to met in a
fresh process — beside the allotment's fern grower, which imports all four, so the probe is seen
to see them.

# What this supersedes, and what it amends

**[metrics-are-an-aspect](/decisions/metrics-are-an-aspect.md) is superseded.** It stood on three
premises. *Each package counts its own* survives and is sharpened: a package no longer counts at
all, it states a select over rows it writes anyway. *The choir is the registry* — `agent.ask("reports")`
— is gone with the choir, and what replaces it keeps the argument while changing the mechanism:
discovery by a mechanism the kernel already has, now a graph's kind, so there is still no
registry for a package to know about. *One sink, one credential* survives per purpose. What it
listed as unchanged — `agent_health`, `agent_sensor_health`, mandatory reporting — has not existed
since 0.1.0 was retired, and its two seams (a `reports()` key collision, `record` reaching whoever
answers) went with the hooks they were about.

**It amends two principles** in `AGENTS.md`, edited in the same change:

- *A broker's address is the world's to state and the agent's to be told* — still true, and now
  structural: the world states it in a deployment graph the agent does not load, and an agent may
  be told several, one per broker it shares with something it needs. Amended in turn (§7): a world
  may state it, and the installation allocates one the world leaves out.
- *A series is watched and never believed, and it keeps the shape the panels draw* — the first
  half stands; the second falls. The shape was 0.1.0's, kept so the terrace's panels drew across
  the switch, and it was the shape of one property: every other lands as soil moisture. History is
  measured per property, and the panels follow.

**It makes two older claims false, reconciled here too.** [series-and-bus-isolation](/decisions/series-and-bus-isolation.md)
said topics and the broker are ratified in `world.ttl`; they are ratified in the society graph,
and the broker's address in the deployment graph. [world-graph](/decisions/world-graph.md) moved
the broker "to the world" as the one piece of infrastructure all members must agree on; the
rendezvous stays public, its address does not.

# Seams left open

- **How several broker addresses, and a credential per broker, reach an agent.** Two constraints
  are fixed: the agent never constructs a name from an instance (a bucket's name was refused on
  that ground in series-and-bus-isolation), and it never reads a deployment graph. Within them,
  environment keyed by the broker's IRI and a mounted file per broker are both open. The trigger
  is the first world stating two brokers; until then onboarding refuses such a world (#821).
- **A sovereign-owned graph of tuning figures**, re-read at boot, for what is hard-coded now:
  `BUDGET` in `agent/planning/planner.py` (32), `agent/belief/revise.py` (64) and
  `agent/belief/deliberator.py` (256), `DEFAULT_PATIENCE_S` in `agent/execution/executor.py`, and
  `SILENT_AFTER` in `agent/sensing/missed.py`; only the planner's has an override, `--budget`.
  Not decided. The kind rule says who would read such a graph; what is not settled is whether a
  figure no plan branches on is a belief at all
  ([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).
- **A wrong world is not caught by derivation.** A premise misstated loads the wrong packages as
  confidently as a right one loads the right ones; what would catch it is a world's own tests.

# Verified, and assumed

Verified on 2026-09-27: the documents hanoi's boot reads (`documents()` listed); the hardware
quads a directory boot holds (116 and 147, counted in the booted store's public graphs); one
broker per world with a bus (four of four); the `soil_moisture` measurement for every property
(the code, and the terrace test's pinned points); the MQTT4SSN properties touching `Broker`
(parsed from the vendored copy); the five hard-coded figures and their lines.

Assumed: that selects over existing rows cover what an operator needs of an agent's health — not
checked figure by figure against 0.1.0's health point, which nobody has missed since it went; and
that the premises in the table above are the right ones, which each package's issue settles
against its own reads.

# Issues it filed

- #820 — load only the kinds a reader reads; the hardware graph leaves the agents.
- #821 — refuse a world stating several brokers rather than merge their addresses.
- #822 — measure each observation under its property.
- #823 — split the society and the deployment out of each world graph.
- #824 — load a package only when its premise holds.
- #825 — history per purpose, contributed by sensing and execution.
- #826 — metrics as each package's selects.
- #827 — the installation document.
- #828 — fold back the `Capability` page type.

Transport per broker has no issue on purpose: no world needs it yet, and #821 holds the line until one does.
