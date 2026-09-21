---
type: Decision
title: There is no BDI ontology, and the mind does not need one
status: superseded-in-part
superseded-by: the-future-is-a-cone-and-the-present-is-identified-in-it
timestamp: 2026-08-22T00:00:00Z
description: >-
  The survey settlement-speaks-rea ran for the market, run for the mind. Nobody owns Belief,
  Desire or Intention the way SOSA owns observation — FIPA SL is the only standard-shaped
  artifact and it is frame-based modal logic, not RDF, dormant since the early 2000s. Four
  adjacent vocabularies were examined and refused: DOLCE Ultralite (an upper-ontology
  commitment for four words), prov:Plan (already bound and vendored, and still wrong — our
  plan is required to be lost, never an entity an activity cites), WoT Thing Description (its
  affordance is an authored interface contract where ours is a derived conclusion), and hmas
  (research-grade, and about workspaces rather than mental states). The deeper reason no
  import is wanted: external vocabulary pays where data crosses a trust boundary, and a mind
  never does — belief-base isolation is structural. BDI's WORDS are already ours; only the
  IRIs are home-made, and IRIs matter only to consumers, of which the design guarantees there
  are none.
---

> **Superseded in part** by
> [the-future-is-a-cone-and-the-present-is-identified-in-it](/decisions/the-future-is-a-cone-and-the-present-is-identified-in-it.md)
> (2026-09-06), in one premise only: "our plan is required to be lost" narrows to *a plan the
> world has moved away from is lost*; a plan whose worlds the present still matches is kept and
> re-rooted. The conclusion stands untouched — no import, because a mind crosses no trust
> boundary — and nothing in the cone makes a plan an entity anything cites.

# Context

[settlement-speaks-rea](settlement-speaks-rea.md) set the method: where a standard already has
the words, check ours against it, borrow the words, state the deviations, and import no IRIs
that nothing consumes. It found no canonical auction ontology and a very good accounting one.
After [the-dictionary-names-its-terms](the-dictionary-names-its-terms.md) made term-binding a
gate, the sovereign asked the same question of the mind: is the BDI layer — `progression:Intention`,
the desire shapes, the deliberation modes, the modality graphs — reinventing something a
standard owns?

# Finding — nobody owns the B, the D or the I

There is **no canonical BDI ontology**, in the same sense there was no auction one: nobody
owns `Belief` the way SOSA owns observation or PROV owns provenance.

**FIPA SL** is the only artifact that was ever a *standard* for BDI content — its semantic
language carries belief, uncertainty and intention modalities (FIPA00008), and it is the
closest thing to an official vocabulary the field produced. It is frame-based modal logic for
agent communication, not RDF; there is no OWL artifact to import; and FIPA has been dormant
since IEEE absorbed it in the early 2000s. At most it is a words-check target, and our words
already pass it: *belief*, *desire*, *intention* and *deliberation* here are the literature's
words (Bratman; Rao–Georgeff), used in the literature's senses —
[an-intention-is-an-amortised-deliberation](an-intention-is-an-amortised-deliberation.md) is
explicit that an intention is BDI's third letter.

# The adjacent four, examined and refused

| candidate | what it offers | why refused |
|---|---|---|
| **DOLCE Ultralite** (`DUL.owl#`) | `Goal`, `Plan`, `Task`, `Situation` — the closest maintained ontology with intentional concepts | an upper-ontology commitment: every class wants a place in its hierarchy, and the hand-materialised closure ([one-graph-both-engines-read](one-graph-both-engines-read.md)) would have to cover its axioms — the cost settlement-speaks-rea refused for ValueFlows, paid for four words |
| **prov:Plan** (+ p-plan) | already **bound and vendored** here — the one candidate a `term:` could name today | see below — the sharpest refusal, because it is the only one that was actually available |
| **WoT Thing Description** (`2019/wot/td#`) | `ActionAffordance`, `PropertyAffordance` — the one place our word and a W3C Recommendation's word coincide | same Gibson word, different kind of fact — see below |
| **hmas** (`purl.org/hmas/`) | agents, artifacts, workspaces, signifiers — the hypermedia-MAS research line | research-grade and evolving, not a standard; and it models an agent's *situation* (where it is, what artifacts it can reach), not its mental states — the part of the mind it covers is the part our world graph already is |

