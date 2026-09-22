---
type: Decision
title: A store is a modality, and a graph is who put the fact there
description: >-
  The sovereign moved the mind's partition one level down. Six-graphs classified graphs on
  three axes; now the MODALITY is a STORE, and inside each store graphs carry only arrival.
  What it buys is structure where there was discipline — the desires store is rebuilt from
  premises and read-only to the runtime, so "never retracted, only recomputed" and "never
  written by the agent" stop being rules and become the absence of a write handle — and each
  modality chooses its own persistence, which the imaginarium and the series store had each
  already chosen alone. The cross-modality joins that made one dataset look necessary
  concentrate at a single seam, and every crossing already has a native shape in the house.
status: accepted
timestamp: 2026-08-22T18:30:00Z
---

# A store is a modality, and a graph is who put the fact there

Ruled by the sovereign, refining [the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md)
rather than repealing it. That record found the organising principle — *the graph is the
modality* — and classified every graph on three axes: modality, visibility, arrival. This one
moves the first axis down a level: **a modality is a STORE, and within each store the graphs
say only who put the fact there** — asserted, derived, entailed, received, recorded, exactly
the arrival axis [who-put-the-fact-there](/decisions/who-put-the-fact-there.md) built. Three
axes become two levels; the container does the asserting, and the graph does the attributing.

The third axis folds rather than falls. Rule 4 means visibility was never a store property —
there is no shared store, so every store is one agent's copy — and what "public" always meant
was *genesis-authored and identical for everyone*, against *this agent's own at runtime*.
That is arrival, seen from outside: the sovereign's and the vocabulary's graphs against the
agent's recorded and received ones.

## What it buys: structure where there was discipline

**The desires store cannot be written by the one who wants.** It is rebuilt — from the
ratified files and the derivation rules, at boot and again whenever re-derivation runs — and
the runtime holds a read-only handle. Three standing rules stop being rules:

