---
type: Domain Concept
title: The genesis session — from a description to a living society
description: The LLM-assisted, interactive process that turns a sovereign's description into a ratified world: what must be elicited, what "consistent" means concretely, where each agent's opening beliefs come from, and why a world's KIND changes some of them but not others.
tags: [genesis, llm, bootstrapping, beliefs, world-kind, birth]
timestamp: 2026-08-04T00:00:00Z
---

# What it is

A **genesis session** is the conversation that turns *"I have three plants, a water barrel and
some ESP32s"* into a ratified world the agents can be born from. It is deliberately
LLM-assisted and interactive: the sovereign knows the garden, the drafter knows the
vocabulary, and neither alone can produce a correct world.

That it is a *sovereign act* rather than a configuration step — narrate, draft, ratify, write —
is settled in [genesis](/decisions/genesis.md). This document is the session itself: what has to
be got out of the sovereign, how to tell when the result hangs together, and what happens
between a ratified world and a running society.

```
  narrate ──▶ draft ──▶ ratify ──▶ write ──▶ seed ──▶ birth
  (English)   (Turtle)  (human)   (genesis/) (derive) (agora-up)
```

# Why it has to be a conversation

A world is not a form to fill in. Almost every field implies a question the sovereign has not
thought about, and the questions only surface once something concrete is on the table:

- "the fern's sensor" → *is that board reachable at any moment, or does it sleep?* — because
  that alone decides whether its agent gets `ag:Polling`, `ag:Subscribing` or `ag:Listening`
  (see [who-holds-the-clock](/decisions/who-holds-the-clock.md)).
- "they share the barrel" → *who owns it?* — because owning the venue is what derives
  `ag:Hosting`, and owning the valves is what derives `ag:Actuation`. A barrel with no owner
  produces a market nobody hosts.
- "the fern is thirstier than the succulent" → *thirstier at what number?* — a band is the
  agent's own opinion and nothing can infer it.

The drafter's job is to keep asking until every derivation has an answer, then propose Turtle.
The sovereign's job is to ratify or correct it. The LLM is a **drafting assistant, not an
agent**: it holds no stake and proposes only.

# What must be elicited

The session is finished when all of these have an answer, because each is something no default
can supply honestly:

| | why it cannot be guessed |
|---|---|
| every subject, and what is observed about it | the domain is a plug-in; nothing knows a "plant" is intended |
| every device, and **how it is driven** (`ag:senseMode`) | this is what derives the perception capability |
| where each device is reachable — its bus and channels | nothing builds a topic from a naming convention |
| who is wired to what (`ag:polls`, `ag:hasActuator`) | this *is* the access grant, not a separate permission system |
| whether there is anything scarce, and who owns it | a market with no owner is a market nobody can host |
| each agent's desire and limits | opinion; a fern and a succulent may disagree and neither is wrong |
| **what kind of world this is** | see below — it changes the operational beliefs, and nothing else |

# What "consistent" means here

Not a feeling — four mechanical checks, in order. A world that passes all four is coherent in
the only sense the system needs.

1. **It parses, and every wire name is stated.** A device on a bus with no channel is caught by
   that transport's shapes.
2. **Derivation produces the abilities the sovereign expected.** `agora-seed` prints what it
   decided; read it. An agent that derived nothing has wiring implying no ability — almost
   always a missing `ag:senseMode`. This is the step where a misunderstanding surfaces cheaply.
3. **Every derived capability has the beliefs it needs.** `agora-validate` is capability-aware:
   a shape applies to an agent only if that agent derived the capability it belongs to. A
   subscribing agent with no interval fails here rather than at 3am.
4. **The society actually comes up.** `agora-up` starts one process per agent; each refuses to
   boot if a belief its capability requires is missing, naming the term and the graph.

Interconnection is not checked as such, and does not need to be: the graph *is* the
interconnection, and a dangling reference shows up as a capability that failed to derive or a
query that returns nothing.

