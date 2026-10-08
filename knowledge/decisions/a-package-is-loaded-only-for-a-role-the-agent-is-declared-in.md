---
type: Decision
title: An agent's roles are declared, and a package is loaded only for a role it serves
description: >-
  The sovereign's decision of 2026-10-08, recorded before its code. Packages were loaded by a
  premise read off the world, and belief, planning and execution were forced on every agent, so a new
  package reached every running agent whose world happened to satisfy its premise. Decided - an
  agent's ROLES are declared, in its own stances document beside its self and never in the public
  world; each package declares the roles it serves in its own ontology, and a domain's roles imply
  package roles by rdfs:subClassOf, so the boot's closure loads what a domain role needs; there is no
  default set and no fixed mind, and an agent declaring no role loads nothing and is refused; what a
  premise checked moves to onboarding, both ways - a declared role whose needs the world lacks, and a
  sensor no declared role reads. Transports and watchers are not roles. A role is internal; what a
  peer needs to address an agent is a public relation the world states, and the courier lacks one.
  Hanoi becomes planning only, which needs an ending of its own. Refused - premise-derived loading, a
  fixed mind, default roles, roles in the public world, asking a peer for its roles, and package roles
  with no domain roles. Supersedes in part a-documents-kind-says-who-reads-it,
  a-layer-is-a-package-and-need-loads-it and capability-packages.
status: accepted
timestamp: 2026-10-08T12:00:00Z
---

> **Recorded before the code.** Nothing below is built. Where this record says how the tree IS, it
> was read on `e99731d0` (2026-10-08) and the measurements were run in memory there; where it says
> how the tree WILL be, the issues at the end carry it. The pages that describe loading today —
> [package](/domain/kernel/package.md), [agent](/domain/kernel/agent.md),
> [runtime](/domain/kernel/runtime.md) — stay true of the code until those issues land, and are
> rewritten with it.

# The question

