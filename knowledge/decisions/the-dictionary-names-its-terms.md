---
type: Decision
title: The dictionary names its terms, and a test holds the join
status: accepted
timestamp: 2026-08-22T00:00:00Z
description: >-
  A domain page that fixes a word carried by the T-Box binds it in frontmatter — term:
  a full IRI, because the bundle is the unit of distribution and a prefixed name is
  unresolvable outside this repo — and tests/test_knowledge.py holds the join in both
  directions: every bound
  term must be declared, one term has one owner, and every capability family must be bound by
  some page. A page without a term is a statement, never an omission. External vocabularies
  are vendored under tests/fixtures/vocabularies/ so sosa:Observation is checked against SOSA
  rather than against our spelling of it; words borrowed without IRIs, like REA's, never
  appear in term:.
---

# Context

The ubiquitous-language audit found that of the three joins a shared language needs, two were
already gates — prose against prose (`tests/test_knowledge.py`'s
`test_no_two_domain_pages_state_the_same_claim`), code against ontology
(`tests/test_vocabulary.py`, per
[every-term-in-its-own-house](every-term-in-its-own-house.md)) — and the third, dictionary
against ontology, was convention. Convention had let two synonyms stand for months after being
noticed: [a-mandate-is-not-a-commitment](a-mandate-is-not-a-commitment.md) acted on a collision
that `every-term-in-its-own-house` had *recorded* without renaming, and
[channel-is-the-word](channel-is-the-word.md) closed a split nobody had chosen at all.

# Decision

**A domain page that fixes a word the T-Box carries binds it**: `term:` in frontmatter, a
list where one page legitimately fixes two (`review` binds the family and the mandate;
`intention` binds the record and the family). OKF permits producer-defined keys, so the bundle
stays conformant for any consumer.

**The value is a full IRI, never `prefix:Name`.** The first cut wrote `ag:Agent`, and the
review caught what that is: a name resolvable only where the ontologies that declare the
prefixes live. An OKF bundle is the unit of distribution — tarball `knowledge/` alone and a
prefixed name is an opaque string, where `http://example.org/orexis#Agent` is still the term.
OKF's own `resource` field is the precedent for a full URI in frontmatter; `term:` stays a
producer key rather than reusing it because `resource` is singular and a page may bind two.

`test_a_dictionary_term_is_a_declared_one` holds the join:

- every bound term must be **declared** — by a project ontology for our namespaces, by the
  vendored vocabulary for `sosa`, `ssn`, `prov`, `dcterms` and `sh`, and by at least a bound
  namespace for the rest;
- **one term, one owner** — two pages binding one term is the frontmatter form of the
  restatement the overlap gate refuses in prose;
- the reverse, scoped to rule 2's unit: **every class `rdfs:subClassOf ag:Capability` must be
  bound by some page**. A family nobody answers for is the thing the capability rules exist to
  prevent, said about words.
- only the dictionary binds: a decision is an argument about a term, never its owner.

**A page without a `term:` is a statement.** A gap is computed and never stored; an auction is
an event; a venue and a lever are instance-side words whose classes other pages own; a wallet
is designed and unbuilt. Forcing a term onto those would be reification for the gate's sake —
the dictionary is deliberately larger than the T-Box.

# External vocabularies are vendored, not fetched

`tests/fixtures/vocabularies/` holds SOSA and SSN (from the W3C sdw repository's integrated
files), PROV-O, DCTERMS and SHACL — on the
[their-descriptions-are-our-fixtures](their-descriptions-are-our-fixtures.md) precedent, and
for the same reason the gate exists at all: `sosa:hasSimpleResult` should be checked against
what SOSA declares, not against our memory of it, and a gate that needs w3.org up is a gate
that flakes (w3.org served 503s during the very session that vendored these). Words borrowed
**without** their IRIs — REA/ValueFlows, per [settlement-speaks-rea](settlement-speaks-rea.md)
— never appear in `term:`: `vf:` is deliberately unbound, and `term:` names only what code
could query.

# Seams left open

- **Members and single abilities are out of the reverse check.** `sensing:Subscribing`,
  `market:Bidding`, `actuation:Actuation` are typed `a ag:Capability` (or a family) directly;
  the family's page describes them, and requiring a binding each would manufacture owners. If
  a member ever grows a page of its own, binding it there is one frontmatter line.
- **Non-capability classes have no reverse check.** `ag:Graph` subclasses, part and firmware
  models, review's evidence vocabulary — a page per class would be a registry, which is the
  shape this project refuses. The forward direction still covers them the day a page binds one.
- **`schema` and `unit` are prefix-checked only** — vendoring schema.org wholesale is
  megabytes for terms no page currently binds. The day a page binds one, vendor the subset.
