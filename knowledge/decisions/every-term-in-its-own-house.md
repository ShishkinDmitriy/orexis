---
type: Decision
title: A term is named seven ways, and a rename sees one of them
description: The five packages still declaring into ag: took namespaces of their own, finishing a correction begun when review's terms left the kernel file but kept the kernel's name. The sweep's finding is bigger than the move: a term is named seven different ways here, six of them survive a rename by matching nothing, and one had been doing so undetected for four merged PRs. There is now a test for it. The audit half found no standard worth adopting that we had not already taken.
status: accepted
stage: v1
tags: [vocabulary, namespaces, ubiquitous-language, reuse, testing]
timestamp: 2026-08-11T00:00:00Z
---

# Context

[a-package-owns-its-namespace](a-package-owns-its-namespace.md) gave `capabilities/market` a
namespace of its own and made `store.PREFIXES` assembled from each package's `ontology.ttl`, so
the kernel no longer had to be edited for a package to be nameable in SPARQL. That removed the
only reason the rest were still `ag:`. Five packages stayed anyway — 102 terms across
`review`, `sensing`, `water`, `mqtt` and `actuation`.

`agent/ontology.py` opens by saying everything in the kernel is true of *every* capability.
That has been false the whole time, and
[self-review-is-a-capability](self-review-is-a-capability.md) already found it: ~24 of the
kernel's terms belonged to self-review. It moved the **file** into `capabilities/review/` and
left the **name** behind, so `ag:` went on claiming universality for summaries, revisions and
mandates that only an agent with room to move holds. This is the other half of that.

# Decision — five namespaces, and the kernel means what it says

`review:`, `sensing:`, `water:`, `mqtt:` and `actuation:`, each at
`http://example.org/agora/<name>#`. Nothing else changed: **grants byte-identical across all
three worlds, compose and firmware regenerate unchanged**, and the six comment lines that do
move are the compose generator naming the sense modes in its own output.

`packages/plant/water` is the one that matters beyond tidiness. AGENTS.md opens by saying the v1
domain is plant watering and that the domain is a plug-in — *"plant/water language is the
example, not the architecture"* — and its terms were `ag:SoilMoisture`, `ag:bandLow`,
`ag:hasTarget`, indistinguishable by inspection from what every agent has. Swapping the domain
is swapping a namespace now, which is what the sentence was promising.

# A term is named seven ways

This is the finding, and it is worth more than the move. Only the first is what a text rename
sees:

| | form | where |
|---|---|---|
| 1 | `sensing:polls` | SPARQL text, Turtle |
| 2 | `<http://example.org/agora#statusTopic>` | hardcoded in a `sh:sparql` |
| 3 | `"http://example.org/agora#SoilMoisture"` | a Python string constant |
| 4 | `<{AG}readingTopic>` | interpolated in the sovereign's tooling |
| 5 | `AG + "Sensor"` | concatenated |
| 6 | `term("slowSleepS")` | the kernel builder, imported into a package or a test |
| 7 | `ontology.term("hasTarget")` | one package reaching for another's term |

**Six of them fail silently.** An IRI no ontology declares is not an error in SPARQL — it is a
pattern that matches nothing, and a query returns fewer rows rather than raising. Four bit
during this sweep: `agora-firmware` stopped finding a board, a simulated actuator stopped being
asked for its status topic, a won claim stopped opening a valve, and the supplier stopped
being mounted its signing keys.

## One had been failing since PR #72

`tests/test_isolation.py` built `bidsIn` and `claimTopic` from the kernel namespace. Market
took `market:` four merged PRs ago, so that query has matched **nothing** ever since, and the
claim half of a privacy test asserted nothing while passing. Measured: three rows now, zero
before.

Its own subject guard — `assert private, "…the test proves nothing"` — did not fire, because a
second query kept the dict non-empty. **A subject guard is only as good as the narrowest thing
it guards**, and that is the transferable lesson: the guard proved *some* channel was being
protected, not that both kinds were.

## So there is a test for it now

`tests/test_store.py::test_no_source_names_a_moved_term_in_the_kernel_namespace` scans every
source tree for a full IRI in `ag:` whose local name `packages/core/agora` does not declare. It is
the same shape as the prefix scan beside it, and for the same reason: the harness was more
forgiving than the store, so the class could not be caught by testing behaviour.

Instances are exempt and that is why it is a *name* check rather than a ban —
`ag:moisture_sensor_fern` was a thing in a world, not a term in a vocabulary. Since the worlds
took their individuals into namespaces of their own, no world FILE puts an instance in `ag:`
any more (a test refuses one that does) — but the exemption stays, because runtime-minted
nodes (`ag:obs_…`) and synthetic test fixtures still do, legitimately. The heuristic is that a term is Capitalised or camelCase and an instance is a single
lowercase word or carries an underscore. Verified by reintroducing the real defect: it fails on
`bidsIn`, naming the file.

## And a form the sweep created

