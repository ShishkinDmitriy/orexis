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
`infra/installation.ttl`: the **series store**, with its url, its organisation and its image; the
**series view**, where a person draws the series — Grafana, with its url and image; and the pool
a broker's ports are allocated from.

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
`onboarding:organisation`, `onboarding:image`, `onboarding:allocatesFrom` — so an agent's boot
passes over a graph of it. The terrace, the greenhouse and the allotment assert their brokers'
urls; the sensing world asserts none and is allocated the 1884 and 8884 it once asserted.

`onboarding/installation.py` reads the installation, and `orexis-onboard` derives with it first:
`derive` holds the services, every asserted url and every allocation already made, and gives each
broker left the lowest slot of the pool free of all of them — Python, since it is a search that
remembers, where a join would be a rule (`onboarding/derived.py` writes either and reads it back
with `orexis:arrivedBy orexis:Derived`). Then every renderer only formats: `broker` in
`onboarding/mqtt.py` answers the asserted url or the allocated one, for the compose file, the
broker's config and a board's `config.h`; `orexis-compose` writes the series store's url and
organisation into every agent's environment; `orexis-influx` mints buckets in that store; and
`orexis-infra-compose` writes `infra/compose.yaml`, the images and ports the document's and the
rest the template's. `tests/test_layout.py` holds both committed documents to a fresh rendering and
refuses a collision, a hand-edited allocation, a url carrying a credential, and an installation
saying anything but a type, a url, an organisation, an image or a pool. The kind is decided in
[a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md), and the
allocation in its amendment.
