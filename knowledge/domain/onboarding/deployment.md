---
type: Domain Concept
title: Deployment
description: >-
  What has to run for a world to be a society, and where each thing is reached - brokers and
  their addresses, series stores, containers, images - stated in a graph of its own kind, read
  by onboarding alone and handed to an agent as environment. Never a credential.
---

# What it is

A **deployment graph** says what must be running and where it answers: the address a broker
listens on, a series store's URL and organisation, the image a container runs. Its one reader is
[onboarding](/domain/onboarding/onboarding.md). A broker is two things, and they go to two graphs:
as a rendezvous — what clients are connected to, so that two parties on one can meet — it is
named in the society graph every agent reads ([world](/domain/kernel/world.md)); the `schema:url`
it listens on is deployment.

The **installation** is the deployment graph of what every world shares — the series store and
Grafana — kept under `infra/`, since nothing there may be true of one world and no world may know
that the others exist. A world's own deployment graph states its broker.

# How it reaches an agent

Not as a document. The kind is declared in onboarding's vocabulary, which no agent loads, so an
agent's boot passes over it. Onboarding reads it and writes what an agent needs of it into that
agent's environment — the broker's address, the series stores' — which is how a deployment fact
has always reached an agent; what changes is that the facts start in a document and not in a
hand-kept `.env`, so the compose file can be derived whole.

**Never a credential.** A deployment graph says where, never what may be done there. A token in
a graph would persist in the agent's volume, be copied into every possible world a search forks,
and sit one careless select away from a document speech builds for a peer; credentials are minted
into `world/<name>/secrets/` and mounted into one container.

# What is built

Nothing yet. The four worlds with a broker state its address in their world graph, where every
agent loads it and none reads it, and the series store's address is in `infra/.env`. The kind is
decided in [a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md),
and #820, #823 and #827 build it.
