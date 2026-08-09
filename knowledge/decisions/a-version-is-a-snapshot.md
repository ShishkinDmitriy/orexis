---
type: Decision
title: A version is a snapshot, and the delta is derived
description: World versions become a real append-only chain — snapshots store, deltas derive, retraction needs no vocabulary, and a content hash catches an edit that forgot to ratify.
status: accepted
stage: v1
tags: [world, versions, provenance, genesis, ratification]
timestamp: 2026-08-09T00:00:00Z
---

# Context

`ag:WorldVersion` has been documented as *"one ratified version of the world's topology; the
chain is append-only"* since the vocabulary was written. There was no chain.

Every world declared exactly one node — `ag:version_1` — with no predecessor, no author and no
timestamp. **Nothing anywhere wrote a version.** It was read in four places (`world.py`,
`sensed_writer`, `observation`, `metrics`) and produced in none, so amending a world meant
editing a file and bumping an integer by hand, and forgetting was invisible.

Which made one shipped feature structurally dead. `metrics.py` reports `world_version` with this
rationale: *"Which world an agent is actually running, as opposed to which one is on disk. A
world can be re-ratified while agents keep running the version they booted with, and nothing
else at runtime would show the difference."* It exists to catch exactly that drift, and could
not, because the number never changed.

There is also an inversion worth naming, because it is what made this obviously wrong rather
than merely incomplete: **an agent's belief history was better modelled than the world's.**
[a-belief-is-a-pick-within-a-range](a-belief-is-a-pick-within-a-range.md) records every revision
an agent makes with a from-value, a to-value, the evidence, a timestamp and who chose. The world
recorded `1`. The thing a sovereign authors had weaker provenance than the thing an agent decides
on its own.

# Decision

## Snapshots store; deltas derive

A version is the world **as it stood, entire**. Amending it produces a new complete snapshot, and
the bodies live in git.

The consequence that decides everything else: **retraction needs no vocabulary.** A device that
moved is simply *absent* from the later snapshot. There is no `ag:retracts`, no statement that
some other statement no longer holds, and therefore no reification and no RDF-star — which were
the only ways to say such a thing, and both were rejected for provenance
([who-put-the-fact-there](who-put-the-fact-there.md)) for the same reason: they make every query
worse in order to express something that can be computed instead.

And *"who introduced this triple"* survives as **the earliest version containing it** — a
computation over snapshots rather than a fact anyone states. So the intuition that a world is
"additions on top, by different authors" is preserved exactly. It is the **view**, not the
storage.

## The head is derived, never declared

`ag:currentVersion` is computed by `vocabulary/agora/rules.ru` as the version nothing else
revises, and lands in the derived graph beside `ag:hasCapability`.

This is what lets `versions.ttl` be append-only in the *literal* sense: ratifying only ever adds
a node. A file that had to be edited to record which of its own entries was current would be a
pointer with history attached, not a chain — and `git log versions.ttl` would stop being the
record of who ratified what.

It is structural rather than numeric on purpose. `MAX(?versionNumber)` would trust the integer an
author typed; `prov:wasRevisionOf` is what actually builds the chain. The number is for ordering
and for the author's claim that this is a new version, and when the two disagree the link is
right and the number is a typo.

## Stated integer, computed hash

The failure mode here is not the model, it is **discipline** — someone edits a world and forgets
to ratify. So the author states the version and `ag:contentHash` is computed at ratification and
re-checked by `agora-validate`, which refuses and names the command that fixes it.

**Over raw bytes, including each file's name.** A canonical serialisation of the parsed graph
would be meaning-stable, and that is the wrong stability: it answers *does this still mean the
same*, where a ratification gate asks *is what is on disk what was ratified*. Under the canonical
form, a world could be reformatted and every comment rewritten while still claiming to be a
version it is no longer — and comments are part of what a sovereign authored, because a world is
reviewed by being read. Raw bytes is also the simpler thing to be sure of: canonicalising a graph
containing blank nodes, and `prov:qualifiedAttribution [ … ]` is one, needs RDFC-1.0.

## Ratification becomes a command

A hash cannot be hand-written, so `agora-ratify <world>` is what mints a version: bump, compute
and record the hash, link `prov:wasRevisionOf`, attribute with `prov:qualifiedAttribution`
(agent and role — the shape from [who-put-the-fact-there](who-put-the-fact-there.md)), timestamp.

It refuses to mint when nothing changed. Otherwise the chain would record when someone ran a
command rather than when the world changed, and every reader comparing two versions would start
seeing differences that mean nothing.

It lives in `onboarding/` for the reason `create_keypair` does: **an agent that could version its
own world could rewrite the terms it is held to.** `agent/` reads a version and never authors one.

# Two file-layout consequences

**`versions.ttl` is separate because a hash cannot cover the document that states it.** Writing
the fingerprint would change what the fingerprint describes. So `world.ttl` holds pure content
and states no version at all, and the attribution moved with it — onto the *version*, which is
where it belonged, because ratifying is an act and acts are what have authors. A world attributed
once, for ever, could not say that alice ratified v2 of what dimonina began.

**`versions.ttl` IS mounted for agents**, unlike `hardware.ttl`. The distinction is not symmetry:
hardware is withheld because an agent must never learn which pin a probe is on, and the absence
*is* the enforcement. A version chain is neither secret nor large, and an agent must cite the
version in force on every observation it records — withholding it would withhold something it is
required to state.

# Consequences

- `world_version` in the metrics can finally differ, which is the only reason it was ever added.
- The claim in the vocabulary is now a mechanism rather than an aspiration.
- `agora-validate` gained a check that runs *before* the shapes, because it asks a prior
  question: are these files even the ones this world claims to be? A world can satisfy every
  shape while being something other than what it says it is, and no shape can see that.

# Seams left open

- **Past bodies are not in the store.** Git holds them, which is the line
  [two-store-beliefs](two-store-beliefs.md) already draws between citable current-state and bulk
  history. Recovering what v2 actually said means leaving the graph.
- **Deltas and per-triple attribution are derivable and not derived.** Nothing computes *"who
  introduced this triple"* yet, because nothing needs it.
- **A ratification is testimony, not proof.** The chain says who ratified, and anyone who can
  edit `versions.ttl` can edit that claim — the same ceiling
  [who-put-the-fact-there](who-put-the-fact-there.md) records. `agora-keygen <world> sovereign`
  already works; signing the hash is what would make a version verifiable rather than merely
  recorded, and it is the natural next pass.
- **Nothing garbage-collects the chain.** A world ratified daily for a year carries 365 nodes.
  They are four triples each, so this is not urgent, but there is no story for pruning.
