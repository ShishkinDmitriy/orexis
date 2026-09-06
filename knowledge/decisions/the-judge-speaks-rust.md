---
type: Decision
title: The judge speaks Rust
description: >-
  The SHACL verdict is computed by rudof behind one door, packages/orexis-agent-deliberation/judge.py,
  with the two gaps it ships closed there: SPARQL-based targets are resolved on our own
  engine and handed over as explicit target nodes, and an authored sh:message is put back
  where the engine wrote its own. Severity needed nothing — rudof honours it exactly where
  pySHACL does, which is exactly where this repo declares it. The alternative refused is
  staying on pySHACL, which cost a quarter of a hanoi solve, held the kernel to rdflib, and
  answered qualified shapes wrong under focus. pySHACL is not gone: the inference-parity gate
  and four test files still hold the closure to what it would entail. Measured on the bench:
  three disks 5.52 s against 5.71 s before the swap, having been 7.95 s at the first cut — and
  the swap only paid once the border stopped speaking Turtle, since rdflib's Turtle WRITER was
  a third of a verdict where the Rust validation is a sixth of pySHACL's. A faster engine
  behind a serialization boundary is a slower system until the boundary is cheaper than the
  win.
status: accepted
timestamp: 2026-09-01T17:20:00Z
---

# The judge speaks Rust

The engine under everything else was already Rust — pyoxigraph holds every store and answers
every query, 1,237 of them for 0.4 s in a hanoi solve. The judge was not: pySHACL is the one
complete SHACL implementation Python has, it only speaks rdflib, and that single fact is most
of why rdflib survived in this kernel at all. The sovereign ruled: track the performance, and
use a Rust SHACL implementation — rudof, **if it is actively supported and improving**.

It is, by measurement rather than impression: eight releases in August 2026, two on the day
this was checked, PyPI in lockstep, and a SHACL-SPARQL constraint support that its own issue
tracker still lists as missing — the code had moved past its paperwork. Probed at `pyrudof
0.3.16` with one expected violation per feature, it evaluates EVERYTHING these packages'
shapes use — qualified value shapes, `sh:xone`, SPARQL constraints, all of it — except two
things, and the two are what this record is actually about.

## The two gaps, closed at the door rather than worked around

**`sh:SPARQLTarget` binds nothing, silently.** The empty-result trap in a new coat: twenty-one
shape families would simply have stopped applying, and no test would have gone red on the
engine's account. Closed where the house rules already point: a target select is a QUERY, and
queries here run on pyoxigraph — so `judge.py` resolves every SPARQL target itself against
the data and appends explicit `sh:targetNode`s to the shape text. A shape must be named to
carry a SPARQL target through that door, and a blank one fails loudly rather than losing its
targets.

**An authored `sh:message` is sometimes overwritten** with the engine's own prose. rudof
honours `sh:message` for most constraints and generates its own for some — a qualified
max-count came back *"QualifiedValueShape: 1 nodes conform to shape _:c4d3…, which is grater
than maxCount: 0"* where the shape said *"SoilMoisture is below 0.2 — past what fern survives,
not merely uncomfortable"*. The generated line is about the constraint; the authored one is
about the plant, and a report is read by whoever has to act. So the door restores the
author's message wherever the shape that produced a result states one, correlating by
`sh:sourceShape`.

**And the gap that was not there.** The first cut of this record said severity was flattened
to `sh:Violation` and built a whole apparatus to split shapes by force before the border.
Measured properly, rudof honours `sh:severity` in EXACTLY pySHACL's two places: DOWN on the
property shape for a declarative constraint, UP on the node shape for a `sh:sparql` one — the
split rule [a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md) measured into existence
against the old engine, obeyed to the letter by the new one. The apparatus was deleted. Two
engines, one severity rule, nobody's workaround — and a reminder that the first measurement
of an unfamiliar engine is a hypothesis.

## What was refused

- **Staying on pySHACL.** A real alternative — it is correct, complete, and maintained. Refused
  because it cost a quarter of a hanoi solve in judging alone, answered qualified value shapes
  wrong under `focus_nodes` in both directions ([a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md)
  measured a silent thirsty plant and a false catastrophe), and held the kernel's flat worlds
  to rdflib forever: no judge that reads rdflib can ever let the planner stop building rdflib
  graphs.
- **Splitting shapes by force before the border.** Built, run, and deleted when the engine
  turned out to honour severity where we declare it. It survives in this record because the
  reasoning was sound and the premise was false — and because the shape of the mistake is
  reusable: an apparatus that compensates for an engine you have not measured precisely will
  compensate for something the engine does not do.
