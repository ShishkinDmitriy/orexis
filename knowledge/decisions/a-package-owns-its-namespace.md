---
type: Decision
title: A package owns its namespace, and a directory is a package rather than a capability
description: Every package has declared an owl:Ontology IRI of its own since there were packages, and then put its terms in someone else's namespace — because store.PREFIXES was a kernel constant, so a package wanting one had to edit the kernel to be nameable in SPARQL. The prefixes are now read off the ontologies that declare them, packages/orexis-capability-market took market:, and bid matching folded into it. Three latent bugs only became visible once a second namespace existed.
status: accepted
timestamp: 2026-08-10T00:00:00Z
---

> **Current statement: [package](/domain/package.md).** This record is how the model got
> there and why; the domain concept is what it is now. Four records amend each other on
> this subject, so read the concept first unless you want the argument.

# Context

Two things were true at once and should not have been.

**Every package already declared a namespace of its own.** `packages/orexis-capability-market/ontology.ttl` opens
`<http://example.org/orexis/market> a owl:Ontology`, and so does every other package — review,
sensing, actuation, the mqtt transport. The trees under `vocabulary/` went further and put their
*terms* there too: `mc:`, `onewire:`, `i2c:`, `probe:`, since
[pins-and-wires](pins-and-wires.md). So the convention existed, was in use, and was documented.

**And every capability put its terms in `orexis:` anyway.** `ag:Hosting`, `ag:matchesBy`,
`review:reviewIntervalS` — declared by a package, spelled as though the kernel owned them. An ontology
that declares an IRI and then defines nothing under it is an ontology in name only.

`agent/ontology.py` explained the split, and its explanation was the tell:

> The hardware layer keeps namespaces of its own … It can afford this **precisely because no
> runtime code names these terms**: an agent never queries a pin, so `term()` and
> `store.PREFIXES` are untouched.

True of the arrangement, false as a rule. The constraint was never that a namespace must go
unqueried. It was that **`store.PREFIXES` was a kernel constant** — the only set a query may use,
because rdflib pre-binds prefixes Fuseki does not and a query naming an undeclared one passes every
test and 400s in production. A package wanting a namespace had to edit the kernel to be nameable.

That is a registry, in the tree whose entire claim is that
[adding a package edits nothing](capability-packages.md).

# Decision — three of them, and the first is what made the others possible

## The prefixes are read, not registered

`agent.loader.prefixes()` scans every package's `ontology.ttl` for `@prefix` lines under this
project's base and returns the label-to-IRI map. `store.PREFIXES` composes that with the external
vocabularies it keeps. Nothing is listed, and adding a package with a namespace of its own is still
adding a directory.

**Read rather than imported, and that is forced.** Half the capabilities import `orexis_agent_progression.store`, so a
store that imported them back would close the loop. Reading Turtle text needs no import and runs
before any capability's Python.

**The kernel's own external vocabularies stay in the kernel, and the rest are discovered.**
`rdf:`, `rdfs:`, `owl:`, `xsd:`, `sh:`, `prov:` are standardised, stable, and the language the
kernel's own structure is written in; a package that could rebind `rdfs:` could make
`rdfs:subClassOf` mean what it liked — the walk
[one-graph-both-engines-read](one-graph-both-engines-read.md) materialises and every shape leans
on. Every other external vocabulary — `sosa:`, `ssn-system:`, `unit:`, `schema:`, `dcterms:` — is
READ off whichever ontology declares it, exactly as a package's own namespace is, since
[the-stake-is-sensings-want](the-stake-is-sensings-want.md)'s third step: the kernel speaks no
reading, so it does not declare the vocabulary readings are written in. What the old "not a
package's to bind" argument needed is the loader's refusal of one label bound to two IRIs, and
that holds without the kernel naming the vocabulary. (This said `sosa:` was the kernel's; it was,
while the kernel derived the stake.) `orexis:` is read the same way, off the ontology that declares
it, and hard-coding it would have made it an exception for no reason but habit.

**AMENDED in one word.** This said `orexis:` arrives "like any other package's, because the base
vocabulary is a package". It is not one any more — it is the kernel, `agent/ontology.ttl`, not
discovered but prepended. The mechanism is untouched and is the part that mattered: the prefix is
read from the ontology rather than registered anywhere, so nothing here changed but the file's
address.

**A label bound to two namespaces is refused.** It is the quietest bug available — both spellings
are valid SPARQL, so one package's query would read another's terms and no engine could tell
anyone.

## A directory is a package, and `packages/orexis-capability-market/` holds three capabilities

AGENTS.md rule 2 said *"a capability … is a directory"*. That was already false when it was
written: `packages/orexis-capability-market/` provided `ag:Bidding` and `ag:Hosting`, which are not
interchangeable members of one family but two different abilities. The rule conflated two axes and
hid the one that matters.

**What isolates a capability is `PROVIDES` and its term, never the directory boundary.** So bid
matching moved into `packages/orexis-capability-market/` — `matching.py`, plus its share of the package's
ontology, shapes and rules — and the family is unchanged. `hosting.py` still asks
`agent.provider(BID_MATCHING)` and still never learns which member answered.

**The claim #66 proved needs restating, not withdrawing.**
[uniform-price-dissolves-the-uncontested-round](uniform-price-dissolves-the-uncontested-round.md)
demonstrated that a second member landed without `hosting.py` moving. That was `PROVIDES` doing the
work, not the directory: the module registers a term, the protocol asks for a family, and neither
knows where the other's Python sits. Folding removes nothing from that argument.