# Where opening beliefs come from

Today: hand-authored per world, one `beliefs-<agent>.ttl` per agent, written during the same
session and ratified with the rest of it. Genesis seeds them; from then on they are the agent's
own to revise (aspirational — nothing revises them yet).

**But beliefs are not all the same kind of thing**, and the two shipped worlds make the split
visible. The same agent id, the same hardware, two worlds:

| | `genesis/society` | `genesis/sensing` |
|---|---|---|
| `ag:slowSleepS` | 600 | 10 |
| `ag:hasTarget` | 0.55 | *absent — it holds no stake* |

The cadence differs because the **circumstance** differs, not because the agent wants anything
different. A bench rig should be watched every ten seconds; a battery board in a garden should
not. That is a fact about the deployment.

So there are two families, and they behave differently:

- **Operational beliefs** — `ag:fastSleepS`, `ag:slowSleepS`, `ag:maxReadingAgeS`. How closely
  to watch, how stale is too stale. These track the *world's kind*: bench, staging, production.
  A sensible default could be supplied per kind, and hand-authoring near-identical numbers into
  every world is duplication waiting to drift.
- **Stake beliefs** — `ag:hasTarget`, `ag:bandLow`/`ag:bandHigh`, `ag:hasEndowment`,
  `ag:maxValuePerL`. What this agent wants and what it will pay. **Not derivable from anything**
  — "this is a test world" tells you nothing about whether a fern is parched at 0.35. These are
  the agent's own and must be elicited.

Usefully, the split falls exactly on the capability packages: the operational family is
perception's block, the stake family is the market's.

# Should beliefs be created at birth instead?

An open question, and the honest answer is *partly*. Two things argue against moving them
wholesale:

- **Birth would clobber revision.** Opening beliefs are the agent's to revise thereafter
  ([genesis](/decisions/genesis.md) §"Genesis vs sensing"). If `agora-up` wrote them, every
  restart would reset the agent to the sovereign's opinion — turning a belief into a
  configuration, which is the thing this architecture removes.
- **It would move authorship.** Only the sovereign authors the world
  ([constitution](/domain/constitution.md)). Beliefs generated by code at birth are authored by
  code, and the provenance stops meaning what it says.

What *could* move is narrower and safer: **let a world declare its kind, and let that kind
supply defaults for the operational family only**, still materialised at seed time so they are
ratified and inspectable like everything else. Stake beliefs stay elicited and hand-authored.
Nothing is generated at birth; birth stays what it is — read the world, read your beliefs, run
your modules.

# Birth

Once seeded, nothing lists the agents. `agora-up` asks the belief base `?a a ag:Agent` and
starts one process per answer, handing each the only instance identifier it will ever be given:
its own id. The roster *is* the ratified world, so a different world brings up a different
society with no edit anywhere.

Firmware is the exception and the contrast is the point: a board is hardware, flashed by hand.
What genesis decides is what an **agent** is — which is why the same board is a watcher in one
world and a bidder in another. See [world](/domain/world.md).

# Seams left open

- **World kind is not modelled.** There is no `ag:worldKind`, no defaults keyed to it, and no
  check that a bench world is not accidentally deployed with production cadences. Today the
  distinction lives only in which directory you seeded.
- **The session is not tooled.** Narrate→draft→ratify happens in a chat window; nothing
  captures the transcript, and the rationale for a number is lost the moment it lands in
  Turtle. `log.md` in the bundle would be the natural home.
- **No delta between worlds.** [genesis](/decisions/genesis.md) calls for declarative
  reconciliation — narrate the *desired* world, compute a migration. Today re-seeding replaces
  wholesale, so amending is only safe because nothing yet revises its own beliefs.
- **Nothing checks two worlds agree about shared devices,** which is exactly the property
  `society` and `sensing` rely on to let one flashed board run in either.