- **Removing pySHACL from the repository.** It remains what it is uniquely good for: the
  reference implementation four test files and `tests/test_inference.py` hold the materialised
  closure against. A gate is allowed to be slow and Python; a judge on the planning path is
  not.

## Blank nodes, skolemized at the crossing

rudof pre-binds a SPARQL constraint's `$this` through a `VALUES` clause, and a blank node is
illegal in `VALUES` — so a held envelope (a blank shape in belief data) was a parse error,
"expected UNDEF", 114 tests deep. And a SPARQL target resolving to a blank node could not
cross the serialization border as itself at all. `judge.crossed` therefore skolemizes the
data once per verdict batch; the verdict logic never compares a skolem IRI to anything but
another one.

**Three things had to be learned about WHICH nodes may be named**, each by a failing suite:

- **Not the shapes wholesale.** A property PATH is a blank-node structure — `[ sh:inversePath
  … ]`, a sequence as an RDF list — so naming them turned every path into a plain IRI
  predicate matching nothing: fifty shapes reporting minCount violations against beliefs that
  were perfectly good. Only the constraint CARRIERS are named (the objects of `sh:property`
  and `sh:sparql`), which is exactly what a result cites and never part of a path.
- **Not before the carve.** A caller carves its data-borne shapes out with `cbd`, and cbd
  recurses through BLANK nodes only — so skolemizing the data first stopped the carve at the
  first property shape and dropped every nested constraint with its authored message. Carve
  first, cross after.
- **Deterministically, and by the node's own id.** rdflib's own `skolemize` mints a fresh UUID
  per call, so a graph and a graph carved out of it disagree about every blank node they
  share. Naming a blank node after its id makes the two agree without anything being passed
  between them.

# Amended 2026-09-06: the search no longer crosses the border

The verdicts the search reads — a want's, the law's at every expansion, the winner's legality
— are compiled to SPARQL by the same compiler that says a want (#497, #548) and asked of the
imaginarium at the node's graph. The judge decides at the gates, where the authored report
is for a person, and is the oracle the compiled rows are held to. Two of its behaviours were
measured into the compiler rather than argued: a blank node crosses this border as an IRI, so
`sh:nodeKind sh:IRI` at the gates means "not a literal" and the compiled form says the same;
and a node shape's severity reaches its `sh:sparql`, `sh:or`, `sh:not` and its own value
constraints but never its property shapes, and a severity stated on a constraint node is
ignored. A single UNION over every package shape was tried and refused by measurement — 843
ms on `world/simulation` against 65 for the same branches asked one shape at a time — so the
engine is handed small questions.

# Seams left open

- **rudof's reader has a floor, and it is per read — paid at the gates only, since #548.**
  `read_data` costs ~75 ms before it has looked at anything, on two triples and on 3,500 alike,
  and the floor is paid on every read rather than once per instance (measured 2026-09-06: a
  second read after `reset_data` costs the same). The binding keeps the data across a shapes
  swap (`reset_shacl`) and drops the shapes on a data swap. The search stopped paying it: the
  shapes it judges by compile to selects (`violation.report_selects`) asked of the imaginarium,
  and this judge is what those selects are held to by parity, feature by feature and on a
  shipped world (`tests/test_legality.py`). The floor is rudof's to fix and is unreported
  upstream; boot and onboarding pay it once each, for a report a person reads.
- **The two gaps are of different kinds, and rudof's own roadmap says which.**
  [#94](https://github.com/rudof-project/rudof/issues/94) covers the SHACL Recommendation and
  lists `sh:message` and `sh:severity` as supported; SPARQL-based TARGETS appear nowhere in it,
  because they are SHACL-AF — the same spec as the constraints tracked in
  [#671](https://github.com/rudof-project/rudof/issues/671). So `_resolved_ttl` supplies
  something never claimed and is a stable arrangement rather than a temporary one, while
  `_prose_restored` compensates for a claim the engine does not keep: measured at 0.3.16, an
  authored message survives a `minCount` and is replaced by generated arithmetic on a
  `sh:qualifiedMaxCount`. Neither is reported upstream yet, and the second is a bug worth
  reporting with the six-line case that found it.

# Issues this emits

[#481](https://github.com/ShishkinDmitriy/orexis/issues/481) — a candidate world is copied
into rdflib per node rather than diffed, which is now the largest single cost in a solve and
the last thing holding the planning path to rdflib. The reasoning stays here; the issue says
what is left.