**What it does cost is deletion.** Removing the matching family used to be `rm -r` on a directory;
it is now an edit to a shared `ontology.ttl`, `shapes.ttl` and `rules.ru`. That is the real price
and it is worth naming: a directory is how a package is *found* and how one is *deleted*.

In exchange the cross-package reference goes. `market/terms.py` had to re-declare the family term
to ask for it, and under a namespace split would have had to re-declare the namespace IRI beside
it — one string in two files, with nothing to catch drift.

## `packages/orexis-capability-market/` takes `market:`

Nineteen terms and five shapes. The line is **who declares the term**:

| stays `orexis:` | why |
|---|---|
| `orexis:Agent`, `orexis:Capability`, `orexis:hasCapability`, `orexis:localId` | the kernel's — true of every agent |
| `water:hasTarget`, `water:bandLow`, `water:maxValuePerL` | `packages/orexis-plant-water`'s — what a bid is *worth* here |
| `mqtt:eventTopic`, `mqtt:readingTopic` | the mqtt transport's |

A bidder's belief block now reads from two namespaces at once, and that is the split stated rather
than implied: the wallet is the protocol's (`market:hasEndowment` — what it brought to the venue),
everything under it is the domain's answer to what water is worth to a plant.

Only market converted. The other packages could, and the criterion for when it is worth it is
below — **superseded**: all five converted in
[every-term-in-its-own-house](every-term-in-its-own-house.md), and the reasoning below turned
out to weigh the wrong thing.

# Three couplings that were bugs, not costs

Each was invisible while every term shared one namespace, and each is a real defect that a second
namespace merely exposed.

**A belief block mapped a field to a bare local name** and `agent/beliefs.py` wrapped `orexis:` around
it. So the kernel decided where every capability's beliefs lived, and a package could not carry a
belief of its own at all. Blocks now hold full IRIs, built by each package with its own `term()`,
and the reader learns nothing about where any of them live.

**Sensing matched a revised belief by stripping the namespace off** and comparing local names:
`belief_term.rsplit("#", 1)[-1] not in SUBSCRIBING_BLOCK.terms.values()`. Two packages may each
declare a `slowSleepS`, and the stripped form cannot tell them apart — so a revision of someone
else's belief would have been taken up as this module's. Compared whole now.

**`onboarding/mqtt.py` derives the broker ACL from `bidsIn` and `hosts`.** A missed rename there
un-grants every market topic and nothing fails: the generators are not run by either gate, which is
exactly how [PR #62](https://github.com/ShishkinDmitriy/orexis/pull/62) shipped a live regression in
the supplier's signing keys. So the grants and the compose files were regenerated and diffed rather
than assumed.

# Consequences

- **`tests/test_layout.py` holds `NS` to the namespace its own `ontology.ttl` declares.** They are
  two copies of one fact — Python needs one without parsing Turtle, SHACL needs the other — and
  drifting them apart fails in the worst available way: a world would conform while the agent
  reading it found nothing, because an empty result is not an error. Proved by drifting it.
- **`store.PREFIXES` grew the hardware prefixes** as a side effect, so a query *may* now name
  `mc:` or `onewire:`. Nothing does. The point is that it would work rather than 400.
- **A world author sees which package owns a term.** `world.ttl` reads `ag:hosts`… no longer: it
  reads `market:hosts` beside `orexis:localId`, and the prefix says where to look. Noisier to write and
  self-documenting to read.
- **`agent/world.py` still names market terms.** It queries `market:bidsIn` and `market:marketFor`
  to load an agent's own view of itself. That the kernel knows what a market is predates this
  change and is untouched by it; the namespace makes it visible rather than introducing it.

# Seams left open

- ~~**The other four packages have not converted.**~~ **Closed, and the criterion was wrong.**
  This said the benefit was legibility where a sovereign reads a world file, so packages writing
  their terms into SPARQL text heavily would be "the same size of change for less benefit". Both
  halves missed the point. The size was not in the SPARQL text at all — that form is the one a
  rename can see — it was in the six forms that name a term some other way and fail silently. And
  the benefit was not legibility but a bounded kernel: the kernel vocabulary (`agent/ontology.py`
  then, `packages/orexis-agent-progression/ontology.py` since #452) claims everything in it
  is true of every agent, and 102 terms were making that false. See
  [every-term-in-its-own-house](every-term-in-its-own-house.md).
- ~~**`vocabulary/` packages ship no Python**, so they have no `terms.py` to hold an `NS` and
  their namespaces stay as constants in `agent/ontology.py`.~~ Closed: nothing in the kernel
  ever read those constants — only the sovereign's generators — so they are
  `onboarding/namespaces.py`'s now, where they are consumed, and the kernel names no package's
  namespace at all. A knowledge-only part still has no `terms.py`, and needs none.
- **Nothing stops a package declaring terms in another's namespace.** The loader would find the
  prefix and every gate would pass; only a reader would notice. A shape could check that each
  package's `ontology.ttl` defines only terms under its own base, and would need an exception for
  the several packages that legitimately do not have one.
- **The kernel still decides that `orexis:` is what a package gets by default.** `orexis_agent_progression.ontology.term()`
  builds into `AG`, so a package that declares no `NS` silently inherits the kernel's namespace
  rather than being asked to choose. That is the state four packages are in.
