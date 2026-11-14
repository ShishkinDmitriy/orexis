---
type: Decision
title: The world says what it is connected to, and a package reads it there as it starts
status: accepted
timestamp: 2026-11-14T12:00:00Z
description: >-
  The sovereign's ruling of 2026-11-14. An agent was told where each service is through its environment, a variable
  per service written into its container, so a package could not ask whether a service was there and whoever ran the
  agent made its connectors for it. Decided - the world is the golden source of a package's configuration. Onboarding
  derives the services a world is connected to, each with where it answers, into a document of the world of the
  kernel's kind orexis:DeploymentGraph, which the agent's boot puts in and no reader of the mind is handed; a package
  asks it as it starts, makes what it needs itself, and ends its start where the world names no service of its
  kind. Built for the tracer first; the other services follow one by one. Credentials stay files.
---

# What was wrong

An agent's packages were configured from outside. `orexis-compose` read the installation's document and wrote each
agent's container a variable per service: `OTLP_ENDPOINT`, `INFLUX_HISTORY_URL`, `MQTT_BROKERS`, `MODEL_URL`,
`JOURNAL_PORT` and twenty more. `orexis-agent/src/main.rs` read them, made each connector and handed it to the
package it was for. Three things followed.

- **A package could not ask.** Whether the agent is traced was whether somebody had handed the shipper an endpoint.
  The package had no way to find that the world has no tracer and stop.
- **The binary knew every package.** Making each package's connector for it is why `orexis-agent` names the journal,
  the series store, the tracer and the model, and why a boot had to know what joined before anything started.
- **The source was already a document.** `infra/installation.ttl` states the tracer with its url in RDF, and a
  world's `deployment.ttl` its broker's. The environment was a second, lossy copy, made for a reader that could
  have read the first.

# What is decided

1. **The world says what it is connected to.** Onboarding derives it, from the installation's document and the
   world's own deployment, into `world/<world>/deployment.derived.ttl`: each service with its `schema:url`, typed in
   the words of the package that uses it. A tracer is `journal:Tracer`.
2. **Its kind is the kernel's, `orexis:DeploymentGraph`, and it is no belief.** The boot puts it in with the
   world's other documents. No reader of the mind is handed it and no plan branches on it, which is the test
   [model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md) sets; a
   package reads it by its kind, as it reads a stance off the self graph.
3. **A package reads it as it starts, and makes what it needs itself.** Whether to join is the package's own
   question ([package](/domain/kernel/package.md)): what ships the journal's activities joins where the journal did
   and the world names a tracer, and ends its start where it names none. Joined, it reads the url and makes its own
   sender. Nothing hands it an endpoint.
4. **Derived, not authored, where the installation decides.** Which port an agent's journal serves on is allocated
   across the host, and where the shared tracer answers is the installation's to say. A world's author knows
   neither, so onboarding writes them, as it writes `society.derived.ttl`; what a world asserts of its own
   deployment still wins. The derived document is committed and held to a fresh derivation.
5. **A credential is never in it.** Tokens and passwords stay files in the agent's own `secrets/<agent>/`
   ([an-agent-keeps-its-secrets-in-a-directory-of-its-own](/decisions/an-agent-keeps-its-secrets-in-a-directory-of-its-own.md)).

# What was refused

- **The address on the role, authored in the self graph.** A recorder's role stating the tracer's url, or its
  journal's path and port, puts a fact of the host in a document a world's author writes: the port is allocated per
  host and unknown to them, and every test that boots that world would reach for the host's services. What the
  author chooses of a role, how long a log is kept or how many readings make a sensor stuck, stays on the role.
- **The installation's document handed to the agent.** `infra/installation.derived.ttl` is the one document that
  names every world, and an agent never learns that other worlds exist. The world's derived document states what
  this world is given and nothing of another.
- **Keeping the environment and adding a flag.** A variable saying "no tracer" is the same copy with one more
  spelling of absence.

# What it changes in the rules

Rule 5 said deployment facts are environment, because they are not beliefs anyone holds. They are still not
beliefs. They are no longer environment where a package has moved: they are a graph of the world that is no belief.

# Built, and still to build

Built: the tracer. `orexis-journal-otlp/` reads `journal:Tracer` from the deployment graph; `OTLP_ENDPOINT` and
`OTLP_INTERVAL_S` are gone from the binary and from every compose file.

Still environment, to move one by one, each with its package making its own connector: the series store for
history and for metrics, the brokers' addresses, the model's url, each bot's url, the journal's port and its
archive's path, and the intervals. Tracked as #1173, not here.

# Seams left open

- **The interval a package ships at** is its own constant now. An author's choice of it belongs on the role, as a
  stance, when somebody needs to change it.
- **What an agent may do** with a service is still its credential, minted per agent. This record moves where a
  service is, not who may use it.
