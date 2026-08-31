---
type: Role
title: Sovereign
term: http://example.org/orexis#Sovereign
description: >-
  Whoever ratified a world — authored its files and stands behind them. A ROLE and not an
  identity: `orexis:Sovereign` is a `prov:Role`, there is no sovereign agent and there must not be,
  because an installation has several users and which of them was sovereign is a fact about ONE
  ratification rather than a permanent property of a person. It is outside the society looking
  in: it holds the tools no agent may hold, its authorship is what "ratified" means, and it may
  ASK a running agent but never reach into one — disclosure rather than access, read-only by
  construction because the query API cannot execute an update.
---

# What it is

The **sovereign** is whoever ratified a world: authored its files, and stands behind them.

It is a **role**, not a kind of user. The same person may hold it for one world and not another;
an installation's other users hold none. `orexis:Sovereign` is a `prov:Role`, cited by a world's
`prov:qualifiedAttribution`, and **there is no sovereign agent** — that absence is deliberate, not
an omission waiting to be filled.

The role set is open on purpose. `orexis:Operator` and whatever else is eventually needed are absent
because nothing distinguishes them yet, and a role no activity cites is speculation.

# It is outside the society, and the boundary is enforced by absence

The sovereign's tools live in `onboarding/`, beside the kernel and outside it, and the line is
drawn by **who calls a function** rather than by subject matter: an agent validates *itself* at
boot, so that code stays; only the sovereign validates a *world*, so that code moved. An agent may
load its two keys; it may not mint them.

**The surest guarantee is that the code is absent from the image.** `orexis-influx` reads an admin
token that opens every bucket and that no agent may ever hold — so what keeps it out of an agent
is the `Containerfile` not naming the tree, asserted by a test, and `lint-imports` holding the
direction: onboarding may import agent, agent may never import onboarding.

# What ratification means

A world is TTL files, and **ratified** means the sovereign wrote them and stands behind them.
There is no ceremony beyond that and no second copy of the world anywhere — an agent's belief base
is built from those files at boot and replaced from them on every start.

So the sovereign's authorship is the root of everything derived: capabilities are worked out from
what the files say, and a fact in the derived graph traces back to a rule applied to something the
sovereign wrote. **What the sovereign may NOT do is write a conclusion** — `world.ttl` must not
contain `orexis:hasCapability`, because a capability nobody is answerable for is exactly the thing
that rule exists against.

# It may ask, and it may not reach in

An agent's belief base is a file inside that agent's container, and pyoxigraph holds an exclusive
lock on it — so nothing outside the process can open it, not even the person who authored the
world.

The answer is `orexis-ask`: **one SPARQL question per message**, over the world's own bus, gated to
a single principal by the broker ACL, answered by the agent from its live store across everything
it holds. That is **disclosure, not access** — the agent answers about itself rather than being
read — and it is **read-only by construction**, because the query API structurally cannot execute
an update.

This is also why the planner writes down what it considered: a reader outside the process cannot
re-run a search to see what it saw, and that limit is the same fact `orexis-ask` exists for.

# What it is not

**Not a governor.** It states structure — who is wired to what — and never plays. The sharpest
case is who convenes a market: that is fixed by the wiring the sovereign authored rather than by
anything happening in the market, and [host](/domain/host.md) has the argument for why it must be.
The sovereign sets the board and does not move on it.

**Not an authority an agent obeys at runtime.** Its mandates arrive as constraints an agent is
validated against, not as commands. An agent that cannot satisfy them refuses to start, which is
the strongest form of obedience available and the only one that needs no enforcement.

# Related

- [world](/domain/world.md) — what gets ratified, and what genesis derives rather than accepts.
- [genesis-process](/domain/genesis-process.md) — the session in which a sovereign authors one.
- [constitution](/domain/constitution.md) — the constraints even a sovereign works inside.
- [the-sovereign-may-ask](/decisions/the-sovereign-may-ask.md).
