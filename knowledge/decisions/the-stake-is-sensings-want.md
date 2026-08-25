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
  `ag:Desire`, `ag:metWhen` and the ledger of debts, derives no want, and keys nothing by
  property: a want is its node, an intention is an act pursuing a want, and the aim moves to
  sensing with the region it sits in.
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

**What a reading looks like is asked, not walked** (#376, landed). `current_reading` is a
sensing provider method (bidding, actuation and hosting reach it through `agent.provider`, as
they already reached `fresh_reading`); the keeper is handed the baseline a watch leaves from by
the actor that opens it; the planner reads no value at all — an effect rule reads where the
property stands from `$sensed` itself, and an actor sizing a step (`Module.size(query, graph,
property)`) asks sensing's `value_in` at the node's graph; and the signature's "never the
timestamp" is a declaration sensing makes on the class it writes — `sosa:Observation
ag:keyedBy` its feature and property, `ag:carries` its result — which `signature.py` reads once
per pass and canonicalises by, naming no vocabulary. (The record first said `ag:volatile`;
saying what a node is keyed by and what it carries is the same declaration from the side that
keeps a look from being a new world, and it needs no list of what to ignore.)

**The kernel keys nothing by property.** The sovereign's ruling, sharper than the first draft
of this record: a property is a sensing notion, and a BDI engine has wants, acts and
commitments, not properties. So `ssn:forProperty` leaves the kernel's vocabulary and code
altogether, not by renaming it but by no longer needing it:

- a **want** is identified by its node; `Desire.observed_property` goes, and a package that
  needs the property of a want it holds walks `?want ssn:forProperty ?p` in its own query;
- an **intention** is `ag:pursues` the want and `ag:by` the act — both already written — and
  the ledger's `ssn:forProperty` goes; patience, suspicion and `standing(...)` key on (act,
  want). The ledger migrates: a row's property becomes the want it pursued, found through the
  want the property named for that agent;
- an **affordance row** and an **act** carry the want they serve, not the property; an
  action's `ag:available` binds `?want` from `$wants` and walks to the property on the
  package's side, and an effect rule is handed `$want` and walks the same way;
- the **actors' door** is `pursue_for(want)`; an actor holding a reading finds the want it
  means by its own query (bidding: the want about the property it is priced in);
- the **aim** — a pick inside a region — moves to sensing with the region: `ag:Aim`, `ag:aims`,
  `aims_of` and `AimShape` become sensing's, and the sovereign-authored aims in
  `world/*/beliefs/*.ttl` are read by sensing's words. The kernel keeps *pick* as a concept —
  a belief chosen inside a range, which review moves — and holds no aim of its own.

SSN's generic relation was the honest word for "which property" while the kernel had to say
it; it no longer has to say it.

# Order of work

1. Readings behind sensing — `current_reading` as a provider method, `value_in` as a hook,
   `ag:volatile` for the signature (#376).
2. The stake as sensing's want — `desires.ru`, `Region`, `gaps_of`, the region shapes, and
   `desires_of` as assembly (#377).
3. Reconcile: `store.PREFIXES` still declares `sosa`/`ssn-system` because prefixes are
   discovered from ontologies; the kernel's own files should then name neither, and the
   ratchet's prefixed-name blind spot (#344) is what would keep it so (#378).
4. No property in the kernel — wants by node, intentions by (act, want), rows and acts
   carrying the want, the actors' door by want, the aim to sensing, the ledger migrated
   (#380). The largest step, and the one that makes the kernel exactly the BDI engine.

# Seams left open

- **A world with no sensing has no stakes.** That is already true in fact — nothing writes a
  reading — and becomes true in structure: a stake is derived by the package that reads.
- **The debts and the calls are derived by their owners already**; the kernel's `desires_of`
  after this change is an assembly function that happens to live in `regions.py`, and the
  file's name will be wrong the day the regions leave. Rename with #377.
- **`ssn:forProperty` in `agent/ontology.ttl`'s comments** narrates the old arrangement until
  #380 lands; the term itself is declared by SSN, not by us, so nothing in the T-Box changes.
