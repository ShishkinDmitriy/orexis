---
type: Decision
title: The stake is sensing's want — what a reading looks like leaves the kernel, and the kernel derives no want of its own
description: >-
  Every sosa the kernel speaks is "what a reading looks like": the readings query behind the
  desire modality, `current_reading`, the planner reading a value out of a candidate world,
  the signature dropping a timestamp, and the met-shapes `desires.ru` writes over
  observations. And the stake itself — a reading inside the range the subject states — is the
  same kind of want freshness already is: sensing's. Decided: sensing derives the stake as it
  derives the freshness want, keeps the region, the envelope and the gap, and answers the
  planner's and the keeper's questions about readings through hooks; the kernel keeps
  `ag:Desire`, `ag:metWhen`, the pick and the ledger of debts, and derives no want. SSN's
  generic `ssn:forProperty` stays the kernel's word for what a want is about.
status: accepted
timestamp: 2026-08-27T18:00:00Z
---

# What was true before

After [sensing-owns-the-reading-pipeline](/decisions/sensing-owns-the-reading-pipeline.md) and
[self-is-bdi-and-wiring-is-the-packages](/decisions/self-is-bdi-and-wiring-is-the-packages.md)
the kernel still speaks `sosa` in five places, and every one of them is *what a reading looks
like*:

| where | what it does with sosa |
|---|---|
| `regions.py` `_READINGS_Q` | the value, instant and instrument of every current reading, for `desires_of` and `gaps_of` |
| `beliefs.current_reading` | one reading of (subject, property), with `sosa:isSampleOf` for a sampled subject |
| `planner._value_of` | the value a property reads in a candidate world |
| `signature.py` | an observation canonicalises to its upsert key and value, never `sosa:resultTime` |
| `desires.ru` | the stake's met-shapes: *no observation of mine sits below the floor*, written in `sosa:hasFeatureOfInterest` / `observedProperty` / `hasSimpleResult` |

And `desires.ru` is the kernel **deriving a want** — the region want, from
`ssn-system:hasOperatingRange` on the subject or on the instrument that monitors it
(`sensing:monitors`, a package word), with the envelope from `hasSurvivalRange`. Sensing
already derives the freshness want by the same mechanic (`packages/capability/sensing/desires.ru`)
and declares the stake's *measure* (`measures.ttl`, `sensing:measureOf sosa:ObservableProperty`).
The want's shape and the want's measure are in two owners.

# What is decided

**The stake is sensing's want.** *A reading of this property, inside the range the subject
states* — that is a want about a reading, exactly as *a recent reading of this instrument* is,
and the package that already measures it derives it. `desires.ru`'s region-and-envelope
derivation moves to sensing's `desires.ru` beside the freshness want; `Region`, `regions_of`,
`gaps_of` and the gap arithmetic (signed distance, scaled by the survival room) move with it
(a `regions.py` of sensing's own); the kernel shapes that check a region against its
subject's ranges go to sensing's shapes. The reader of `ssn-system:*` leaves the kernel with it.

**The kernel derives no want.** `agent/desires.ru` goes. Every want an agent pursues is
contributed through `Module.desires()` — sensing the stakes and the freshness wants, owing the
debts, hosting the calls — and `regions.desires_of` becomes the *assembly*: the shape, the
measure asked of the choir, the pick, and nothing sosa-shaped. `Desire`'s `value` is filled
by whoever contributed it.

**What a reading looks like is asked, not walked.** Three hooks, all answered by sensing:
`current_reading(subject, property)` becomes a sensing provider method (bidding and actuation
already call `fresh_reading` on it); the planner's `_value_of` becomes `Module.value_in(query,
graph, subject, property)`; and the signature's "never the timestamp" becomes a declaration —
a package marks the predicates that do not count as *where a plan stands* (`ag:volatile`, a
kernel term sensing puts on `sosa:resultTime`), and `signature.py` reads the term, not the
vocabulary.

**`ssn:forProperty` stays the kernel's word for what a want is about.** It is SSN's generic
relation — a condition, a capability, a property of interest, all "for property" — with no
sensing baggage, and it is what every want, intention and aim already carries, including the
aims a sovereign authored in `world/*/beliefs/*.ttl`. `ag:about` in its place would need a
migration that cannot tell a want's `forProperty` from a datasheet condition's. A kernel that
speaks SHACL for shapes and PROV for provenance may speak SSN for "which property".

**The pick stays.** `ag:Aim`, `ag:aims`, `aims_of` and `AimShape` are the agent's choice inside
a range — [pick](/domain/pick.md) — and the shape reads the want's bounds through `ag:metWhen`,
kernel structure. What moves is the range; what stays is the choosing.

# Order of work

1. Readings behind sensing — `current_reading` as a provider method, `value_in` as a hook,
   `ag:volatile` for the signature (#376).
2. The stake as sensing's want — `desires.ru`, `Region`, `gaps_of`, the region shapes, and
   `desires_of` as assembly (#377).
3. Reconcile: `store.PREFIXES` still declares `sosa`/`ssn-system` because prefixes are
   discovered from ontologies; the kernel's own files should then name neither, and the
   ratchet's prefixed-name blind spot (#344) is what would keep it so (#378).

# Seams left open

- **A world with no sensing has no stakes.** That is already true in fact — nothing writes a
  reading — and becomes true in structure: a stake is derived by the package that reads.
- **The debts and the calls are derived by their owners already**; the kernel's `desires_of`
  after this change is an assembly function that happens to live in `regions.py`, and the
  file's name will be wrong the day the regions leave. Rename with #377.
