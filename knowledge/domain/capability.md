---
type: Domain Concept
title: Capability
term: http://example.org/orexis#Capability
description: >-
  A named ability with INTERCHANGEABLE IMPLEMENTATIONS — the family is the slot, its members are
  the ways of having it, and a caller asks for the family and never learns which member
  answered. That interchangeability is the test: where nothing could differ you have a function,
  not a capability. Every one is granted by its OWN premise, stated in its own `rules.ru`, and
  there is no pattern to fit a new one into — wiring grants some, latitude one, a stake another,
  a stake AND a lever two more. Never hand-declared: `world.ttl` must not contain
  `ag:hasCapability`, because a capability nobody is answerable for is the thing the rule exists
  against.
---

# What it is

A **capability** is a named ability an agent has, and the word carries a stronger claim than
"feature": the ability is a **family** — the slot — and its **members** are interchangeable
implementations of it.

`sensing:SensingCapability` is a family. `sensing:Subscribing` and `sensing:Listening` are two
ways of having it, chosen by what the hardware can do. Reviewing your own settings by strict
rules or by asking a model is one ability with two implementations; pay-as-bid and uniform price
are one auction with two.

**That is the test to apply before naming one.** A capability worth naming is one where the *how*
could differ. Where nothing could differ, you have a function.

# What isolates one is `PROVIDES`, never a directory

A [package](/domain/package.md) is a directory; a capability is not, and one package may provide
several — `packages/capability/market/` provides bidding, hosting and the matching family, and it
is one package.

What keeps a capability separable is the **term** and the registration, not the folder:
`hosting.py` asks `agent.provider(BID_MATCHING)` and never learns which member answered, which is
why uniform price landed without touching a line of it. `PROVIDES` in a package's `__init__.py` is
how an implementation registers, and its absence is what makes a package knowledge-only.

**Packages never import each other's Python.** Reach another by asking `agent.provider(family)`,
or contribute through the [choir](/domain/choir.md) hooks.

# Each is granted by its own premise

There is no pattern to fit a new capability into. **The premise lives in the capability's own
`rules.ru`**, and it is whatever fact makes *that* capability meaningful:

| granted by | capability | the premise |
|---|---|---|
| **wiring** | `sensing`, `actuation`, `market` | equipment, or a position in a market |
| **latitude** | `review:Reckoning` | a mandate whose ends differ — settings you are permitted to move |
| **a stake** | `desire:Deducing` | `ag:actsFor` a subject that states what it needs |
| **a stake AND a lever** | `intention:Keeping`, `deliberation:Reflex` | wanting without means is a wish; means without wants decide nothing |
| **universally** | `reporting` | granted by a rule and insisted on by a shape |

When you add one, ask what makes *yours* meaningful rather than which of these it resembles. The
two that share a premise stay two capabilities, because how commitments are kept and how decisions
are reached are separately replaceable — which is the family test again.

# Deduced at genesis, never hand-declared

`world.ttl` must not contain `ag:hasCapability`. Two kinds of fact end up there and neither is
written by hand:

- **derived** — a strict function of the wiring. A board that keeps an interval gives its agent
  `sensing:Subscribing`, and nothing could have decided otherwise.
- **deduced** — someone at genesis judged that this agent should have it, and could have judged
  differently.

Both land in the world graph, and since the provenance split they are distinguishable rather than
merely distinct. So "deduced at genesis" is the rule; "computed from the wiring" is how it happens
to work for the one family whose hardware forces the answer.

**What the prohibition is actually against is a capability nobody is answerable for.** That was
unenforceable while a declared one and a derived one looked identical in the graph, which is why
the rule had to be absolute. It no longer is: a derivation writes to its own graph, the ratified
graph is exactly what the files say, and every graph says who put it there.

# What holds one to its word

A capability brings [shapes](/domain/shape.md), and they are scoped BY the capability: one applies
to an agent only where that agent derived the ability it belongs to. So the shapes an agent is
held to are a function of what the world worked out for it, and a capability granted by a premise
that no longer holds takes its obligations with it.

Where the checking happens, and what a failed check does, is [shape](/domain/shape.md)'s.

# Related

- [package](/domain/package.md) — the directory a capability ships in, and how the loader finds it.
- [shape](/domain/shape.md) — what a capability holds its agent to.
- [capability-packages](/decisions/capability-packages.md) and
  [a-package-owns-its-namespace](/decisions/a-package-owns-its-namespace.md) — why it is arranged
  this way.
