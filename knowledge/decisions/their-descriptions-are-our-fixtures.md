---
type: Decision
title: Their descriptions are our fixtures, and a part is not a deployment
description: The W3C's own SSN worked examples are vendored as test fixtures, because whether a standard description can be deployed without editing was a question reasoning kept circling and one measurement settled. The answer is yes for a description and no for an illustration. Two relaxations were needed and both were spelling — the legacy http schema.org namespace and QUDT 1.1 — while the four remaining refusals are deployment facts no vendor could know, which is the boundary that makes "as-is" coherent rather than a wish.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

[one-word-for-one-relation](one-word-for-one-relation.md) settled which of our terms defer to a
standard, by asking whether the standard answers the same question. That worked for terms. It did
not answer the operational question behind it: **can a description written by somebody else be
used here at all?**

The ambition is specific — take a vendor's SSN description of a part and put it in a world. Not
translate it, not re-key it, not extract from it. Use it.

That question kept being argued from first principles and the arguments kept being wrong, in both
directions. So it was measured instead: the W3C's own worked examples of a DHT22 — the KY-015's
sibling, written by the people who wrote the vocabulary — dropped into a copy of `world/sensing`
and held to every shape this project owns.

# Decision — vendor them, and let the shapes report

`tests/fixtures/w3c-ssn/` holds `dht22.ttl` and `dht22-deployment.ttl` from
[`w3c/sdw`](https://github.com/w3c/sdw), byte-identical to upstream and checkably so: the git blob
hash of each equals the blob SHA GitHub reports. `tests/test_w3c_descriptions.py` builds a world
around them through the same path `agora-validate` uses.

**Through the real path, not over a bare graph.** Validating the fixture as a standalone graph
reports two violations about scaling curves that no deployment ever sees, because neither the
derivation nor `agent/inference.py`'s closure has run. A measurement that reports faults a
deployment cannot have is a measurement of the harness.

## What the measurement said

**A standard deployment description needs no editing at all.** `dht22-deployment.ttl` — rooms,
walls, boards, deployments, and the `PCBBoard1` that carries `sosa:hosts` and `ssn:hasSubSystem`
on one edge — satisfies every shape here, verbatim, with no overlay and nothing relaxed.

It works because that file describes **platforms and systems and declares no `sosa:Sensor`**. Our
sensor shapes ask for deployment facts; there is no sensor to ask about. Which is the whole
finding in miniature: a description of where things are mounted is complete on its own, and a
description of a sensor is not.

**A device description is missing exactly the deployment.** Their two DHT22 channels lack a name
on our wire, a sense mode, a subject and a topic — four refusals, and a vendor could not supply
any of them. They are facts about *this* deployment. Their absence is correct, and calling it an
incompatibility was the error the measurement corrected.

## Two relaxations, and both were spelling

Neither was a modelling conflict. Both made a figure their file **plainly states** invisible to a
shape.

**schema.org's legacy namespace.** They write `http://schema.org/`; ours is the canonical
`https://schema.org/`. schema.org calls https preferred while http *"will remain widely understood
for the foreseeable future"* — but RDF does not care what a registry prefers. Two IRIs, so their
`schema:value` is not our `schema:value`, and the shape reported a node as missing figures it
states correctly in the other scheme.

Sharpest detail: the idiom was copied **from this example** in
[one-word-for-one-relation](one-word-for-one-relation.md), and written in a different spelling
than the example it came from. All three violations that example raised about its frequency were
this, and none was the QUDT version they looked like.

Bridged one direction only — legacy entails canonical — so a vendor's file satisfies our shapes
and nothing here emits the legacy form. `agent/inference.py` rule 4 carries it, which is the rule
written for exactly this and whose own comment recorded that it had nothing left to exercise.

**QUDT 1.1.** Their unit is `qudt-1-1:Second`, a different namespace rather than an older
spelling. `sh:in` now says which spellings can be *read*, where `packages/part/dht11/` shows the one
we write. A figure is still refused unless it says seconds.

## What still refuses, and why that is the point

One node in the whole world: their `<observation/1087>`, a sample reading included to illustrate
`ssn-system:qualityOfObservation`. It states a sensor and a procedure and nothing else — no
result, no time, no feature of interest, no author.

**It stays refused.** Completing it in the overlay would have bought a green test by fabricating
provenance for a reading nobody took, which is precisely what `prov:wasGeneratedBy` on a reading
exists to prevent. A test names the residue instead, so it cannot grow quietly.

The distinction is worth keeping: a vendor ships a **device**, and a reading is **ours**. Their
example bundles one for illustration, and that one part of their file was never deployable.

# Consequences

- **"Use a standard description as-is" is coherent, and the boundary is the part/deployment
  line.** A vendor describes what a thing IS and what it CAN do; a world says where it is, who
  drives it, what it watches and where it publishes. Neither restates the other, and our fixtures
  now demonstrate exactly that split rather than asserting it.
- **The frequency figure is corroborated.** Their datasheet says 2 seconds, which is what
  `packages/part/dht11/` declares for the KY-015 — a number nobody here measured, confirmed by the
  vocabulary's own authors.
- **A third-party file is now a gate.** If a future change makes a vendor description fail for a
  new reason, a test says so and names it.

# Seams left open

- **One in four of their published examples does not parse.** `dht22.ttl`'s observation statement
  ends with `;` and never receives its `.`. The fixture is left exactly as published and the
  one-character repair lives in the test, self-invalidating: it asserts the fault is still there,
  so if W3C fixes it the test says to drop the patch. Whatever else "as-is" means, it has to
  tolerate files that are only approximately right.
- **The successor draft models a datasheet differently, and would change what our figures mean.**
  [`w3c/sdw-sosa-ssn`](https://github.com/w3c/sdw-sosa-ssn) redefines `ssn-system:Frequency` from
  *"the smallest possible time between one Observation and the next"* to *"the rate at which a
  system performs a function"* — **inverse quantities** — and re-models datasheet entries as
  `sosa:Observation` under a `sosa-cap:` namespace rather than as `SystemCapability` with
  properties. A floor of 2 seconds and a rate of 2 Hz are not the same claim, and nothing here
  would fail if the meaning flipped underneath. We build on the **2017 Recommendation**; that is a
  choice, and `IBS-TH2-PLUS.ttl` is deliberately not vendored because it is a warning rather than
  a fixture.
- **Nothing imports a description.** A vendor file has to be placed in a world by hand and its
  deployment half written beside it. What is missing is a command that reads a description and
  reports what it does and does not give you — the fifth generator this measurement argues for
  and does not build.
- **The overlay names their IRIs.** `deploy-dht22.ttl` states deployment facts against
  `http://example.org/data/DHT22/4578#…`, so the two files are joined by agreeing on an
  identifier. Nothing checks that the identifier a vendor chose is one this world meant.
