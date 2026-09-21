---
type: Decision
title: An abstraction's situated instance is kept only when it is testimony
description: >-
  Three pairs have the same shape, and the sovereign's words for it are the right ones - one is a
  LONG-LIVED OBJECT and the other is SITUATIONAL DATA ABOUT IT.
  `orexis:Desire` and a judgment, `orexis:Action` and an affordance, `sosa:ObservableProperty`
  and an observation. The relation is identical and the DURABILITY is not - an observation is
  kept and the other two are never written down - because an observation is testimony and the
  other two are conclusions whose premises are stored. Three differences follow, and each is a
  mistake somebody would otherwise make: the cardinality is not 1:1, the provenance is not one
  provenance, and only one of the three is subjective.
status: accepted
timestamp: 2026-09-18T12:00:00Z
---

# Three pairs, one shape

**One is a long-lived object and the other is situational data about it.** That is the whole of
why the three feel alike, and it is worth saying before anything else, because every difference
below is a difference the feeling hides.

| the long-lived object | situational data about it | kept? |
|---|---|---|
| `orexis:Desire` — what this agent stands for | a **judgment** — how badly, right now | no |
| `orexis:Action` — a way of acting | an **affordance** — this lever, this world | no |
| `sosa:ObservableProperty` — a thing measurable | an **observation** — this subject, this instant | **yes** |

In each row the left is declared once, by a package or a world, and outlives everything around
it. The right exists because a situation arose, carries the left's IRI, and is what something
downstream actually ranges over: a deliberator ranks judgments, a planner walks affordances, a
measure reads observations. **Nobody ranges over the left**, which is the tell that the right is
not a detail of the left but the thing the system runs on.

**The instance is keyed by the abstraction plus whatever the situation individuates it by**, and
that key is different in each row — which is the first thing anyone assuming these are one shape
gets wrong.

# What differs, measured

**Cardinality.** `Agent.pursuing()` keys its dict by uri and deduplicates on purpose — *"one
want, one node… the second sighting is the same want and not a second one"* — so a judgment is
one per desire, always. An observation is one per (subject, property) and UPSERTS, which
[observation](/domain/observation.md) already states. An affordance is one per *binding*:
measured on `world/simulation`, eleven actions yielded four rows for the fern and four for the
supplier, of which `Serving` alone was three — one per valve — and nine of the eleven actions
yielded nothing at all. So a judgment ANNOTATES its abstraction, an observation RECORDS an
encounter with it, and an affordance GROUNDS it, possibly many times and usually never.

**Provenance.** A judgment is CONTRIBUTED: the ledger measures a debt by its redeem window,
sensing by the survival envelope, and the kernel supplies no formula because it could not know
what a fern needs. An affordance is DERIVED: the action's own `orexis:available` select says how,
and the kernel runs it uniformly for every action it finds. An observation is RECEIVED: it comes
from outside and nothing here computes it. Three rows, three of
[who-put-the-fact-there](/decisions/who-put-the-fact-there.md)'s own arrival kinds.

**Subjectivity.** It follows from provenance and is the sharpest of the three. Two agents holding
the same desire may judge it differently and both be right — urgency is the holder's, unit-free
so the answers can be ranked against each other without either knowing the other's formula. An
affordance is not like that: given this agent and this world, anyone running the same select gets
the same rows. A judgment is a view; an affordance is a fact about a relation.

# Why only one of them is kept

Situational data is not one kind of thing, and the split is between data that RECORDS a situation
and data that CONCLUDES something about one.

An **observation is testimony**. Something spoke, and what arrived is true of the world whatever
anybody concludes from it. It has no stored premises — it IS the premise. Nothing can falsify it;
only time can make it stale, which is why it carries `sosa:resultTime`, why freshness is a
modality of its own, and why every agent holds a freshness desire per sensor.

A **judgment and an affordance are conclusions whose premises are all stored** — regions, wiring,
the ledger, the world's facts. Writing the conclusion down lets it outlive them: unplumb the
valve and a stored row still says you can dose; the pot dries and a stored urgency still says you
are content. [affordance](/domain/step.md) makes this argument for its own half, and the
other half is the same argument.

This is not a new rule. AGENTS.md already says **anything the interpreter already knows is
computed and never asserted — "what stands, what I can do, how stale this is" — and what comes
from outside is stored**
([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).
*What I can do* is the affordance and it is listed there as computed. What this record adds is
that the rule cuts exactly along the abstraction/instance axis, which is why the three pairs look
alike and behave differently.

# What this refuses

**Treating the three as one shape**, which is not hypothetical — each difference above is a
mistake that was available while the pairs went unnamed:

- **Handing `Affordances` the choir.** `Judgments` takes the whole agent because a judgment is
  contributed and the contributors ARE the choir. `Affordances` takes a DOOR, because what it
  derives depends on the world being asked about and not on who is asked. Copying one
  constructor to the other would have coupled the menu to the modules for nothing.
- **Expecting one affordance per action.** Nine of eleven actions afford nothing, and one
  afforded three. Any reader that assumed 1:1 would have found the wrong valve, silently, since
  an empty result is not an error.
- **Storing a judgment, or recomputing an observation.** The first is the stale-urgency bug; the
  second is worse — it would mean the agent inventing testimony it never received, which is the
  one thing the belief design refuses everywhere.

**And it refuses making a fourth.** `Standing` looked like a candidate — the keeper's view of
unresolved intentions — and is not one: every field comes off stored rows through a
`FILTER NOT EXISTS`, which is a repository read and not a situated derivation. Three pairs is
what there is, and a shape claimed for a fourth that does not fit would cost more than the naming
is worth.

# Seams left open

- **Nothing gates the split.** A future capability could store a conclusion, or compute a
  testimony, and only review would catch it. Whether the arrival kinds the classification already
  carries could be held to this — a graph whose contents are conclusions may not be `Received` —
  is a question for the first time somebody gets it wrong.
- **The pattern has no name in the code.** Three pairs share a shape and no base class, contract
  or annotation says so, deliberately: a base class is an import and what these share is an
  argument rather than behaviour. If a fourth pair ever appears, that is when to ask again.
