---
type: Domain Concept
title: Deployment
term: http://example.org/orexis/onboarding#DeploymentGraph
description: >-
  What has to run for a world to be a society, and where each thing is reached - brokers and
  their addresses, series stores, containers, images - stated in a graph of its own kind, read
  by onboarding, which derives what a world is connected to into a document its agents read and tells
  the rest as environment. A world may assert its broker's; the
  installation allocates one that is not asserted, in a derived graph. Never a credential.
---

# What it is

A **deployment graph** says what must be running and where it answers: the address a broker
listens on, a series store's URL and organisation, the image a container runs. Its one reader is
[onboarding](/domain/onboarding/onboarding.md). A broker is two things, and they go to two graphs:
as a rendezvous — what clients are connected to, so that two parties on one can meet — it is
named in the society graph every agent reads ([world](/domain/kernel/world.md)); the `schema:url`
it listens on is deployment.

The **installation** is the deployment graph of what every world on a host shares, asserted in
`infra/installation.ttl`: the **series store**, with its url, its organisation, its image and the
purposes it serves (`onboarding:serves` — history by exactly one store, metrics by one or none),
and how many days a purpose is kept where not for ever; the **series view**, where a person draws the series — Grafana,
with its url and image; and a pool per kind of listener it allocates ports to — a broker's, and an
agent's [journal](/domain/kernel/journal.md)'s, each saying which (`onboarding:allocatesFor`).

The installation also says **where the language model answers**, where an agent of this host may be
a [translator](/domain/translation/translator.md): one `onboarding:Model` with the `schema:url` of its
API, which onboarding states of each [model](/domain/translation/model.md) a translator's role names. Which model and the key are no deployment fact:
they are `infra/secrets/model.env`, template `infra/model.env.example`, mounted into each translating
agent's container and no other, as the admin token is mounted into no agent's. An installation naming
no model has no agent translate, and a world with one that does is refused, as a monitored world is
where metrics are served by no store. Where an agent's Telegram bot answers is the world's deployment
graph's, `<bot> schema:url`, derived into what the agent reads.

It says **where an agent's activities are sent as spans**: one `onboarding:Tracer` with a `schema:url`
and an image, Tempo. Which agent is traced is the agent's to say: a recorder whose role names a
tracer (`journal:tracedBy`) is given this one's url in its world's derived deployment. An installation naming no
tracer refuses a world whose role names one, and otherwise refuses nothing.

**What a world is connected to is derived into a document its agents read.** `orexis-onboard` writes
`world/<world>/deployment.derived.ttl`, of the kernel's kind `orexis:DeploymentGraph`: each service a role of one of its agents
names, with its `schema:url`, typed in the words of the package that uses it. Today that is the
[tracer](/domain/journal/tracer.md) a recorder's role is traced by, the
[archive](/domain/journal/archive.md) it is archived in, the
[endpoint](/domain/journal/endpoint.md) its journal is served at, and the
[series](/domain/kernel/series.md) store an observer's readings are archived in or a meter's windows are written to. The boot puts it in, no reader of the mind is handed
it, and a package asks it as it starts and ends its start where its role names no service of its kind. It names
nothing of another world. The services still told as environment move there one by one
([the-world-says-what-it-is-connected-to](/decisions/the-world-says-what-it-is-connected-to.md)).

What an agent's [journal](/domain/kernel/journal.md) counts as an incident beside its vocabulary is no deployment
fact: the [recorder](/domain/journal/recorder.md)'s role says it.

A world is **monitored** where an agent of it plays a [meter](/domain/metrics/meter.md), in its self graph. Its
meters then write their metrics — the admins' instrumentation
of how each is doing ([series](/domain/kernel/series.md)) — each to a metrics bucket of its own,
and the world gets a health dashboard per package that reports. A world with no meter is not monitored: metrics are
opted into, world by world, since they are for whoever runs the host and a world is not the
host's. The installation may serve metrics from no store, and then monitors no world; a world
with a meter there is refused at onboarding, before anything is granted. The greenhouse's grower
and the terrace's agent play one.

