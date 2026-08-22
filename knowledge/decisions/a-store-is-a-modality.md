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
  ([#263](https://github.com/ShishkinDmitriy/agora/issues/263)) — recomputation is the only
  write path that exists;
- *an asserted want is written from files and never by the agent*
  ([#264](https://github.com/ShishkinDmitriy/agora/issues/264)) — the self-satisfaction
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
| desires | memory | genesis and re-derivation; runtime is read-only | every boot, from files and premises |
| intentions | volume | the keeper | nothing — a commitment survives a restart |
| history | volume ring | the runtime, append-only | the ring's own bound; Influx keeps the rest |
| hypotheses | memory, per pass | the planner | the end of the pass |

**`ag:BeliefsGraph` retires, with the modality graph classes.** Everything in the beliefs
store is a belief; a class that names one graph inside it "the beliefs graph" asserts nothing.
[#65](https://github.com/ShishkinDmitriy/agora/issues/65) asked for a rename; deletion answers
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
  bounds to compute signed distance — and the deducer already materialises exactly that join
  as `Region` objects. The split moves a join into code that performs it now.
- **The affordance walks take the desired properties as a parameter.** Three `affordances.rq`
  files join wiring with *which properties I hold desires in* — a small set, injected as a
  `VALUES` block by the same collector that already substitutes `$me`.
- **Effect rules already take their inputs as parameters.** `GRAPH $beliefs { … ?conversion }`
  becomes `$conversion`, the move
  [#247](https://github.com/ShishkinDmitriy/agora/issues/247) made for `$value` when the
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
  rebirth, `agora-ask`, every module's store handle and the test fixtures all assume one
  store. The order of work below keeps both gates green at every step; no step lands half.
- **The split queries are unmeasured.** The `VALUES`-injected walks and the per-tick gap
  computation are expected to be cheap — small sets, per-tick cadence — and expected is not
  measured. The measurement is the first step, on the Pi, before anything moves.

## Three rulings this record does not make

Each is marked here with a recommendation, and the sovereign decides:

1. **Where the picks live.** A pick is desire-like in what it asserts and belief-like in who
   may write it — it is the one want the agent legitimately moves, inside its mandate.
   Recommendation: the desires store holds only what the agent may NOT author — the mandate,
   the derived regions, the obligations — and the picks stay in the beliefs store as the
   agent's own recorded choices, legitimate exactly while `validate_agent` passes against the
   desires store. The write boundary, not the assertion, is what the store split exists to
   enforce.
2. **Whether the menu is a store at all.** Six-graphs' own seam flagged it as the one graph
   with no independent existence. Recommendation: it stays unmaterialised — recomputed per
   ask, as today — and gets no store, because a pure conclusion needs no container.
3. **What `agora-ask` addresses.** The sovereign asks a mind, not a shard. Recommendation:
   the ask surface presents the union — each store answers and the answers merge — with a
   per-modality address as an optimisation if the union proves slow.

## Seams left open

- **Received-fact trust** is inherited from six-graphs unchanged: a signature checked at the
  edge still leaves no triple. The received graphs now recur in two stores (readings in
  beliefs, obligations in desires), which sharpens the question without answering it.
- **The trigger for revisiting:** if the measurement (order of work, step 1) shows the split
  queries costing what a planning pass costs, the graph-partition of six-graphs remains the
  recorded fallback, and this record is the one to supersede.

## The order of work

1. Measure the split-query shapes on the Pi before anything moves —
   [#296](https://github.com/ShishkinDmitriy/agora/issues/296).
2. Sort the beliefs graph's contents by what each term asserts —
   [#297](https://github.com/ShishkinDmitriy/agora/issues/297).
3. The desires store, read-only to the runtime, with the query splits above —
   [#298](https://github.com/ShishkinDmitriy/agora/issues/298).
4. Intentions and history in stores of their own; the modality graph classes retire —
   [#299](https://github.com/ShishkinDmitriy/agora/issues/299).
