---
type: Domain Concept
title: Service — something a package offers, that nothing grants
description: >-
  A thing one package makes available for others to use, reached by term and never by import.
  Distinguished from a capability by how it comes to exist: a capability is derived from a
  premise the world states, so an agent may or may not hold one; a service simply exists for
  any agent whose build includes the package that offers it. Nothing is built yet — the word is
  minted here because the design that needs it is recorded, and a word used before it is
  defined is a word everyone defines differently.
---

# What it is

A **service** is something one package offers for other packages to use — a store, a sink, a
client, a registry — reached by its term through the agent that owns it.

The distinction that matters is **how it comes to exist**. A [capability](/domain/capability.md)
is derived: the world states a premise, genesis works out who qualifies, and an agent may hold it
or not. A service is not derived and not granted. It exists for any agent whose build includes
the package offering it, and there is no fact in any world that decides otherwise.

That is why it needs its own word. Calling a series sink a capability would put it through
machinery built for a question it does not raise — *which agents qualify?* — and the honest
answer for a sink is *all of them, or none, depending on what was installed*.

# What it is not

- **Not a capability.** No premise grants it, no `rules.ru` derives it, and no world can refuse
  one agent a service another agent has.
- **Not a [module](/domain/choir.md) answering a question.** The choir collects from everyone who
  has an opinion; a service is one thing, looked up. Fan-in where the choir is fan-out.
- **Not a store, though a store may be offered as one.** The agent owns its stores today —
  beliefs, desires, intentions — and reaches them by attribute. Offering one as a service is what
  would let a package bring a store of its own, which nothing yet does.

# Where it sits

Three ways a package reaches another package's work, and a service is the third:

| what you want | how |
|---|---|
| everyone's opinion | `agent.ask(POINT)` — the choir |
| whoever implements an ability | `agent.provider(family)` — one member of a derived family |
| **a particular thing another package offers** | **a service, by term** |

# Nothing is built

There is no `@provides`, no `agent.service()`, and no service in the tree. The word is minted
because [an-injected-service-is-reached-by-term](/decisions/an-injected-service-is-reached-by-term.md)
records the design, and a record may not use a word the dictionary lacks. What would make it real
is a package needing to bring one — [#311](https://github.com/ShishkinDmitriy/orexis/issues/311),
the history ring, is the first.
