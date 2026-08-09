---
type: Decision
title: One graph both engines read — entailments are materialised, not inferred twice
description: The vocabulary's entailments are asserted into the store at genesis, and validation runs with inference off against that same graph.
status: accepted
stage: v1
tags: [inference, rdfs, shacl, validation, vocabulary, store]
timestamp: 2026-08-09T00:00:00Z
---

# Context

Two engines read this society's graphs and they did not agree about what it says.

`pyshacl` validated with `inference="rdfs"`, so a shape's SPARQL saw
`onewire:DataPinRole a mc:OutputRole` — asserted nowhere, entailed through two `rdfs:subClassOf`
steps. `pyoxigraph`, which every query at runtime goes through, infers nothing at all. **A world
could therefore validate against a relationship the code would never observe.**

[#27](https://github.com/ShishkinDmitriy/agora/issues/27) recorded this as *"the runtime does no
inference"*, and that framing is not quite right. Counted before changing anything:

- **six** queries carried `rdfs:subClassOf*` property paths by hand — `runtime.py`'s `_family_q`,
  and three capabilities' `rules.ru`
- **twenty-five** subclass axioms were declared across `vocabulary/` and `agent/capabilities/`

So the runtime *did* infer. It inferred **by hand, inconsistently** — an axiom meant something
only where whoever wrote the query happened to remember to walk it, and the other nineteen had no
reader at all. That is the sharper defect, and it is the one that scales badly: every new
capability inherits the obligation to remember.

The trap had already caught the code twice. `ag:models rdfs:subPropertyOf ag:polls` made shapes
see simulated sensors as polled while the runtime did not, and the workarounds are still legible
— `onboarding/mqtt.py` asks a second time, `dashboards.py` survives on a `UNION`. And it had just
caught it a third time: `review.py`'s `_REVISABLE_Q`, shipped in
[a-belief-is-a-pick-within-a-range](a-belief-is-a-pick-within-a-range.md), reads
`?term a ag:RevisableBelief` with no path, so a package declaring a revisable belief through a
subclass would have validated perfectly and returned nothing.

# Decision

**Materialise a restricted closure into the store at genesis, and turn validation's own inference
off.** `agora/inference.py` runs inside `refresh_public`, after the files are loaded and *before*
each package's `rules.ru`, so a derivation rule may ask what a thing **is** rather than spelling
out how to find out.

What is computed is deliberately narrow: transitivity of `rdfs:subClassOf` and
`rdfs:subPropertyOf`, and the type and property entailments that follow. Nothing else.

Full RDFS entailment was refused rather than deferred. It would assert that every resource is an
`rdfs:Resource` and every property an `rdf:Property` — true, useless, and it would multiply the
triple count that [agent-metrics](../domain/agent-metrics.md) reports as flat and that
[a-belief-is-a-pick-within-a-range](a-belief-is-a-pick-within-a-range.md) leans on to trigger
compaction. The closure is exactly what the code and the shapes actually ask.

## It cannot go stale, and it cannot accumulate

`refresh_public` replaces the ontology and world graphs from the ratified files on every start
and then re-runs the closure, so it is a function of the files rather than a deposit. Running it
twice changes nothing, which is asserted rather than assumed.

## Six hand-rolled paths became one literal question

Every site that read `?x a ?type` and then joined the ontology for `?type rdfs:subClassOf* C`
collapsed to `?x a C` in a single graph. The two-graph join existed *because* the runtime could
not infer; with the entailment asserted, the join has nothing left to do.

# The option not taken

**Stop inferring in validation and leave both engines equally literal** was the cheapest fix, and
#27 named it. It was tested rather than argued about, and the result is worth recording because
it is counter-intuitive in both directions.

Flipping `inference="rdfs"` to `"none"` and validating all three worlds **passed**. That looks
like the answer and is the trap: `sh:targetClass` and `sh:class` match subclasses *by SHACL's own
specification*, independent of any reasoner, so the shapes that target `mc:Peripheral` kept
firing on a `probe:CapacitiveMoistureProbe` and everything appeared fine.

Running the test suite is what showed it. **Seven shape tests failed**, every one of them a
`?role a mc:…Role` test *inside a `sh:sparql` constraint* — which is ordinary SPARQL and does no
subclass matching. So the dependency is real, and it lives in precisely the construct the runtime
also uses. Taking that option would have meant hand-rolling property paths into the shapes too:
spreading the workaround rather than removing it, and making `rdfs:subClassOf` decoration as #27
predicted.

Validation *does* now run with inference off — but against a graph that already carries the
entailments, which is a different claim.

# Consequences

- **The vocabulary's axioms mean something everywhere, not somewhere.** Declaring a subclass is
  now sufficient; no reader has to be told.
- **`_family_q` stopped depending on an accident.** Its subclass branch matched *reflexively*, and
  that zero-length match is what made `agent.provider(ACTUATION)` resolve at all — there is no
  term anywhere declared `a ag:Actuation`. The reflexive case is now stated outright, because a
  behaviour nobody wrote down is a behaviour the next edit removes.
- **Two test helpers were validating something no caller builds.** `_flatten` and `_wiring` in
  `tests/test_shapes.py` parsed the vocabulary from *files*, so they never saw the materialised
  graph — the same drift this decision is about, inside the tests meant to catch it. Both now go
  through a real store, which is what makes their "exactly as validation sees it" true.
- **The guard is a comparison, not a scan.** `tests/test_inference.py` runs validation both ways
  over the same graph and requires the same verdict, so if pyshacl ever entails something the
  closure does not, a test fails rather than a deployment. A source scan additionally refuses a
  seventh hand-rolled path — reading only query strings, since scanning raw text would punish the
  comments explaining why the paths went away.

# Seams left open

- **`owl:` axioms are not materialised.** `owl:Class` appears throughout the vocabulary but only
  as a type; no OWL semantics are computed, and an `owl:equivalentClass` or `owl:inverseOf` would
  be as invisible to the runtime as `rdfs:subClassOf` was. The guard does not catch that, because
  nothing declares one yet.
- **The closure runs on every start, for every agent.** It is milliseconds on a graph this size
  and nobody has measured it on the Pi under nine agents starting at once.
- **`rdfs:domain` and `rdfs:range` entail types too**, and are not computed. Deliberate: they are
  declared here as documentation of intent, and materialising them would type things by the
  properties they happen to carry — which is how a `mc:gpio` on a class would have made that class
  infer as an `mc:Pin` and be held to a pin's shapes. That trap is recorded in
  [pins-and-wires](pins-and-wires.md), and this decision leaves it defused by not reasoning there.
