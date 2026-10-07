---
type: Decision
title: A step's prediction is two graphs it names, stated and never asserted
description: >-
  A step carried what it predicts as a JSON literal of canonical triples in a triplestore, and its
  precondition as a second one nothing wrote or read. The prediction is now two named graphs the
  step points at, `execution:adds` and `execution:retracts`, each classified on the catalogue under
  a kind no reader of the present is handed, so the engine computes the diff, compares the present
  to it and writes a fictive step from it, and a snapshot abbreviates every IRI. Reification and
  RDF-star were measured and refused; the committed step stays a second graph; the step's
  precondition is retired rather than translated.
status: accepted
timestamp: 2026-10-04T18:00:00Z
---

> **Amended 2026-10-07** (#919): what the two graphs hold is what the step's effect changed in the
> world it was applied to, and nothing else. Diffing the world the step reaches against the one it
> leaves is that only where the first was forked from the second. Since #596 a world landing in a
> later ground is forked from that ground with the path replayed, and the two worlds then differ by
> everything the predictions moved between their periods as well: with another van's route laid
> as predictions, every drive carried that van's next cell, a fictive drive wrote it into the
> readings and the landing check held the drive to it. `take` now writes the replayed child
> against the ground it was forked from, each way, into two graphs derived from the child before
> that ground is cleared, and `extract_plan` copies those where they exist. The first two bullets
> under *What it is now* describe the diff of the two worlds, which is still what every world
> forked from its parent gives. The diff is taken per fact, so an effect that deletes a fact and
> puts it back — a wait — predicts nothing: two graphs named and empty, held to the step's landing
> and answered there (`a_wait_across_a_prediction_predicts_nothing`).

# What was wrong

Since #510 a [step](/domain/execution/step.md) said what taking it changes, and the
[executor](/domain/execution/executor.md) held the world to that. It said it as one string:

```turtle
plan:tank1.1 execution:predicts "{\"adds\":[[[\"iri\",\"http://example.org/test#tank1\"],
  \"http://example.org/test#level\",[\"num\",5.0]]],\"retracts\":[[[\"iri\",…]]]}" .
```

Three readers parsed it — the executor's expectation check, its fictive write, and `refine`, which
regresses a step's facts through a bridge — and one writer made it, `extract_plan`, by taking the
canonical facts of two possible worlds in Python and `json.dumps` of the set difference. #759 named
what that costs. Nothing could ask the store *which plans predict a change to this property*, though
every fact needed was in it. Nothing could abbreviate the IRIs inside the string, so every snapshot
carrying a plan was unreadable, which is how the issue was found. And the verdict on whether the
world answered a step was Python comparing parsed JSON against `facts_of` the present — a second,
hand-rolled notion of "the same fact" beside the engine's.

`execution:precondition` was worse: declared, documented on three pages, and written by nothing.
The writer that filled it (#550's remembered-plan check) was retired with 0.1.0, and the reader
that decides whether a step still applies became `Planner._blocked`, which asks the action's own
precondition of the present — since #916 `Planner.check`, as the step is about to be taken. A term
nobody reads is annotation.

# What it is now

A predicted fact has to be **stated without being asserted** — a world where the dose has landed is
not this world. This repo already has a way to state facts without asserting them: a graph whose
kind no reader of the present is handed. A `planning:PossibleGraph` is exactly that, kept in the
imaginarium beside the grounds, and `graphs_of(STATE)` never answers with one. The step's prediction
is the same move at one grain finer.

- **Two graphs per step, named by the step.** `<step>.adds` holds every fact the world the step
  reaches states that the world it leaves does not; `<step>.retracts` holds the converse. The step
  says `execution:adds <…>` and `execution:retracts <…>`. Their rows on the catalogue say
  `execution:AddsGraph` and `execution:RetractsGraph`, both beneath `orexis:Graph` alone — not
  belief, not public, not working — so no reader asking for the present, the public knowledge or a
  package's scratch is handed one. The retracts side is as much a prediction as the adds side, and
  a graph is classified per kind it holds, so the two sides are two graphs and not one with a flag.
- **The diff is the engine's.** `extract_plan`'s one update gained the operations that fill them:
  `INSERT { GRAPH ?adds { ?s ?p ?o } } WHERE { GRAPH ?w { ?s ?p ?o } FILTER NOT EXISTS { GRAPH ?in
  { ?s ?p ?o } } }`, once per world on the ancestry, and the mirror for the retracts. The docstring
  that said "a diff of two graphs is not a pattern" was wrong: it is one `FILTER NOT EXISTS`. A blank
  node keeps its identity across a fork (`copy_graph` is the engine's), so a term diff is at least as
  faithful as the canonical-form diff it replaces. (Amended: where the world was forked from a
  later ground, the diff is against that ground, as `take` wrote it before the ground went.)
- **The verdict is one `ASK`.** The executor asks, over the readings and their revisions as the
  default graph, whether any fact of the adds graph has no equal in the present or any fact of the
  retracts graph has one; the step is answered when the ask is false. Equality is SPARQL's `=`, so
  `5` and `5.0` are one value as they were under the rounded canonical form, and a literal of
  another type is simply not equal.
- **A fictive step is two update operations**: delete from the state what the retracts graph
  holds, insert what the adds graph holds. The Python that rebuilt a term from `("num", 5.0)` and
  refused a blank node is gone with the form it rebuilt from.
- **Refinement reads rows.** `refine(store, me, step, now)` and `bridge.keeps(store, step)` read a
  step's two graphs as the terms they are and bind a bridge's head to them; the `as_fact` that
  made "a canonical fact, whether it came from JSON or from the store" one shape has no second
  source left to reconcile.
- **The graphs travel with the plan.** `publish_plan` copies them into the belief base under the
  published name beside the plan, with their rows; the executor brings them in when a case hands it
  a plan from another store; `withdraw` forgets them with the plan.
- **`execution:precondition` is retired**, with the three pages that described it. What decides
  whether a step still applies is the present asked with the action's precondition, not a stored
  copy of what the search read; translating an unread string into unread graphs would have been
  annotation twice.

# What was refused

- **Reification, four triples per fact.** `[ rdf:subject ?s ; rdf:predicate ?p ; rdf:object ?o ]`
  per predicted fact, hung off the step, is plain RDF 1.1, needs no graph and no catalogue row, and
  a snapshot would inline it readably. It was refused because a reified fact is a *node about a
  triple*, not a triple: every reader that wants to know whether the present holds it rebuilds the
  pattern from three joins, the diff cannot be written as `INSERT { GRAPH ?g { ?s ?p ?o } }` but as
  three triples around a blank node minted per solution, and that node is an identity nothing here
  reads. What a step predicts is the facts of a *world* — the possible world it reaches is a graph
  already, and the diff of two graphs is a graph. RDF 1.2 agrees: writing `<< s p o >>` into
  pyoxigraph 0.5.11 mints a reifier with `rdf:reifies`, the same shape under a newer name.
- **RDF-star, a quoted triple per fact.** Measured on pyoxigraph 0.5.11 before leaning on it. The
  engine stores a triple term, matches `<<( s p ?x )>>` in a pattern and answers it in
  SPARQL-JSON — but as `{"type": "triple", "value": {"subject": …}}`, which `store.rows` flattens
  to a dict where every other column is a string, so every reader gains a special case.
  `hash_named_graph.forms` raises `AttributeError` on an `ox.Triple` object, so a plan graph could
  never be hashed or compared. rdflib 7.6.0 refuses the N-Triples the store dumps
  (`<<( … )>>`), so the snapshot serialiser, which canonicalises through rdflib, would read no
  plan at all — the opposite of what the issue asked for. And the semantics are the wrong way
  round: RDF-star quotes a triple to say something *about* it; a step says nothing about a fact
  except that a world holds it, and a graph is that saying.
- **One graph, the committed step's.** The executor already writes each adopted step as an
  `execution:CommittedStepGraph`, a belief holding over the step's landing window, carrying the
  step's filling for a drift to read as a flow ([committed-step](/domain/execution/committed-step.md)).
  Putting the predicted facts in it would make them *beliefs*: `graphs_of(BELIEF)` would hand "the
  soil is inside its range" to every met-test from the moment of adoption, and the want would read
  met before the world answered. The two graphs differ in modality — believed against stated — and
  in lifetime — the window against the plan — so they are two graphs, and the committed step goes on
  carrying no prediction, which `test_a_committed_step_is_a_belief_over_its_landing_window` pins.
- **Keeping the precondition and translating it too.** Done-when #759 lists it; but a graph
  nothing writes is as dead as a string nothing writes, and the reader that would justify it was
  replaced by a better question. It returns with a reader, if one is ever needed.

# Measured

- pyoxigraph 0.5.11: `ox.Triple` stored as an object term and queried back; `ASK` with a quoted
  pattern binds; SPARQL-JSON answers `"type": "triple"`; `INSERT DATA { … << s p o >> }` writes a
  blank reifier and `rdf:reifies`; `store.dump` emits `<<( … )>>`, which rdflib 7.6.0's N-Triples
  parser rejects.
- The three `plans/` cases regenerated: every step, its order, its instants and its filling
  unchanged; the one `execution:predicts` line per step became two links and two graph blocks of
  one abbreviated triple each, with two catalogue rows per step.

# Seams left open

- **A predicted fact hanging off a blank node** is compared by the node's identity, which survives
  the copy into the belief base but never equals a node the world mints; such a step waits out its
  patience. Nothing shipped predicts one, and the fictive writer used to refuse one outright.
- **A step whose effect replaces what a prediction moved retracts the foreseen value** (2026-10-07,
  #919). The fill in `a_fill_lands_in_a_later_ground` lands where the drain has made the tank four,
  so it retracts four and adds nine, which is what the world is held to at the landing. A FICTIVE
  step writes that at take time, into a present still reading six, and the delete finds nothing:
  the readings would hold six and nine. A step's prediction is facts and the effect's delete a
  pattern, and the pattern does not survive into the facts. Nothing shipped has met it: across the
  suite the only shipped steps whose worlds are forked in a later ground are the courier's fictive
  drives and boardings in the dispatcher and the driver, and there the later ground holds what the
  parent's does, so their two graphs were the same before #919 as after.
- **Equality is exact.** The rounded canonical form compared numbers to six decimals; `=` compares
  values. No step predicts a sensed number — a dose predicts `sensing:inside`, which the rules
  conclude — so nothing has met the difference, and a tolerance belongs in the rule that would
  need it, not in the verdict.
