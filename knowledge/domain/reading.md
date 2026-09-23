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
  gap rather than a satisfied one. In Agent 0.2.0 a reading STANDS as the present for the horizon
  sensing gives it and then does not, by the clock, and the number is kept beside the bands.
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

So **"stale" is the agent's own verdict, and since #598 it is one it WRITES rather than one every
reader recomputes.** The rule is unchanged and still the agent's — how long a reading of this
instrument is evidence is `sensing:staleAfterS`, its own judgement, not the board's, and see
[sensing](/domain/sensing.md), which owns the clock. What changed is where the answer lives:
sensing arms a deadline when the reading arrives, and when it lands the reading carries
`sensing:staleSince`. A reader asks for the fact.

**Because the alternative was arithmetic in a search.** The freshness measure and the want
derived from it both computed *this instant plus that horizon against now* — inside a planning
pass, where `NOW()` is the real clock and never the instant the act being weighed would be taken
at, so the answer was about a world nobody is in. A rule reading a triple asks no clock in a
possible world or a real one. It is the same move a reading's VALUE made when it became a
[band](/domain/band.md): deliberation compares triples and interprets no literal, and a datetime
is a literal.

Two things follow, and both are properties of the sensed graph rather than of the fact. **A
fresh reading takes the mark with it**: the graph holds one node per subject and property and
upserts it, so the reading that replaced a cold one carries no `staleSince` and needs no
sweeping. And **a possible world inherits both** — which is what makes a look worth taking in
one: the reading it predicts is evidence by construction, and the one it replaced is not there
to be asked about.

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

# In Agent 0.2.0, it stands for its horizon and the mind reads its band

The sensing layer of `agent/` (`agent/sensing/revise.py`, #783) writes a reading as TWO graphs
holding for one stretch, from the instant it was taken to the horizon — the cadence with
whatever tolerance the instrument earns. The graph of readings holds the node, what it is of,
which property, and every [band](/domain/band.md) the domain's definitions say a value like
this one is; a graph of sensing's own kind beside it holds the number, the instant, the
instrument and its procedure. A plan forks the first and a step is held to it; a drift and an
envelope read the second where it holds. Nothing marks a reading cold: past the horizon a
reader asking at an instant is handed neither graph, the drift's [prediction](/domain/prediction.md)
whose window has begun is the present instead, and past the last window the property is
unmeasured, which is the desire's side to notice. `sensing:staleSince` is the 0.1.0 container's
mark and stays its.

# Its identity when compared

When a present is matched to a kept world, or a step states what it read, a reading is
stated by its [band](/domain/band.md) — the class the domain asserted on it — and not by its
number; two readings the domain calls the same are one fact (#576).