**Asserted wins, derived completes.** A world may assert where its broker listens, in a
`deployment.ttl` of its own, and is told exactly that — the terrace does, since a board is flashed
with its port. A world that asserts nothing leaves the choice to the installation, which
**allocates** it: a port is unique across the host and only the installation sees the host, so the
one reader that can choose safely is the one that chooses. What it allocated is a **derived**
deployment graph, `infra/installation.derived.ttl` — committed, read back as derived, and kept, so
a world added later never moves another's port. What is refused is a **collision**: two brokers on
one host and port, asserted or allocated, or a broker on a service's — by onboarding's
[requirement](/domain/onboarding/requirement.md) that one port on one host is held by one listener,
judged over everything the installation holds. Every address is a
`schema:url`, so the host is stated where the port is. The installation may name worlds; a world
names nothing of the installation, and onboarding asks it about one world's broker at a time.
Every agent's journal is allocated the same way and never asserted, on the host's loopback, a
port of the journals' pool free of every service, broker and journal before it, written
`onboarding:journal` on the agent, and stated in the world's derived deployment as the url of the
[endpoint](/domain/journal/endpoint.md) that agent's recorder role names.

# How it reaches an agent

Not as a document. The kind is declared in onboarding's vocabulary, which no agent loads, so an
agent's boot passes over it. Onboarding reads it and writes what an agent needs of it into that
agent's environment — the broker's address, the series store's — which is how a deployment fact
has always reached an agent; what changed is that the facts start in a document and not in a
hand-kept `.env`, so the compose files, the installation's included, are derived.

**Never a credential.** A deployment graph says where, never what may be done there. A token in
a graph would persist in the agent's volume, be copied into every possible world a search forks,
and sit one careless select away from a document speech builds for a peer; credentials are minted
into `world/<name>/secrets/` and mounted into one container.

# What is built

`onboarding:DeploymentGraph` is declared in onboarding's vocabulary (`onboarding/ontology.ttl`)
beside the installation's words — `onboarding:SeriesStore`, `onboarding:SeriesView`, `onboarding:Tracer`,
`onboarding:organisation`, `onboarding:image`, `onboarding:allocatesFrom`, `onboarding:allocatesFor`,
`onboarding:journal`, `onboarding:serves`,
`onboarding:retentionDays`, the two `onboarding:SeriesPurpose`s,
— so an agent's boot passes over a graph of it. The terrace,
the greenhouse and the allotment assert their brokers' urls; the sensing world asserts none and is
allocated the 1884 and 8884 it once asserted.

`onboarding/installation.py` reads the installation, and `orexis-onboard` derives with it first:
`derive` holds the services, every asserted url and every allocation already made, and gives each
broker left the lowest slot of the pool free of all of them — Python, since it is a search that
remembers, where a join would be a rule (`onboarding/derived.py` writes either and reads it back
with `orexis:arrivedBy orexis:Derived`). Then every renderer only formats: `broker` in
`onboarding/mqtt.py` answers the asserted url or the allocated one, for the compose file, the
broker's config and a board's `config.h`. Which purposes a world's agents are told of is
`purposes` in `onboarding/installation.py` — history always, metrics where the world is monitored
— and every tool asks it: the world's derived deployment states, for each, the store serving it as an
`orexis:SeriesStore` with its url and organisation, and for metrics the window; `orexis-compose` mounts each
purpose's credential; `orexis-influx` mints each one's buckets in that store, kept as long as the
purpose's retention says, and revokes the metrics grants of a world that stopped being monitored;
`orexis-dashboards` draws health for a monitored world alone; and `orexis-infra-compose` writes
`infra/compose.yaml`, the images and ports the document's and the rest the template's.
What the installation must state is its own [requirement](/domain/onboarding/requirement.md),
`infra/requirements.ttl` beside it, judged as the document is read: one store and one view, their urls, images and the store's
organisation, history served, one retention and one window per purpose, one pool with a host and a
port in every url, and no credential anywhere. `tests/test_layout.py` holds both committed documents
to a fresh rendering and refuses a collision, a hand-edited allocation, each of those, a monitored
world where metrics are served by none, and an installation saying anything but a type, a url, an
organisation, an image, a purpose served, a retention, an interval or a pool. The kind is decided in
[a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md), the
allocation in its amendment, and monitoring in its last.
