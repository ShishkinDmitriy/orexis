---
type: Domain Concept
title: Modality
description: >-
  What a triple's content asserts about its subject — is, may be, would like, could do,
  doing, did, would-be-if — where the subject, the property and the unit stay the same.
  The one thing a reader must know before interpreting a fact, and the axis the mind is
  organised along. Its carrier has moved twice without the concept moving at all — first a
  classification on graphs, now the store itself, with a class owning each — and it is the
  address a question needs, because a value, a bound, an aim and a reading about one
  property are four different assertions that would collide in any container that did not
  keep them apart.
---

# What it is

A **modality** is what a fact asserts, as opposed to what it is about. Fern's moisture is
one subject and one property, and about it a mind holds an observation (what IS), a bound
(what MAY be), an aim (what it PURSUES), a menu row (what it COULD do about it), a
commitment (what it is DOING) and a ledger entry (what it DID) — six assertions that share
every term except their force.
[the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) named them and owns the table;
the [imaginarium](/domain/imaginarium.md) holds the seventh, *would be, if I did*.

# Its carrier, twice moved

The concept has not changed; where it lives has.
[the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) carried it as one of three
axes classifying graphs. [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) moved
it down a level: the **store** does the asserting, and a graph inside one says only who put
the fact there. In code a modality is a **class that owns its store** — `Beliefs`,
`Desires`, the rest as [#299](https://github.com/ShishkinDmitriy/orexis/issues/299) lands —
deciding for itself what kind of store, whether it persists, and whether anything may write
it. The agent holds the modalities; nothing holds or addresses their collection, by the
fourth ruling. Since [a-layer-is-a-package-and-need-loads-it](/decisions/a-layer-is-a-package-and-need-loads-it.md) each class lives in the LAYER that owns it, and there is no floor beneath the
layers: the store engine, the graph naming and the kernel vocabulary's Python spelling sit in
progression (`packages/orexis-progression-patience/store.py`, `graphs.py`, `ontology.py`) with
the intention modality, because progression is the lowest layer that persists anything;
`Beliefs` and `Desires` sit in deliberation (`packages/orexis-deliberation-search/beliefs.py`,
`desire.py`), because a belief and a want are read by the search and by nothing beneath it.
A modality is not a family of packages: what a lower layer needs of an upper one it hears as
an EVENT, never as an import.

# The address a question needs

`orexis-ask` names a modality, required, with no default — the third ruling, which is "there
is no default world" said of a mind — and a module asks for the modality it means
(`agent.desires.read`, sensing's `current_reading`). What makes the address necessary is
the first paragraph: a question that did not say which assertion it meant would be answered
with a value where it wanted a bound.

# The logics these belong to, which are older than this project

The six are not six strengths of one thing. They are different **modal logics**, and the
classification is standard — usually credited to G. H. von Wright's *Deontic Logic* (Mind, 1951),
which coined the middle term and grouped the modes:

| here | logic | Greek | force |
|---|---|---|---|
| [desire](/domain/desire.md) | **bouletic** | *boulē*, will | what is wanted; unmet is a gap |
| [obligation](/domain/obligation.md) | **deontic** | *deon*, what binds | what is owed; unmet is a breach |
| the constitution | **deontic**, its prohibitive half | | what may not be, enforced rather than urged |
| [affordance](/domain/affordance.md) | **alethic** | *alētheia*, truth | what is possible now |
| a freshness want | **epistemic** | *epistēmē*, knowledge | what is known, and how stale |

**The distinction earns its keep at one place**: an obligation is not a stronger desire. They are
different logics, so an unmet want and an unpaid debt fail differently — one is a gap and the
other is a breach — even though [both rank on one unit-free urgency](/domain/desire.md) so that a
drying pot and a litre owed can be compared. Rank them together; do not merge what they assert.

**RFC 2119 cannot express this**, and the attempt is instructive: it defines SHALL as a synonym of
MUST and SHALL NOT of MUST NOT, so it offers three strengths for conformance requirements on an
implementer rather than a vocabulary for what a mind holds.

**And `epistemic` is already in the code** — `Desire.is_epistemic`, seven sites — which is von
Wright's word from exactly this table. The family was half-adopted before it was named.

# Not its neighbours

- **Not [arrival](/decisions/who-put-the-fact-there.md).** Asserted, derived, entailed,
  received, recorded answer *who put the fact there*; a desire is a desire whichever way it
  arrived. The two axes were separated precisely so neither would have to encode the other.
- **Not severity.** Within one modality, severity does the finer splitting — a region and a
  survival envelope are both wants, differing in what violating them means. See
  [a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md).
- **Not a store.** The store is the container (a pyoxigraph triplestore, nothing more); the
  modality is what makes it *that* store — which is why the classes are named `Beliefs` and
  `Desires` rather than anything about storage.
