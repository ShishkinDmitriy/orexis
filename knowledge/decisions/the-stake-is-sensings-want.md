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
already derives the freshness want by the same mechanic (`packages/orexis-capability-sensing/desires.ru`)
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

**The kernel derives no want** (#377, landed). `agent/desires.ru` went, and so did the
kernel's `desires.rq` and `regions.py`. Every want an agent pursues is contributed through
`Module.desires()` — sensing the stakes and the freshness wants, owing the debts (its own
query over its own graph, `packages/orexis-capability-market/ower.py`), hosting the calls — and `Agent.pursuing` is the
whole assembly: it merges the modules' lists and folds a want seen twice into one by its
node, because two sensing modules read the same regions. There is no kernel `desires_of` left
to be an assembly function; `Desire`'s `value` is filled by whoever contributed it. The AIM
went with the region, in the same change and ahead of #380's schedule, on the sovereign's
ruling that a pick in a property checked against a range is sensing's sentence: `sensing:Aim`,
`sensing:aims`, `sensing:AimShape`, `aims_of` in sensing's `regions.py`, `aim()` on the
sensing provider, the world files' aims respelled and `vocabulary.MOVED` carrying a deployed
volume across. The deducer is gone — the kernel has no module in the desire modality now. The
choir's verdicts on a reading (the band, the bounds a board watches, the
urgency a cadence follows, the gaps and the health figures) are sensing's hooks now, and
`ag:KeeperShape` asks for a patience from an agent that `ag:holds` a want whose violation is not
`ag:Stale` — the stake said in the kernel's own words, where "acts for a subject that states
what it needs" was its premise in sensing's.

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

**The kernel keys nothing by property** (#380, landed). The sovereign's ruling, sharper than
the first draft of this record: a property is a sensing notion, and a BDI engine has wants,
acts and commitments, not properties. So `ssn:forProperty` leaves the kernel's vocabulary and
code altogether, not by renaming it but by no longer needing it — with one thing the
implementing change found and this record did not foresee, said first:

**A want is ABOUT something, and the kernel carries that without reading it.** The desire
modality is its own store ([a-store-is-a-modality](/decisions/a-store-is-a-modality.md)), so an
`ag:available` query or an effect rule, which run against the belief base or the imaginarium,
cannot walk `?want ssn:forProperty ?p` themselves — the want is not in the graph they are asked
about. What the kernel passes instead is `ag:about`: the one node a package's query may join a
lever to, stated by whoever derived the want and opaque to the kernel. Sensing says a region
want is about its property and a freshness want about its INSTRUMENT — which is what keeps a
purchase from serving a want about knowing, since the market's queries join `?about` to a
valuation's property and an instrument matches none. `menu_of` hands every action query
`VALUES (?want ?about) { … }`; a row carries the want and its about; the planner binds `$want`
and `$about` for the rule; a want about nothing — a call — ranges over every row of the
agent's own, which is how the dealer's two-step is still found. A generic object of a want is
a BDI notion; which property it is stays sensing's.

- a **want** is identified by its node; `Desire.observed_property` is gone, and sensing's
  `ObservedWant` — the kernel's `Desire` plus the property — is what sensing contributes, so a
  package that needs the property of a want asks sensing (`want_about`, `stake_about`,
  `wants_about`) or reads the field off the object sensing handed over;
- an **intention** is `ag:pursues` the want and `ag:by` the act, and the ledger's
  `ssn:forProperty` is gone; `adopt`, `satisfy`, `drop`, `standing`, `expect`,
  `open_expectations` and suspicion key on (act, want). The ledger migrates at the keeper's
  construction (`vocabulary.migrate_ledger`): a row with a property and no want is given the
  want that property names for the agent, through `ag:about`, and the property triple is
  dropped from every row;
- an **affordance row** carries the want it serves and what that want is about; an action's
  `ag:available` binds `(?want ?about)` from `$wants` and joins a lever to `?about` in its own
  words, and an effect rule is handed `$want` and `$about`;
- the **actors' door** is `pursue_for(want)`; an actor holding a reading asks sensing which
  want it means (bidding: the stake about the property it is priced in; actuation: sensing's
  `want_about`, knowing first);
- the **reading choir** — `annotate`, `bounds`, `urgency`, `on_reading_recorded`, `measures` —
  is no longer defined by name on the kernel's `Module`: the kernel keeps the mechanism
  (`Agent.ask`, `Agent.tell`) and sensing keeps the contract (`sensing/choir.py`). The keeper
  no longer listens for readings; sensing hands it a number per want (`keeper.judge`) and asks
  whether a watch is open (`keeper.watching`). The influx writer takes tags it does not read;
- the **aim** — a pick inside a region — moved to sensing with the region under #377 (above).
  The kernel keeps *pick* as a concept — a belief chosen inside a range, which review moves —
  and holds no aim of its own.

SSN's generic relation was the honest word for "which property" while the kernel had to say
it; it no longer has to say it.

# Order of work

1. Readings behind sensing — `current_reading` as a provider method, `value_in` as a hook,
   `ag:volatile` for the signature (#376).
2. The stake as sensing's want — `desires.ru`, `Region`, `gaps_of`, the region shapes, and
   the kernel's `desires_of` dissolved into the modules' own `desires()`; the aim with them
   (#377, landed).
3. Reconcile (#378, landed): `store.PREFIXES` keeps six vocabularies the kernel speaks itself
   and DISCOVERS the rest off whichever ontology declares them — `sosa:` reaches a query because
   sensing says so; `SOSA` left `agent/ontology.py` for `onboarding/namespaces.py`; the kernel's
   Turtle declares no package prefix it does not use; and the ratchet reads the prefixed form,
   every namespace, and resolves each term it finds (#344). What the widening found was the
   bus — `mqtt:` in `agent/world.py` and in the simulated-device shape — listed as debt with
   what removes it.
4. No property in the kernel — wants by node, intentions by (act, want), rows carrying the
   want and its about, the actors' door by want, the reading choir out of `Module`, the ledger
   migrated (#380, landed). The largest step, and the one that makes the kernel exactly the
   BDI engine.

# Seams left open

- **A world with no sensing has no stakes.** That is already true in fact — nothing writes a
  reading — and becomes true in structure: a stake is derived by the package that reads.
- ~~**The debts and the calls are derived by their owners already**; the kernel's `desires_of`
  after this change is an assembly function that happens to live in `regions.py`.~~ Closed
  with #377: nothing is left of the file at all — the aim went too.
- **`ssn:forProperty` survives in the ledger migration alone** (`vocabulary._LEDGER_PROPERTY`),
  which names what it migrates FROM, as `MOVED` does. It leaves with the last pre-#380 volume.
- **`ag:about` is one node.** A want about two things — a property on two subjects — would
  need two, and nothing derives one; the day it does, `VALUES` grows a row per pair.

# Paid since — the state graph, and the instruments graph

The kernel's last sensing-shaped names went with the audit. `ag:SensedGraph` is `ag:StateGraph`:
the world's current state as this agent holds it — what an effect rewrites, what a plan forks
per step, what a met-test reads — which is all the kernel knows of it; what is in it is the
packages' word. The instance keeps its IRI (`graph/sensed`) so a deployed volume keeps its
readings. The placeholder a rule is handed is `$state`. And `graph/instruments` is sensing's:
declared in sensing's ontology, named in its terms, and found by the kernel as every graph is —
`Store.recorded_graphs()` asks for belief graphs that arrive recorded, so the planner's
imaginarium and the validator carry it without naming it. `ag:Means` and a duplicated
`ag:Action` block left the ontology in the same sweep.
