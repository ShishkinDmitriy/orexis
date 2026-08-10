---
type: Decision
title: Matching is the word, and auction format is not
description: Three words were in circulation for one concept — matching, rule and format — all three in hosting.py alone. Matching wins because it is accurate about what we model: allocation and prices, not how bidding proceeds. Format was rejected for over-claiming and for being ambiguous in the wild; rule for colliding with rules.ru. No identifier changed.
status: accepted
stage: v1
tags: [ubiquitous-language, auction, matching, documentation]
timestamp: 2026-08-10T00:00:00Z
---

# Context

The domain layer is where terms are defined, and everything else — code, ontology, conversation —
speaks them. That only works if there is one word per concept.

There were three. `agent/capabilities/matching/` implements one thing: turning a lot and a set of
bids into a proposed allocation with prices. It was called **matching** (the directory, the class
`ag:MatchingCapability`, the property `ag:matchesBy`, `propose_match`), **rule** (six places, in
newer comments and error messages), and **format** (seven places, from `auction.py`'s original
framing). All three appeared in `hosting.py` alone, and `ag:MatchingCapability`'s own
`rdfs:comment` managed two in one sentence: the class is a *"Matching capability"* whose text said
*"a host may ask for 'whoever matches' without knowing which **rule** answered."*

Nothing was wrong with the code. What was missing was a statement of which word won.

# Decision — matching, and no identifier changes

**Matching** is the term. `ag:MatchingCapability`, `ag:matchesBy`, `ag:PayAsBid`,
`ag:UniformPrice`, `capabilities/matching/`, `propose_match` and the `match` callable all stay
exactly as they are. The other two words were corrected to it, in comments, docstrings, shape
messages, test names and this bundle. **No behaviour changed and no identifier moved** — the whole
change is words.

`knowledge/domain/matching.md` now defines the term, and `knowledge/domain/auction.md` defines
the process it is a step of. Those two pages are the deliverable; this record is why they say what
they say.

## Why matching

It is **accurate about the width of what we model**. Matching covers who gets how much *and* what
each pays — both halves of the answer a member returns — and it stays true of a member that
allocates differently. A pro-rata member that fills everyone who cleared the reserve in proportion
to what they asked for is an ordinary answer and is still *matching*; that possibility is why the
allocation walk is written out twice rather than factored into a shared helper, and a term that
implied highest-first would have quietly contradicted that.

## Why not format

Two reasons, and the second is the stronger.

**It over-claims.** In the literature an *auction format* — equivalently *auction type* — names a
bidding procedure and a pricing rule together: Dutch is descending open outcry *with* first-price;
a first-price sealed-bid auction is one-shot sealed *with* first-price. We model the pricing axis
only. [round](/domain/round.md) describes an iterative-ascending round, which is a fact about the
bidding procedure and is fixed in the protocol rather than pluggable. Calling
`ag:MatchingCapability` a format would advertise a second slot that does not exist.

**It is ambiguous in the wild.** To an auction theorist a "Dutch auction" is the descending-price
open outcry. In finance the same phrase usually means close to the opposite — a sealed-bid
*uniform-price* auction; Google's IPO was described that way and was uniform-price sealed-bid, and
US Treasury auctions attract the same label. When a term of art means two incompatible things
depending on who is speaking, a project has to define its own narrowly and say what it is not.
That is the whole argument for `domain/matching.md` existing, and it is on the page.

## Why not rule

**`rule` already means something here.** Every capability directory has a `rules.ru` — the SPARQL
that derives capabilities and other conclusions into the derived graph. A sentence like *"the rule
is guarded on `ag:hosts`"* is about `rules.ru`; *"a host that states a rule nothing implements"*
was about pay-as-bid. Two meanings, one word, in the same package. That collision is most of why
this word drifted in and why it is the one that had to go.

Where a word for *one member of the family* was needed, the corrected prose says **member**, or
names it: pay-as-bid, uniform price.

## What was corrected, and what deliberately was not

- `ag:HostStatesItsRuleShape` → `ag:HostStatesHowItMatchesShape`. A shape IRI is prose that
  happens to be an identifier; it was carrying the rejected word.
- Comments, docstrings, `sh:message` texts, and four test names.
- The ontology's `rdfs:comment`s, including the two-axes scope note on `ag:MatchingCapability`,
  so the T-Box carries the boundary rather than only the bundle.
- `decisions/an-auction-format-is-a-capability.md` → `matching-is-a-capability.md`, retitled. A
  decision record is cited by name, and the most-cited record on this subject asserting the
  rejected term in its title is exactly the stale-record failure AGENTS.md warns about. Its
  argument is unchanged; only its words are.
- **`propose_match` and the `match` callable stay.** They agree with the term rather than sitting
  beside it. *Matching* is the noun for the ability; *match* is what a member does to a lot and a
  set of bids; the two are the same word in different parts of speech, which is what a ubiquitous
  language is supposed to produce.

# Consequences

- **A capability directory name is part of the language.** `agent.loader` finds packages by
  directory, so `capabilities/matching/` is not an implementation detail — it is the term, spelled
  once more. Keeping it meant this change touched no imports at all.
- **The scope boundary is now written down twice** — in `ag:MatchingCapability`'s comment and in
  `domain/matching.md`. Unstated scope is what a ubiquitous language exists to prevent, and *we do
  not model the bidding procedure* had never been said anywhere.
- **The gates are unmoved.** `agora-validate` on all three worlds, `pytest tests`, `lint-imports`
  and `./tools/validate-okf.sh knowledge` pass exactly as before, which is the evidence that this
  was a vocabulary change and not a refactor wearing one's clothes.

# Seams left open

- **The bidding procedure is not a family.** Naming the axis is not building a slot for it. If
  ascending, descending and sealed-bid ever become interchangeable here, that is a second family
  in `capabilities/market`, and Dutch would join *it* while still matching by pay-as-bid.
- **Nothing enforces the vocabulary.** `tests/test_store.py` scans source text for stray SPARQL
  prefixes; nothing comparable scans prose for a rejected word, and the drift this record fixes
  would recur silently. A grep in CI would catch it and would also be a new kind of gate; not
  attempted.
- **`ag:MatchingCapability` keeps the `<X>Capability` suffix** that `ag:PerceptionCapability` and
  `ag:ReviewCapability` follow. Under the term the class could as well be `ag:Matching`; the
  suffix is a live convention and breaking it for one family would cost more than it explains.
