---
type: Runbook
title: Measure the search
description: >-
  How to time and profile the planner on world/hanoi, the tracked measurements, and the
  criteria a faster SHACL engine has to meet before it may judge. Numbers are commits, not
  impressions: every row names what ran and where.
---

# Why hanoi is the bench

`world/hanoi` is the measuring stick because it is all search: no bus, no sensors, no
containers — a plain agent, one desire, one action, and the plan is the whole cost. A change
that moves these numbers moved the planner, not the weather. See
[the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md).

# How to measure

```bash
pytest tests/test_hanoi.py -n0 -q --durations=5        # wall, per test
python -m cProfile -o /tmp/hanoi.prof -m pytest \
    tests/test_hanoi.py::test_three_disks_solve_in_exactly_seven_moves -n0 -q
python -c "import pstats; pstats.Stats('/tmp/hanoi.prof').sort_stats('cumulative')\
    .print_stats('orexis/(packages|agent|tests)/', 14)"
```

Wall times, not profiled times: cProfile roughly doubles everything, so the profile is for
SHARES and the `--durations` run is for the row below. One machine, the bench, stated per
row — a number without its machine is an impression.

# Tracked

| date | commit | 3 disks (depth 8) | 2 disks | notes |
|---|---|---|---|---|
| 2026-08-31 | `718274e` | 5.8 s | 1.9 s | six ground actions; first measurement |
| 2026-09-01 | `13876fc` | 5.71 s | 2.65 s | ONE Move action — one action costs nothing |
| 2026-09-01 | `the-judge-speaks-rust` | 6.19 s | 2.55 s | rudof judge; caches recover most of the border tax, the rest is rdflib serializing at the crossing (#481) |

# Where the time goes (profiled at `13876fc`)

- **~70% of the solve is `effects.applied`** — every candidate step copies the ENTIRE base
  world (~2,300 triples) into a fresh rdflib graph, triple by triple, in Python. Expansion
  is O(world), not O(diff): 76 candidates × 2,300 triples for a plan whose steps each
  change 2–4.
- **All 1,237 SPARQL queries cost 0.4 s** — pyoxigraph is never the problem.
- **`conformance.conforms` ran twice and cost ~25%** — pySHACL judges a world in ~1.4 s,
  most of it cloning and preparing the very graphs `applied` just built.
- Boot (`runtime.Agent` + `validate_agent`) is ~2.6 s and outside the search.

The two levers, in order: judge through a faster engine (below), and stop paying the
per-node rdflib copy — a node's flat world already exists in the imaginarium, so the rdflib
view could be derived lazily at the one boundary that needs it.

# The judge in Rust: criteria before adoption

The engine under everything else is already Rust (pyoxigraph). The judge is not:
[pySHACL](https://github.com/RDFLib/pySHACL) only speaks rdflib, which is why rdflib
survives in the kernel at all. Candidate: [rudof](https://github.com/rudof-project/rudof)
(`pyrudof`) — alive by measurement (8 releases in Aug 2026, two on 2026-08-31; PyPI in
lockstep).

Probed at `pyrudof 0.3.16`, every SHACL feature our shapes use, one expected violation each:

- **Handles**: all Core we use — counts, ranges, `sh:datatype`, `sh:class`, `sh:nodeKind`,
  `sh:hasValue`, `sh:in`, `sh:lessThanOrEquals`, `sh:not`/`sh:or`/`sh:xone`/`sh:node`,
  `sh:inversePath`, qualified value shapes, `sh:targetNode`/`Class`/`SubjectsOf`/`ObjectsOf` —
  **and `sh:SPARQLConstraint`**, its own tracker notwithstanding.
- **Gap 1 — `sh:SPARQLTarget` binds NOTHING, silently** (we hold 21). The empty-result trap
  in a new coat: a shapes family would simply stop applying, and no test would go red on the
  engine's account. Closed on our side: the seam resolves SPARQL targets itself, on our own
  engine, and hands the judge explicit `sh:targetNode`s.
- **Gap 2 — an authored `sh:message` is sometimes overwritten** by the engine's own prose (a
  qualified max-count reports its arithmetic where the shape named the plant and the edge).
  Closed on our side: the door restores the author's message, correlating by `sh:sourceShape`.
- **Not a gap, though the first measurement said so — `sh:severity`.** rudof honours it in
  exactly pySHACL's two places: down on the property shape for a declarative constraint, up
  on the node shape for a `sh:sparql` one. A split apparatus was built for this and deleted.

Adoption is legitimate exactly when the full suite and every world's `orexis-validate` pass
with the seam in place — the same gate every other change answers to. **A row below says so**:
the judge is rudof, behind `packages/orexis-agent-deliberation/judge.py`, both gaps closed on
our side of the door — see [the-judge-speaks-rust](/decisions/the-judge-speaks-rust.md).
pySHACL remains the reference the inference-parity gate holds the closure against.

| date | engine | probe / result |
|---|---|---|
| 2026-09-01 | pyrudof 0.3.16 | feature probe as above; 2.5k-triple parse+validate ×10: rudof 1.18 s, pySHACL 2.60 s |
| 2026-09-01 | pyrudof 0.3.16 | ADOPTED. Blank focus nodes break rudof's VALUES pre-binding — skolemize at the door, but ONLY the data and the constraint carriers: naming a property path's blank nodes breaks the path. Border crossed per verdict at first (7.95 s); serialize-once + caches: 6.19 s |