(Jason, JaCaMo and the other BDI *implementations* ship no RDF vocabulary at all, which is
itself evidence for the finding.)

## prov:Plan — available, vendored, and still wrong

PROV is spoken here and its vocabulary sits in `tests/fixtures/vocabularies/prov.ttl`, so
`prov:Plan` is the one candidate a domain page could bind this afternoon. It must not:

- **PROV's plan is an entity because it persists** — its own comment says plans are entities
  *"since plans may evolve over time, it may become necessary to track their provenance"*, and
  it exists to be cited by `prov:hadPlan` from an activity that followed it. Our plan is the
  opposite fact: a path of graph diffs searched inside the [imaginarium](../domain/imaginarium.md),
  the one thing in this design **required to be lost**. Nothing ever cites a plan, because by
  the time anything has happened the plan is gone and what remains is an intention.
- **PROV declines to say what a plan is made of** — *"there exist no prescriptive requirement
  on the nature of plans, their representation, the actions or steps they consist of"* — so the
  import would buy no structure, only a claim of persistence we specifically refuse.

This is the same verdict `review`'s ontology already recorded against `prov:wasRevisionOf`: a
reader who knows PROV would be **wrong about this data**, which is the test.

## td:ActionAffordance — the same word for a different kind of fact

The words-check the audit asked for. WoT TD and this project both took *affordance* from
Gibson, and mean the same idea by it — what could be done here. The modelling is opposite:

- a TD affordance is **authored** — a Thing's interface contract, written in its description,
  stable until re-described;
- a [step](../domain/step.md) a world affords is **derived and never stored** — a conclusion
  recomputed on every ask, precisely so that a row can never outlive the plumbing it was
  concluded from. A stored affordance is the failure mode our page warns against, and it is
  TD's normal case, because a device's interface genuinely is stable in a way an agent's
  options are not.

So: alignment of *word* (kept, and pleasant — both sides read each other correctly in prose),
refusal of *terms*. `td:ActionAffordance` on our menu rows would claim they are declared
interface, which is the one thing they must never be.

# The deeper reason — the mind has no interop surface, on purpose

External vocabulary pays where data crosses a trust boundary: SOSA at the sensing edge, PROV
for who-put-the-fact-there, REA's words at settlement. A mind never crosses one.
[where-the-belief-base-lives](where-the-belief-base-lives.md) makes isolation structural — no
external consumer ever reads a `DesireGraph`, and [the-sovereign-may-ask](the-sovereign-may-ask.md)
returns answers, not graphs. An interop vocabulary for data with no interop surface buys the
closure cost and the alignment risk for nothing.

And the semantics deviate on purpose. A desire here is a SHACL shape
([a-desire-is-a-shape](a-desire-is-a-shape.md)); an intention is an amortised deliberation
kept in a private ledger; deliberation is a capability with interchangeable members, one of
them an LLM consulted at the edge of knowledge. A borrowed mental-state ontology would claim
Rao–Georgeff operator semantics the design deliberately does not keep. Home-made IRIs are not
a compromise waiting for a standard; they are the honest statement that nothing outside this
process is meant to interpret them.

# Seams left open

- **WoT TD for device descriptions is a real candidate** — not for minds. A board's MQTT
  interface is exactly what TD describes (forms, protocol bindings, authored stability), and
  [a-firmware-describes-itself](a-firmware-describes-itself.md) already treats the flashed
  image as a T-Box source. The day a board's description must interop beyond this repo, TD is
  the vocabulary to check first, on the [their-descriptions-are-our-fixtures](their-descriptions-are-our-fixtures.md)
  pattern.
- **FIPA ACL performatives, the day the conversation is formalised.** Agents already exchange
  offers, bids and justifications; if that protocol ever grows message *types*, the
  words-check runs against FIPA's performative vocabulary before any word is invented.

# When to revisit

The trigger is an interop surface appearing: an agent's mental state read by anything that is
not the agent, or a device description consumed by anything that is not this repo's tooling.
Until one exists, a BDI import has no consumer, and this record is the answer to "should we
borrow a BDI ontology?" — asked once, likely to be asked again.