- *desires are never retracted, only recomputed*
  ([#263](https://github.com/ShishkinDmitriy/orexis/issues/263)) — recomputation is the only
  write path that exists;
- *an asserted want is written from files and never by the agent*
  ([#264](https://github.com/ShishkinDmitriy/orexis/issues/264)) — the self-satisfaction
  loophole closes because there is no handle to open it with;
- the violation [aim](/domain/aim.md) files — a want living among settings, excused because
  one dataset made it merely untidy — becomes unwritable instead of filed.

**Each modality chooses its own persistence, and two already had.** The imaginarium is this
pattern's first instance: the hypothesised modality lives in a store of its own because a
hypothesis must not survive the pass, where an intention must survive a restart — the
lifecycle argument, already decided in
[a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md).
The series store behind history is the second
([two-store-beliefs](/decisions/two-store-beliefs.md)). Store-per-modality is those two
precedents generalised, because modality *determines* lifecycle:

| store | persists | written by | reset by |
|---|---|---|---|
| beliefs | volume | endowed at birth; records and receives at runtime | nothing — `rebirth` only |
| desires | memory | its rebuild alone — from files, premises, and the recorded picks; runtime is read-only | every boot and every re-derivation |
| menu | memory | its rebuild alone, from premises | every rebuild — a conclusion is recomputed, never edited |
| intentions | volume | the keeper | nothing — a commitment survives a restart |
| history | volume ring | the runtime, append-only | the ring's own bound; Influx keeps the rest |
| the [imaginarium](/domain/imaginarium.md) | memory, per pass | the planner | the end of the pass |

**The modality graph classes are retired — ALL of them, by
[#312](https://github.com/ShishkinDmitriy/orexis/issues/312)**: `orexis:BeliefsGraph` first, then
`orexis:DesireGraph`, `orexis:ConstraintGraph` and `ag:BoundsGraph` when the copy they selected
dissolved — genesis derives no wants, the modality's own build runs the packages' `desires.ru`
against the world and the records on every rebuild, and the belief base keeps records only,
typed for what they are (`orexis:PickRecordGraph`, `market:ObligationsGraph`). Amended by
[a-root-holds-always-and-an-outdated-graph-is-dropped](/decisions/a-root-holds-always-and-an-outdated-graph-is-dropped.md):
the ROOTS are authored at genesis into a graph the build projects, deducing
nothing — the rules run at birth and at boot to endow. Amended again by
[a-graph-class-is-named-for-what-it-holds](/decisions/a-graph-class-is-named-for-what-it-holds.md):
the spelling `orexis:DesireGraph` is back as a CONTENT class — a graph of `orexis:Desire` rows,
the roots and the promises, beside `orexis:WantGraph` for the pursued — which is a different
claim from the modality class retired here: what rows a graph carries, said by its owner, and
not which store it belongs to. That build was also
[#263](https://github.com/ShishkinDmitriy/orexis/issues/263)'s mechanism: re-derivation during
a life is any rebuild, and a want whose premise has ceased is no longer implied. Everything
in the beliefs
store is a belief; a class that names one graph inside it "the beliefs graph" asserts nothing.
[#65](https://github.com/ShishkinDmitriy/orexis/issues/65) asked for a rename; deletion answers
it more strongly. The graph classes that survive are the arrival ones — and the reader
discipline survives with them: ask the store what graphs it holds, never count them.

## Why the join objection fails, measured against the queries that exist

The argument for one dataset was that SPARQL joins across modalities and a store is the join
boundary. Audited (2026-08-22, every `.rq`, `.ru`, `effects.ttl` and inline query), the
crossings concentrate at **one seam** — desire shapes read as data beside wiring or readings —
and every crossing already has a native shape in the house:

- **Pursuit is validation, not a join.** A desire is a shape
  ([a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md)), and pySHACL takes the shapes
  graph and the data graph as separate arguments. The shapes come from the desires store, the
  data from the beliefs store; this boundary exists in the API today.
- **The gap computation already lives in Python.** `gap.rq` and `desires.rq` read a shape's
  bounds to compute signed distance — and sensing's `gaps_of` already materialises exactly that join
  as `Region` objects. The split moves a join into code that performs it now.
- **The affordance walks take the desired properties as a parameter.** Three `affordances.rq`
  files join wiring with *which properties I hold desires in* — a small set, injected as a
  `VALUES` block by the same collector that already substitutes `$me`.
- **Effect rules already take their inputs as parameters.** `GRAPH $picks { … ?conversion }`
  becomes `$conversion`, the move
  [#247](https://github.com/ShishkinDmitriy/orexis/issues/247) made for `$value` when the
  baseline stopped being a store lookup — and for the same reason: a rule is a function of
  its inputs.
- **Intention never joins belief; it copies.** An expectation copies its baseline into its own
  row (#165), so nothing points across the boundary and nothing dangles when the ring turns.
- **Genesis holds every handle.** A derivation reads premises from one store and inserts into
  another; the orchestrator that runs the rules owns both ends, as it always has.

## What it costs, stated before it is paid

- **Sorting the picks becomes mandatory.** Six-graphs found the beliefs graph holds picks and
  left "move the data to match the labels" optional. A store split forces the sort, term by
  term: what a term asserts decides which store holds it, and nothing may stay filed as
  "untidy but excused".
- **The migration is the largest since the package tree.** Genesis, endowment, compaction,
  rebirth, `orexis-ask`, every module's store handle and the test fixtures all assume one
  store. The order of work below keeps both gates green at every step; no step lands half.
- **The split queries are MEASURED, and the split is faster than the join.** On the Pi,
  against `world/simulation`'s fern with a prototype desires store of 545 quads beside a
  beliefs store of 2,716 (medians of 30, each split checked equal to the query it replaces):

  | crossing | one dataset | split | why |
  |---|---|---|---|
  | `desires.rq` | 3.2 ms | 1.0 ms | two small scoped queries and a Python join beat one large `UNION`-and-`BIND` plan |
  | market affordance walk | 0.8 ms | 0.6 ms | props from the desires store, `VALUES`-injected into the wiring walk |
  | `AcquireEffect` | 0.8 ms | 0.5 ms | conversion prefetched, `$conversion` a parameter |

  Two bounds on what this says: the world was freshly born, so the obligation branch ran over an
  empty obligations graph on both sides — its cost is bounded by open claims, which are few by
  construction; and the Python join reproduced the region want arithmetic (asserted equal, to three
  decimals) but not staleness, which is two comparisons. Neither can turn a 3x win into the
  pass-scale loss the fallback was reserved for.

## Three rulings, made by the sovereign (2026-08-22)

Each was drafted here with a recommendation the other way, and the sovereign ruled all three
in the same direction — **modality purity, strictly**. A pick is a want, so it lives with
wants; the menu is a modality (*could do*), so it is a store like the others; a mind
addressable by modality is asked by modality. The draft's counter-arguments were about
write paths and convenience, and the ruling is that the axis is not to be bent for either.

1. **The picks live in the desires store.** What preserves "read-only to the runtime" is the
   write PATH, not an exception: a re-pick is RECORDED — review writes the revision where the
   agent's own acts are written, which persists in a volume — and the desires store is then
   **recomputed**, its build reading the latest recorded picks among its premises. No module
   ever holds a writable desires handle; *recomputation is the only write path* survives the
   ruling intact, and birth becomes the first entry in the pick record, which is what
   six-graphs' "birth authors picks and nothing else" already said. A pick's legitimacy is
   unchanged: `validate_agent` against the mandate, at the rebuild.
2. **The menu is an in-memory store.** Materialised from premises, never persisted, so a
   model and the sovereign read what the agent could do as data. What guards the staleness
   this record's draft feared is the lifecycle: rebuilt with the same discipline as the
   desires store — a conclusion is recomputed, never edited — and holding no row anything
   is allowed to write.
3. **`orexis-ask` names a modality.** A required argument, not a default — the same rule as
   "there is no default world", for the same reason: a fallback answers a question the asker
   did not ask. A question spanning modalities is several asks, and that cost is accepted.

A fourth ruling followed from the third, when the first implementation grew a `Mind` object
to hold the stores: **the collection has no name, because nothing addresses it.** An agent
holds its MODALITIES — `agent.beliefs`, `agent.desires`, the rest of the table — and each
modality is a class that OWNS its store: what kind of store, whether it persists, and whether
anything may write it are that class's decisions, invisible to the agent and to every module.
Separation of concerns, ruled explicitly: the belief modality chose a writable volume-backed
store, the desire modality chose a rebuilt in-memory one exposing no writer, and the agent
cannot tell. `orexis-ask` names a modality, a module names the one it means, and ruling 3 is
precisely what removed the one caller a union would have had. A holder no question needs is
a namespace, not a concept, and the dictionary takes no page for it. "The mind" stays what
it always was in these records: the sitting's phrase for the frame, not a component.

## The sort, term by term

What [#297](https://github.com/ShishkinDmitriy/orexis/issues/297) asked for: every term
authored into `graph/picks/<agent>` across the shipped worlds, classified by what its
triple asserts. The test that decides each row: **can the world contradict it?** A belief can
be WRONG — a later reading, a ledger, a drained pot can refute it. A pick can only be
ill-chosen; nothing in the world makes 600 seconds of patience false. Falsifiable goes to
beliefs; unfalsifiable is a want about conduct or the world, and by ruling 1 every want is
the desires store's.

| term | asserts | store |
|---|---|---|
| `sensing:aims` (with `ssn:forProperty`, `schema:value`) | the point steered for — a want about the world | desires |
| `sensing:fastSleepS`, `sensing:slowSleepS` | the cadences it wants kept | desires |
| `sensing:readingGraceS`, `sensing:maxReadingAgeS` | how long silence is tolerated | desires |
| `sensing:alarmDeltaFraction` | what counts as a jolt | desires |
| `intention:patienceS` | how long a commitment absorbs a second impulse | desires |
| `actuation:doseGraceS` | slack granted past a dose's open-seconds | desires |
| `reporting:metricsIntervalS` | how often it wants to say how it is | desires |
| `review:reviewIntervalS` | the floor on how often it reconsiders | desires |
| `market:bidWindowS`, `market:roundCooldownS` | the host's chosen schedule | desires |
| `market:offerQuantityL`, `market:reservePricePerL` | what the host chooses to offer and refuse | desires |
| `water:maxValuePerL` | willingness to pay at peak urgency | desires |
| `water:litresPerFraction`, `water:litresPerStoredLitre` | what a dose DOES to the property — falsifiable by the next reading | beliefs |
| `market:hasEndowment` | what it holds — falsifiable by the ledger | beliefs |

Two consequences, for [#298](https://github.com/ShishkinDmitriy/orexis/issues/298):

- **Endowment follows modality.** An amendment that grants a capability authors that
  capability's never-held terms — and under the split, each lands in the store its row above
  names, not uniformly in beliefs.
- **No local name changes**, so the by-local-name migration mapping
  ([a-volume-can-be-older-than-the-vocabulary](/decisions/a-volume-can-be-older-than-the-vocabulary.md))
  has nothing to carry for the sort itself; what moves is which store a volume's triples are
  loaded into at boot, which is #298's build to write.

## Seams left open

- **Received-fact trust** is inherited from six-graphs unchanged: a signature checked at the
  edge still leaves no triple. The received graphs now recur in two stores (readings in
  beliefs, obligations in desires), which sharpens the question without answering it.
- **The trigger for revisiting did not fire.** The measurement (order of work, step 1) was
  reserved the right to send this record back; it came in faster on every crossing instead.
  The graph-partition of six-graphs remains the recorded fallback should a future crossing —
  an obligation-heavy society, a query the audit did not foresee — cost what a planning pass costs.

## The order of work

1. Measure the split-query shapes on the Pi before anything moves —
   [#296](https://github.com/ShishkinDmitriy/orexis/issues/296). DONE: every split faster
   than the join it replaces; the table above. Verdict: proceed.
2. Sort the beliefs graph's contents by what each term asserts —
   [#297](https://github.com/ShishkinDmitriy/orexis/issues/297).
3. The desires store, read-only to the runtime, with the query splits above —
   [#298](https://github.com/ShishkinDmitriy/orexis/issues/298). DONE, in three PRs: the store
   (#304, with the modality classes), the readers (#306, with `Picks` named for what it holds),
   and the root desire — a world states it as a TriG block plus the typing that lets the
   catalog call the graph what it is, and an amendment that drops it drops it everywhere,
   because `put_graph` now replaces every graph a file names. Endowment needed no code: a
   granted pick lands in the record, and the store is built after endowment and rebuilt on
   every premise move — a re-pick, an obligation transition, boot.
4. Intentions and history in stores of their own; the modality graph classes retire —
   [#299](https://github.com/ShishkinDmitriy/orexis/issues/299).
