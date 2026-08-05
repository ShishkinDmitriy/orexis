---
type: Domain Concept
title: Onboarding — a ratified world, granted the means to run
description: The phase between genesis and a running society. What it grants, why every grant is derived from the wiring rather than decided here, why it is not birth, and why its code lives outside the agent's package.
tags: [onboarding, credentials, provisioning, lifecycle, isolation, deployment]
timestamp: 2026-08-05T00:00:00Z
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
agora-onboard <world>
```

# What it grants

| tool | grants | derived from |
|---|---|---|
| `agora-influx` | a bucket per agent, and a token that opens only it | who the agents are |
| `agora-mqtt` | a credential per principal, and the broker ACL | what each agent is wired to |
| `agora-compose` | the roster, as services | the roster, and who actuates |

`agora-onboard` runs all three, after `agora-validate`. They remain separately callable, because
rotating one service's credentials should not touch the other's.

# Nothing here decides anything

Every grant is **derived** from wiring the sovereign already ratified. That is not an
implementation detail — it is what makes onboarding a single command rather than a checklist,
and what makes re-running it safe. Adding an agent to a world and running it again is the whole
of onboarding that agent; there is no list to keep in step, because there is no list.

It is the same move [world-graph](/decisions/world-graph.md) makes everywhere else: the model is
the single source, and anything that could drift from it is computed instead of written down.

Validation comes first for a reason worth stating. Onboarding a world that does not hold
together mints real credentials for agents that will then refuse to start, and leaves them lying
around — so `agora-onboard` refuses rather than grants.

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

The reason is the admin token. `agora-influx` reads it from `infra/secrets/`, and it opens every
bucket in the store — it is the one credential no agent may ever hold. The belief base is
private to its agent because nothing else can reach it, and the same argument applies here: the
surest way for an agent never to hold the admin token is for the code that uses it to be absent
from the image entirely.

That the agent image copies `backend/` wholesale is what forces the split to be a directory
rather than a naming convention. Code is not a credential and shipping it granted nothing on its
own — but `compose.py` already mounts the world **file by file** so an agent cannot read its
neighbours' opening beliefs, and it would be odd to take that care and then ship every agent the
tool that mints credentials for all of them.

See [series-and-bus-isolation](/decisions/series-and-bus-isolation.md).

# Seams left open

- **Nothing revokes.** Removing an agent from a world stops it being granted anything on the
  next run, but its existing bucket, token and credential remain until removed by hand.
- **`--rotate` is the one destructive option.** It replaces credentials that are in use, so
  anything holding an old one is locked out until restarted with the new. There is no staged
  rotation.
- **Devices are onboarded but not configured.** `agora-mqtt` mints a credential per board, and
  putting it into firmware is still a manual flash. A board that has never been given one cannot
  connect at all, now that the broker refuses anonymous clients.
