---
type: Domain Concept
title: Reading
term: http://www.w3.org/ns/sosa/hasSimpleResult
description: >-
  The VALUE an observation carries, and the only thing in an agent's belief base that is somebody
  else's word — `orexis:Received`, the one arrival whose trustworthiness is a question at all. It is
  the thing a plan moves: every shipped effect predicts one, and a possible world differs from
  the real one by exactly this. It ages rather than expires, and how long it stays actionable is
  the agent's own judgement rather than a property of the number — so "stale" is a verdict a
  reader reaches, never a flag anybody sets. Absent is not zero: a property never read yields no
  gap rather than a satisfied one.
---

# What it is

A **reading** is the value — the moisture fraction, the temperature, the litres in the butt. It
lives inside an [observation](/domain/observation.md), which is the node that records it, and the
two words are not interchangeable: a node holds one reading, and a node holding *two* is the
signature of a bug.

# It is somebody else's word

Every other kind of fact in a belief base is the agent's own or the sovereign's. A reading is an
**instrument's**, and the graph says so: its arrival is `orexis:Received`, which is *the only arrival
whose trustworthiness is a question* — an assertion is the sovereign's by definition and a
derivation is checkable arithmetic, but this either carries a signature or does not.

That is why readings sit in a graph of their own rather than among beliefs, and why the plant
asserting its own reading was a decision someone had to take rather than an obvious default.

# It is the thing a plan moves

Every [effect](/domain/effect.md) this project ships predicts a reading, and nothing else. A dose
raises one; a delivery raises one; looking produces one with the same value and a fresher instant.
So a possible world differs from the real one **by exactly this** — which is what makes a plan
representable as a small diff rather than a whole state, and what makes one mutable graph enough
for a search to run against.

# It ages; it does not expire

A reading does not become false at a moment. It becomes **less worth acting on**, and how much
less is the agent's own judgement — a fast-drying pot outruns its reading sooner than a slow one.

So **"stale" is a verdict a reader reaches, never a flag anybody sets.** Nothing sweeps the sensed
graph marking readings dead; a consumer compares the instant against what it believes about the
instrument that produced it. Which is also why the freshness rule belongs to the agent and not to
the board: see [sensing](/domain/sensing.md), which owns the clock.

# Absent is not zero, and it is not satisfied

A property nobody has read yet has no reading, and every part of the design treats that as
**maximal ignorance rather than a neutral value**: `urgency(None)` is 1.0, a [gap](/domain/gap.md)
yields no row rather than a zero, and the first intention an agent adopts is always to look.

The tempting alternative — a default, a zero, a last-known-good — is what makes a system water a
plant it has never measured.

# What it is not

**Not a judgement.** The value and the verdict about it travel together on the wire, but only the
value is a reading; which side of a region it sits on is the agent's reading OF the reading, and
it is recomputed by whoever needs it rather than trusted from the sender.

**Not history.** The sensed graph holds the current one per (subject, property) and nothing else.
What happened before is in the series store, which is a different question asked a different way.

# Related

- [observation](/domain/observation.md) — the node that carries it, and the two questions it
  answers that the number cannot.
- [gap](/domain/gap.md) — what the absence of one means, and what its distance from a region is
  worth.
- [belief-base](/domain/belief-base.md) — why it lives in a graph of its own.

# Its identity when compared

When a present is matched to a kept world, or a step states what it read, a reading is
stated by its [band](/domain/band.md) — the class the domain asserted on it — and not by its
number; two readings the domain calls the same are one fact (#576).