What an agent runs was not anybody's choice. `PREMISES` in `agent/runtime.py` holds one ASK per
package beyond the mind, read off the world's public graphs with the agent bound, and `MIND` —
belief, planning and execution — is loaded for every agent whatever its world
([a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md), #824). So a
package added to `agent/` reaches every running agent whose world happens to satisfy its premise,
at its next boot, with nobody having asked for it; and an agent that should do less than the mind
cannot. The sovereign's case: "Hanoi agent could simply be only planning."

# What the tree holds today, verified

Read on `e99731d0`; each measurement was an in-memory boot, nothing started, nothing written.

- **The mind is a constant, the rest a premise.** `MIND = ("belief", "planning", "execution")`;
  `packages_of` answers `MIND` plus each package whose ASK holds, in `PREMISES`' order. Hanoi's mover
  loads exactly `('belief', 'planning', 'execution')` — measured, and pinned by
  `test_the_mover_loads_the_mind_and_nothing_else`.
- **Planning already tolerates no executor.** `_Planning.link` in `agent/planning/create.py` returns
  at once where `parts.get("execution")` is `None`; nothing else in the runtime indexes
  `parts["execution"]` outside tests.
- **Planning alone plans Hanoi, and then never ends.** Booted with `MIND` narrowed to planning
  alone, Hanoi's mover published one plan of seven steps on its first pass at a budget of 64 —
  execution's ontology document NOT in its store — and then held the agent: forty passes, every one
  `unfinished`, one want standing, one want walking. The cause is `_WALKING_Q` in
  `agent/planning/planner.py`: a plan published and adopted by no intention is counted as WALKED,
  which is right where an executor will adopt it at the next drain and wrong where none exists. So
  the expectation that such an agent "would read `unreachable` with a plan in hand" is not what the
  code does: `_keep` never reaches the unreachable branch, because something is walking. It reads
  neither `met` nor `unreachable`; it does not stop.
- **Planning speaks execution's words, and imports them.** `extract_plan` writes `execution:Step`,
  `execution:then`, `execution:adds` and the two prediction graphs' kinds; `publish_plan` and `take`
  import `agent.execution.ontology`. A planner-only agent therefore imports execution's term
  constants as a package beneath it — and creates no execution part and reads none of its documents.
- **Hanoi ships no rules.** Its store holds no `sh:RulesGraph` (measured); the `sh:rule` blocks in
  `domains/hanoi/` are effects, planning's to run. Belief's part revises Hanoi's state at start and
  concludes nothing. `agent/belief/tests/test_events.py` still uses Hanoi as its world.
- **Speech has no vocabulary document.** `agent/speech/` holds Python only; a role it serves needs an
  ontology it does not have.
- **The market states relations, not roles.** `market:hosts` and `market:bidsIn` (agent to venue)
  and `market:bidder` (bid to agent) exist; no `market:Host` or `market:Bidder` class does, and
  [host](/domain/market/host.md) is bound to the relation `market:hosts`. The market ships a rules
  graph, `domains/market/rules.ttl`, as the tower and sensing do.
- **Nothing says which agent controls a driver.** In `world/driver/` the `:dispatcher` "acts for
  nothing" and `:driver` is linked to no agent; `courier:Drive`'s and `courier:Board`'s preconditions
  name no agent. In a two-agent world starting from one set of documents, as #922 poses it, each
  agent's search admits drives of the peer's van whenever the peer's driver is aboard it — #922's
  "the other van admits no Drive in this agent's search" holds only once a fact says whose the driver is.
- **An agent's own documents are read once.** `boot` puts the agent's own graphs in only where the
  volume is fresh; a volume lived in keeps them as they are. #876's stances document is to be loaded
  the same way.
- **#876 says the opposite of this record** about packages: "Which packages an agent has is NOT one
  of these: that is derived from the world by each package's premise (#824) and stays so." This
  decision reverses that sentence.

# The decision

## 1. Roles are declared, and a package loads only for a role it serves

An agent's **roles** say what it runs and may do. A package is loaded — its documents put in the
store, its part created — only for a role the agent is declared in, or a role beneath one by the
closure. It is opt-in per agent: a package added to the tree reaches no agent until a role it serves
is declared for that agent.

A package beneath a loaded one may still be IMPORTED for its words, as planning imports execution's
term constants; that is the layering's downward import, not loading, and creates no part.

## 2. No default set and no fixed mind

`MIND` and `PREMISES` go. An agent declaring no role loads nothing, and `orexis-onboard` refuses it.
A default would be a kind said by absence — two readers disagreeing about an agent that said
nothing — and a role every agent has is not a role, since OntoClean's test for a role is that its
holders can cease to hold it.

## 3. Each package declares its roles; a domain's roles imply them

**A package declares the roles it serves in its own `ontology.ttl`**, under its own prefix, as one
claim one owner wants. **A domain declares roles in its own words, beneath package roles by
`rdfs:subClassOf`**, and the boot's materialised closure then loads every package behind a domain
role: an author declares `:supplier a market:Host` and never lists the packages a host needs. A
package role may sit beneath the role of a package below it — an observer's sides are revisions, so
sensing's role is beneath belief's — which is how a package's own need is said without the runtime
knowing it. An author may declare a package role directly where no domain has a word for what the
agent is: Hanoi's mover.

**Which package serves a role is read off the package's own ontology, without putting an unloaded
package's documents into the agent's store.** The boot reads the declarations before it decides
what to load, so it reads them apart — Hanoi's store holding no sensing ontology is the #824
measurement this must keep. The package is the directory the declaration was read from, which is
what rule 2 says a package is.

**The words.** The owners are decided; the spellings are the implementing change's, under one
constraint this record found: a role's word may not be one a page already owns for another concept.
"Planner" and "Executor", the examples the decision was given in, title the Service pages for the
Python objects ([planner](/domain/planning/planner.md), [executor](/domain/execution/executor.md)), and a
class of AGENTS under the same word is one word for two concepts — the reader of "the planner checks
the head" could not tell which. Proposed, for the sovereign to confirm before anything declares them:

| owner | role | an agent in it | needs, as a shape over the world |
|---|---|---|---|
| kernel | `orexis:Role` | the kind every role is beneath; its page says what a role is | — |
| belief | `belief:Reviser` | revises what it believes by the rules it holds | nothing |
| sensing | `sensing:Observer`, beneath the reviser | turns its sensors' numbers into observations | a sensor reporting to it, as sensing's premise reads one |
| prediction | `prediction:Predictor` | foresees its readings by the drifts | a sensor of its, and a drift |
| planning | `planning:Decider` | derives wants and searches for plans | a desire or a want it holds |
| execution | `execution:Actor` | walks intentions and takes steps | being a decider too, while a plan crosses no agent (seam below) |
| speech | `speech:Speaker`, in a vocabulary speech does not yet have | hears peers' documents and says its own | a topic it listens to |
| market | `market:Host`, beneath decider, actor, speaker and reviser | holds a venue and serves it | `market:hosts` a venue |
| market | `market:Bidder`, beneath the same four | bids in a venue | `market:bidsIn` a venue |

Decider and actor are the split the seam below is about — one agent deciding, another acting —
and "act" is already execution's word for a step taken. Each new word gets its page under
`knowledge/domain/<package>/` in the change that declares it; [host](/domain/market/host.md) is rebound
from the relation to the role, which is founded on it.

## 4. A role is internal; what a peer needs is a public relation

**Roles are the agent's own knowledge.** They are stated in the agent's own stances document — the
kernel graph kind #876 introduces for the agent's stances, beside its `orexis:Self` — authored by
the sovereign under `world/<name>/` for that agent and mounted into that agent's container alone.
Not in the public world graph: a peer does not learn another agent's roles, as #923 refuses a van
learning that its peer controls a water supply. The stances kind must be the kernel's, as the
society's is, because the boot reads the roles before any package is loaded.

**The line between a role and a public relation is who must read it.** A role says what THIS agent
runs and may do, and nothing outside the agent reads it. A relation a peer needs in order to
address the agent is public and the world states it: `market:hosts` is public because a bidder
must find the host of a venue to call it. That is the test of
[model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)
asked of a peer: a peer's plan branches on whom to call, never on what the callee runs.

A role over something keeps its relation — the host role is founded on `market:hosts`, and its
shape asks for the relation — so the two agree where both exist, and onboarding holds them to it.

**The courier has no such relation, and two minds need one** (#568, #922, #923,
[two-minds-meet-by-saying-their-routes-and-drawing-lots-on-a-conflict](/decisions/two-minds-meet-by-saying-their-routes-and-drawing-lots-on-a-conflict.md)).
A van sensed in range must lead to the agent to ask, and an agent's search must admit drives of
its own van alone. **Proposed, for the sovereign to confirm: `courier:hasDriver`, agent to driver,
public, as `actuation:hasActuator` is agent to actuator** — the driver an agent may take a step
through. Agent to driver rather than to van, because a driver boards another van and the agent's
reach goes with the driver. `courier:Drive` and `courier:Board` then admit only a driver the
agent has, and a peer is found as the agent that has the driver of the van in range.

## 5. What a premise checked moves to onboarding, both ways

Each role states what it needs as a shape (the table above). `orexis-onboard` refuses **a declared
role whose needs the world lacks** — an observer no sensor reports to, a host holding no venue —
and **the converse: what would arrive for an agent and be read by none of its roles**, as it
already refuses a graph no reader declares. The converse, read here from the sovereign's example:

- **a sensor reporting to an agent that is no observer** — the sovereign's case;
- **a topic an agent listens to, and no speaker**;
- **a document of a kind none of the agent's loaded packages declares**, per agent — the existing
  refusal, narrowed from "no reader at all" to "no reader this agent loads", which is how a rules
  graph held by an agent that is no reviser is caught.

**Not refused**, and why: a drift with no predictor — foresight an author may decline, so refusing
it would make the declaration the derivation restated; and an action with an `execution:Saying`
that an agent is in no role to take — whether an action admits this agent is the search's to say,
and onboarding does not search.

The shapes are requirement shapes in #838's sense, and #838's open question — whether a shape the
agent's vocabulary knows loads into every agent — is theirs as much as its own.

## 6. Transports and watchers are not roles

A transport is loaded where a loaded role needs bytes and the society wires a bus: the MQTT member
where an observer's sensor publishes on a topic or a speaker listens to one, the HTTP member where
an observer's sensor is a thing with a form. That is the transports' two rows of `PREMISES`,
re-asked over the loaded roles — the one derivation left, since which bus reaches a device is
wiring and not a choice. History and metrics stay deployment facts, read from the environment.

## 7. Hanoi becomes planning only

Its mover is declared a decider and nothing else. Measured above, that already plans; what follows
is what it costs:

- **The plan is the output.** A published plan is nobody's to adopt, so Hanoi's tests are held to
  the plan — seven steps in the textbook order, at the cost the estimate admits — rather than to a
  solved tower. The cases that use Hanoi to exercise execution, belief and the metrics of a walked
  plan move to a world with an actor, the courier's.
- **An agent with no actor needs an ending of its own, `planned`**: planning lets go when every want
  standing has a plan published and no part will walk it. Without it the agent never stops, because
  a published plan counts as walked (measured above).
- **No reviser is needed**: Hanoi ships no rules, and the planner-only run planned without belief.

# Why

**The premise derivation's own argument, engaged.** It refused "the agent's own file declaring its
packages" on two grounds: one source of truth rather than two, and nothing loaded that no fact asked
for. Both hold where the world's facts imply what an agent should run. They fail where the role is an
**assignment no fact implies**:

- a planner-only agent, whose world is the same whether it acts or not;
- two agents that could both command one pump, of which one may;
- a hot standby, whose facts are its partner's;
- several holders of a good, of which one sells — and `market:hosts` is already a declaration in
  relation form, written by the sovereign because no other fact could say it.

In each, a premise either loads what nobody asked for or cannot be written. **The one-source property
survives**: the declaration is the one source of what an agent runs, and the disagreement the old
record feared — a sensor with no package to read it, a package for a sensor since removed — becomes
an onboarding refusal in each direction instead of a silent load.

**Its second refusal — a premise stated in the package's own document — does not apply to a role.**
That failed on speech, whose premise was in execution's words and the transport's, which speech may
not speak; and on the import, which the runtime would have had to map from a document. A role is in
the package's OWN words, and a caller's need is said by the caller's role sitting beneath it — the
market's host beneath the speaker — so no package speaks above itself. The runtime maps a role to the
directory whose ontology declared it, which is a package by rule 2 and no instance.

**0.1.0's refusal of `market:Host`, engaged.** [a-role-needs-something-to-be-a-role-in](/decisions/0.1.0/a-role-needs-something-to-be-a-role-in.md)
kept market positions as predicates: a role nothing could vary independently of its predicate is a
synonym. Its premise was that every capability was derived from a position. That premise is what
falls here: a role now varies independently of every predicate — a decider holds no relation at all
— and loads code, which no predicate does. For the host the old point still bites: the role and
`market:hosts` coincide in every shipped world. They are kept as two facts because they have two
readers, the agent and its peers, and onboarding refuses them apart. The auction-object question
that record tied roles to is untouched: these roles are about what an agent runs, not about a
position in one auction.

**And it restores a claim the tree had broken.** [capability-packages](/decisions/capability-packages.md)
says a package is found by looking and never listed; `MIND` and `PREMISES` are a list, and a package
directory in neither is read by no agent. Roles declared in each package's ontology are found by
looking again.

# Where it sits in the literature

From memory; the years are approximate.

- **Roles apart from agents.** Agent/Group/Role (Ferber and Gutknecht, ~1998): an agent plays roles
  in groups, and the organisation is described by roles, never by the agents filling them. Gaia
  (Wooldridge, Jennings and Kinny, ~2000): a role is responsibilities and **permissions** — what the
  agent may use and do — which is the half of a role here that loads code. MOISE+ (Hübner, Sichman and
  Boissier, ~2002): roles specialise one another, and a sub-role inherits its super-role's links —
  the shape of a domain role beneath package roles.
- **What a role is.** OntoClean (Guarino and Welty, ~2002): a role is anti-rigid — its holder can stop
  holding it — and an anti-rigid class may sit beneath a rigid one but never above it, so a role
  beneath `orexis:Agent` is sound and a default role every agent has is not a role. Masolo et al.
  (~2004): a social role is founded on a relation and defined by it, which is why a role over
  something keeps its relation, and why the host role's shape asks for `market:hosts`.
- **What this refuses.** FIPA's directory facilitator (~2002): agents register what they offer with an
  overseer that peers query. Nobody here oversees, a peer asks no one for another's roles, and what
  a peer needs is a relation the world states.

# What was refused

- **Premise-derived loading** — it cannot write an assignment no fact implies, and it reaches every
  running agent whose world satisfies a new premise without anyone asking.
- **A fixed mind every agent has** — Hanoi's mover is the counterexample; the ruling that the
  container builds the mind for everyone is what this supersedes.
- **Default roles** — a kind said by absence, and not a role by OntoClean's test.
- **Roles in the public world graph** — need-to-know; a peer that learns what an agent runs learns
  what it can do, which #923 refuses for routes on the same ground.
- **Asking a peer for its roles** — a peer's word about its own role is testimony, believed as a
  document and checked by nothing; what a peer needs is a public relation the world states, and asking
  belongs to an open society, which the [roadmap](/decisions/roadmap.md) parks.
- **A role per package with no domain roles** — the author would list a host's packages by hand in
  every world; a domain role beneath package roles is what lets an author declare in the domain's
  words, and the closure the boot already materialises does the rest.

# Seams left open

- **A plan crossing agents.** A dispatcher decides and each van's agent only acts. Rule 4 means the
  plan crosses by speech, and #916's take-time check — the executor's `taking` answered by
  `Planner.check` in one store — becomes a question back to the deciding agent. Until then an actor
  needs to be a decider. **The trigger: the first world in which one agent decides for steps another
  agent takes** — a dispatcher whose vans are other agents', which `world/dispatcher/` is not: its one
  agent decides and acts.
- **A role declared after birth.** The stances document is the agent's own, and a volume lived in
  keeps the agent's own graphs as they were; so a role added or removed for a running agent reaches it
  only on a fresh volume, as every stance does under #876. A role is anti-rigid, and changing one
  without a rebirth — the hot standby taking over — is an amendment the tree has no mechanism for
  ([an-amendment-endows-what-it-grants](/decisions/an-amendment-endows-what-it-grants.md)). **The trigger:
  the first role change the sovereign wants on a running agent.**
- **A role loads; it does not narrow.** Of two agents that could command one pump, the role says which
  runs an actor; which actions an actor may take is still its actions' preconditions over public
  relations (`actuation:hasActuator`). A role that narrows its holder's actions — Gaia's permissions
  taken all the way — is not decided. **The trigger: two agents in one world whose actions both admit
  a step only one of them may take, with no relation to tell them apart.**
- **A peer's roles stay unknown**, deliberately; what is public is the relations.

# What it supersedes and amends

- [a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md), superseded in
  part: §2 and its #824 amendment — packages derived by premise, the mind always loaded, the refusal of
  the agent's own file declaring its packages. The rest stands, and its per-reader refusal is narrowed
  per agent here.
- [a-layer-is-a-package-and-need-loads-it](/decisions/a-layer-is-a-package-and-need-loads-it.md),
  superseded in part: "the container builds the mind for every agent" and the roster derived from
  grants. Need still pulls — a domain role pulls the package roles beneath it.
- [capability-packages](/decisions/capability-packages.md), superseded in part: its premise that what an
  agent runs is derived and not declared. Its claim that a package is found by looking stands, and is
  restored.
- #876's sentence keeping packages derived; the roles live in its stances document.
- Reversed, and rewritten with the code rather than now: [agent](/domain/kernel/agent.md)'s "nothing is
  granted", [package](/domain/kernel/package.md)'s *How a package is loaded*, and the line in `AGENTS.md`
  that a package beyond the mind is loaded where its premise holds.

# Verified, and assumed

Verified on `e99731d0`, in memory: the packages Hanoi's mover loads; that its store holds no rules
graph; that with planning alone it publishes one plan of seven steps on its first pass, with
execution's ontology document absent, and is still `unfinished` after forty passes with one want
walking; the walking query that causes it; planning's `link` with no executor; planning's imports of
execution's term module; speech holding no vocabulary document; the market's relations and the absence
of role classes; the courier's preconditions naming no agent; a lived-in volume not re-reading the
agent's own documents; #876's sentence.

Assumed: the proposed words and the courier relation, until the sovereign confirms them; the converse
list in §5 beyond the sensor, which is this record's reading of the decision; that every shipped world's
agents can be declared in the roles above without a word this record has not named — the implementing
issue settles that agent by agent; and the literature, cited from memory.

# Issues it files

- Declare roles per package and per domain, load packages by the agent's declared roles, remove
  `PREMISES` and `MIND`, and check roles both ways at onboarding.
- Make Hanoi's mover planning only, with an ending of its own.
- State which agent has the courier's driver, so two minds can find whom to ask.
