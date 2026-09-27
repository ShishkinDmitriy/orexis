---
type: Domain Concept
title: Deployment
term: http://example.org/orexis/onboarding#DeploymentGraph
description: >-
  What has to run for a world to be a society, and where each thing is reached - brokers and
  their addresses, series stores, containers, images - stated in a graph of its own kind, read
  by onboarding alone and handed to an agent as environment. A world may assert its broker's; the
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
how many days a purpose is kept where not for ever, and how many seconds one window of metrics is
(`onboarding:intervalSeconds`); the **series view**, where a person draws the series — Grafana,
with its url and image; and the pool a broker's ports are allocated from.

A world is **monitored** where its own deployment graph says so of itself, in one statement:
`<> onboarding:monitored true`. Its agents then write their metrics — the admins' instrumentation
of how each is doing ([series](/domain/kernel/series.md)) — each to a metrics bucket of its own,
and the world gets a health dashboard. A world that says nothing is not monitored: metrics are
opted into, world by world, since they are for whoever runs the host and a world is not the
host's. The installation may serve metrics from no store, and then monitors no world; a world
saying it is monitored there is refused at onboarding, before anything is granted. The greenhouse
and the terrace say it.

**Asserted wins, derived completes.** A world may assert where its broker listens, in a
`deployment.ttl` of its own, and is told exactly that — the terrace does, since a board is flashed
with its port. A world that asserts nothing leaves the choice to the installation, which
**allocates** it: a port is unique across the host and only the installation sees the host, so the
one reader that can choose safely is the one that chooses. What it allocated is a **derived**
deployment graph, `infra/installation.derived.ttl` — committed, read back as derived, and kept, so
a world added later never moves another's port. What is refused is a **collision**: two brokers on
one host and port, asserted or allocated, or a broker on a service's. Every address is a
`schema:url`, so the host is stated where the port is. The installation may name worlds; a world
names nothing of the installation, and onboarding asks it about one world's broker at a time.

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
beside the installation's words — `onboarding:SeriesStore`, `onboarding:SeriesView`,
`onboarding:organisation`, `onboarding:image`, `onboarding:allocatesFrom`, `onboarding:serves`,
`onboarding:retentionDays` and `onboarding:intervalSeconds`, the two `onboarding:SeriesPurpose`s,
and `onboarding:monitored`, which a world says of its own deployment graph and the loader keeps in
the catalogue beside the graph's kind — so an agent's boot passes over a graph of it. The terrace,
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
— and every tool asks it: `orexis-compose` writes, for each, the url and organisation of the store
serving it into every agent's environment under the purpose's keys, and for metrics the window as
`METRICS_INTERVAL_S`; `orexis-influx` mints each one's buckets in that store, kept as long as the
purpose's retention says, and revokes the metrics grants of a world that stopped being monitored;
`orexis-dashboards` draws health for a monitored world alone; and `orexis-infra-compose` writes
`infra/compose.yaml`, the images and ports the document's and the rest the template's.
`tests/test_layout.py` holds both committed documents to a fresh rendering and refuses a
collision, a hand-edited allocation, a url carrying a credential, history served by no store, a
monitored world where metrics are served by none, and an installation saying anything but a type,
a url, an organisation, an image, a purpose served, a retention, an interval or a pool. The kind is decided in
[a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md), the
allocation in its amendment, and monitoring in its last.
