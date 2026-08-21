---
type: Decision
title: A volume can be older than the vocabulary, and nothing could see it
description: >-
  Beliefs are authored once and never touched again, so a belief base outlives the code that
  wrote it — and PR #85 moved 102 terms out of ag: while both gates stayed green. Boot now
  asks whether the vocabulary still declares what the store actually uses, which needs no
  version marker because the store already holds the evidence. Migration rewrites how a value
  is spelled and never which value it is, and it is a flag rather than a side effect.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

[a-package-owns-its-namespace](a-package-owns-its-namespace.md) and the sweep that followed it
moved 102 terms out of `ag:` into their packages' namespaces. Every gate was green: 764 tests,
three worlds conforming, grants byte-identical, compose and firmware unchanged.

**It would have silenced every deployed agent on its next restart.**

`agent/genesis.py` writes an agent's beliefs once and never again, and
[where-the-belief-base-lives](where-the-belief-base-lives.md) made that deliberate — *"write an
agent's beliefs only if it has none, and require an explicit act to reset an agent that already
exists."* That is what makes a belief the agent's rather than the sovereign's. It also means a
volume can be **older than the vocabulary**: one written before the sweep holds `ag:hasTarget`
where the code now asks `water:hasTarget`. The pattern matches nothing, the agent starts
cleanly, and it bids on a desire it cannot see.

## Why nothing caught it

**Every test builds a fresh store from the current files.** `genesis_store()` starts empty and
authors from whatever the vocabulary says today, so no test has ever met a volume older than the
code it is running. `agora-validate` reads the world files, which the sweep itself rewrote and
which are therefore internally consistent.

Neither gate can see persisted state, and persisted state is the whole design: this project's
isolation is that each agent holds its own store in a volume of its own. So the one thing that
survives a deployment is the one thing nothing reads.

That is the same shape as the four silent breakages the sweep did find — an IRI no ontology
declares is not an error in SPARQL, it is a pattern that matches nothing — one step further out.
Here the mismatch is not between two files in the repository but between the repository and a
disk somewhere.

# Decision — ask the store, do not stamp it

At the end of `open_belief_base`, after everything that writes has run, boot asks: **does this
vocabulary still declare what this store actually uses?** If not, it refuses, naming each term
and what it became.

## Why there is no version marker

The obvious design is to stamp a store with a vocabulary version and compare. It is not what
this does, for two reasons.

**A version is a fact somebody must remember to bump**, and everywhere else this project derives
rather than declares. One that goes un-bumped is worse than none, because it asserts an agreement
nothing ever checked — the same objection
[self-review-is-a-capability](self-review-is-a-capability.md) raised against an optional interval
that meant *never review*: a side channel dressed as a decision.

**And it answers the wrong question.** A version says the vocabulary moved. It cannot say whether
*this* volume is affected, and most would not be: a store using no moved term is perfectly sound,
and refusing it would be a confident lie. The question that matters is about this store, and the
store already holds the evidence — so nothing has to be recorded to answer it.

## What counts as stale, and why the positions differ

A **predicate** is always a term, so a project predicate the T-Box does not declare is wrong
however it got there — a rename, a deletion, or a typo in a hand-written beliefs file.

Anywhere else a project IRI may be an instance: `ag:fern_agent` has exactly the shape of a term
and is not one — and since the worlds moved their individuals into namespaces of their own, an
`ag:`-spelled individual in a volume is itself a sign of age: a volume born before the move
holds `ag:fern_agent` where the world now says `:fern_agent`, and such an agent refuses to
start rather than half-believe. Rebirth is the remedy, exactly as this record prescribes. Those positions are flagged only where the rename map recognises them, which is
where the answer is known rather than guessed. `review:revisedTerm ag:slowSleepS` is caught that
way — the object is a term, and the map says what it became.

## The map is derived from the vocabulary, not from the store

For every term now living in a package, the kernel spelling of its local name can only be the
old one — provided no kernel term of that name survives. So the map is complete before anything
is scanned, and a term used *only* in object position is still covered.

**A local name two packages both declare is contested, not settled.** Refusing outright was the
first attempt and it was wrong twice over: `i2c:DataPinRole` and `onewire:DataPinRole` are both
real and both correct — a data pin means something different on each protocol — and *neither was
ever a kernel term*, so no volume can hold the old spelling. Raising at load would have stopped
every agent from booting over a collision that cannot be reached. It is reported only if a store
actually uses one, which is the difference between a hazard and a fact about the vocabulary.

That distinction only surfaced by running the thing against the shipped worlds before wiring it
into boot. It would not have appeared in any test written from the design.

# Migration, and why it is not `rebirth`

`rebirth` already exists and would clear this: it returns an agent to what the sovereign
authored. It is the wrong remedy, because it throws away everything the agent revised for itself
— and for an agent with `review:commits` latitude that history is the point of having a belief
base at all. A rename should not cost an agent its second thoughts.

So migration rewrites **how a value is spelled and never which value it is.** `0.55` was this
agent's, and it stays `0.55`.

It is a flag — `AGORA_MIGRATE_BELIEFS=1` — and not a side effect, for exactly the reason
`rebirth` is a flag: *"doing it by accident is the bug this separation prevents."* A persistent
store rewritten by the mere act of starting is a thing nobody asked for.

Two refusals inside the migration are deliberate. A term with **no successor** stops the whole
migration rather than being dropped, because deletion is not renaming and guessing at it loses a
value silently. And a store still stale **after** rewriting is a refusal too: a rewrite that did
not take is worse than one that never ran.

**Public graphs are never migrated.** `refresh_public` replaces them from the ratified files on
every start, so they are current by construction — a stale term in one would mean the files
themselves are wrong, and rewriting it here would hide that.

# Consequences

- **The test that would have caught #85 exists.** `tests/test_vocabulary.py` authors a belief
  base the way the code wrote them before the sweep, then opens it with the code that came
  after. It is the only shape of test that can see this class of failure, and there was none.
- **`test_vocabulary.py` joins `test_store.py` as exempt** from the moved-term guard, by name and
  with a reason each. It *is* the old spellings; a fixture generated from the current vocabulary
  would move whenever the vocabulary did and stop being the old world.
- **Boot gained a way to refuse.** It is the third thing that can stop an agent starting, after a
  missing world and failed validation, and it is the same answer this project already reached for
  a world moving under a running agent: *"an agent acting under a world it no longer knows is the
  thing to prevent; being briefly absent is not."*

# Seams left open

- **Only the kernel-to-package direction is mapped.** A term moving between two packages, or a
  package renaming its own term, produces an undeclared predicate that is correctly refused and
  has no computed successor. That is safe and unhelpful, and nothing needs it yet.
- **Nothing warns before the rebuild.** The refusal happens on the restart, which is the last
  possible moment — an operator learns their volume is behind when the agent declines to start.
  A check that could be run against a volume *before* rebuilding would be better and does not
  exist.
- **`:sensed` and the review graphs are covered by the same scan and have never been tested
  against a real migration.** They are private and persistent, so they are in scope by
  construction; no volume has yet held a stale term in one.
- **The gates still cannot see a volume.** This adds a check at boot, not a gate. Nothing in
  `pytest tests` or `agora-validate` reads persisted state, and the next fact that lives only in
  a volume will be just as invisible as this one was.