Adding an `ACTUATION` namespace constant to `onboarding/compose.py` shadowed a module-level
`ACTUATION = AG + "Actuation"` already there, so every `<{ACTUATION}actuates>` expanded to
`…agora#Actuationactuates`. Those patterns sit in `OPTIONAL` clauses, so the query still
returned rows; the capability test silently stopped being true, and a supplier that cannot
co-sign a trade was one regenerate away from shipping — with `pytest` and `agora-validate` both
green.

**Only regenerating the generators' output caught it.** That is the argument for treating
generated artefacts as a gate rather than a by-product, which is the lesson
[#62](https://github.com/ShishkinDmitriy/agora/pull/62) taught and the reason this sweep
regenerated at all.

# The audit half: what a standard already says

Nothing was adopted, because nothing was a pure synonym we had not already taken. Recorded so
the next person does not re-derive it:

| ours | standard | verdict |
|---|---|---|
| `sensing:Sensor` | `sosa:Sensor` | already `rdfs:subClassOf` it, and an **intersection** with `ag:Device` rather than a synonym — keep |
| `actuation:Actuator` | `sosa:Actuator` | the same alignment, and it is **not** declared. An asymmetry: we aligned Sensor and not Actuator |
| `sensing:monitors` | — | SOSA puts feature-of-interest on the **Observation**, not the Sensor. Nothing to defer to |
| `sensing:senseMode` values | `sosa:Procedure` | Pull, Push and Scheduled are procedures by SOSA's own definition. A cheap alignment, untaken — it belongs with whatever next touches [who-holds-the-clock](who-holds-the-clock.md) |
| `review:Revision`, `fromValue`, `atTime` | `prov:wasRevisionOf`, `prov:atTime` | PROV models a revision as provenance. Real overlap, not a synonym, and unexamined |
| `review:Commitment` | `vf:Commitment` | **a name collision, not an alignment.** Ours is a governance mandate — the room an agent may move in. REA's is a promised economic flow. Same word, different concept |
| `actuation:mlPerSecond`, `maxDoseMl` | `ssn-system:ActuationRange` | [#84](https://github.com/ShishkinDmitriy/agora/issues/84) |
| the wire — topics, codec, channel, principal | — | ours by decision; the SSN spec has no guidance on transmission |

# What is still in the kernel and should not be

Answering the question this sweep was supposed to answer. `packages/core/agora` declares 34 terms
and **eleven are not true of every agent**:

- **The simulated device model — seven terms** *(eleven since the scenario grew: the physics
  went time-based and the weather arrived)*. `ag:DeviceModel`, `ag:simulatedBy`,
  `ag:modelDriesPerDay` (was `modelDryRate`, per tick — the tick made drying an artifact of how
  often anyone looked), `ag:modelDailySwing`, `ag:modelInitialValue`, `ag:modelMaxValue`,
  `ag:modelMinValue`, `ag:modelTickSeconds`, plus the world-scenario three: `ag:timeScale`,
  `ag:strayDoseMeanDays`, `ag:rainTopic`. Used by `world/simulation` and no other world. They
  want a simulation package that does not exist — and the drying term is water-domain besides,
  since only a plant dries. The case for that package strengthens as this list grows.
- **Deployment — three terms.** `ag:ComputeHost`, `ag:runsOn`, `ag:lanHost`, used by
  `world/sensing` alone. Every agent runs somewhere, so these are closer to universal; what is
  not universal is stating *where*.
- ~~**`ag:SelfReporting`**~~ — **settled, and the question turned out to be malformed.** It was
  declared `rdfs:subClassOf ag:Capability`, had a shape, and appeared in no world. The reasoning
  above assumed *a capability is what only some agents have*, which conflates two questions:
  rule 2 asks whether the HOW could differ, not who holds it. It is a package now,
  `capabilities/reporting/`, granted to every agent by a rule and insisted on by a shape. See
  [telemetry-is-a-mandatory-capability](telemetry-is-a-mandatory-capability.md).

Moving the remaining ten was out of scope: the seven need a package to exist, and the deployment
three need someone to decide whether stating *where* an agent runs belongs in a world at all.

# Consequences

- **`agent/ontology.py` still overstates itself**, by eleven terms rather than a hundred and
  two. Its docstring now says which, so the claim is bounded rather than aspirational.
- **A package's `terms.py` is the one place its namespace is written.** Two `beliefs.py`
  modules picked up a private copy during the conversion and now import it;
  `tests/test_layout.py` only holds the pair it knows about, so a second copy is a silent
  divergence.
- **Namespace constants for cross-tree references** sit in `agent/ontology.py` beside the
  hardware ones. They are not a prefix registry — the loader still reads those off each
  ontology — but they are the list of namespaces one tree names in another's terms, and it
  should stay short.

# Seams left open

- **The eleven kernel terms above.** Two need a decision first, not a rename.
- **`sosa:Actuator` is not aligned** where `sosa:Sensor` is. One triple, and nobody has asked
  for it.
- **The guard is a heuristic about names.** A term that is a single lowercase word — were
  anyone to declare one — would be taken for an instance and skipped. The message says so.
- **Nothing checks the other five forms in Turtle.** The scan reads Python trees and the
  hardcoded-IRI form appears in `shapes.ttl` too; a `sh:sparql` naming a moved term would not be
  caught by this test, only by a world failing to validate.
