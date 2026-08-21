---
type: Decision
title: Bid matching is the word, and auction format is not
description: Three words were in circulation for one concept — matching, rule and format — all three in hosting.py alone. Matching wins on width: it covers the allocation rule and the payment rule, not how bidding proceeds. Format over-claims and is ambiguous in the wild; rule collides with rules.ru. The qualifier is load-bearing, because bare matching collides with matching a capability to a provider — which is what this project does everywhere else.
status: accepted
stage: v1
tags: [ubiquitous-language, auction, matching, documentation]
timestamp: 2026-08-10T00:00:00Z
---

# Context

The domain layer is where terms are defined, and everything else — code, ontology, conversation —
speaks them. That only works if there is one word per concept.

There were three. One thing was implemented — turning a lot and a set of bids into a proposed
allocation with prices, then its own package and now `packages/capability/market/matching.py`. It was called **matching** (the directory, the
class, the property `market:matchesBy`, `propose_match`), **rule** (six places, in newer comments and
error messages), and **format** (seven places, from `auction.py`'s original framing). All three
appeared in `hosting.py` alone, and the family class's own `rdfs:comment` managed two in one
sentence: the class was a *"Matching capability"* whose text said *"a host may ask for 'whoever
matches' without knowing which **rule** answered."*

Nothing was wrong with the code. What was missing was a statement of which word won.

# Decision — bid matching

**Bid matching** is the term. The other two words were corrected to it, in comments, docstrings,
shape messages, test names and this bundle. `knowledge/domain/bid-matching.md` defines it and
`knowledge/domain/auction.md` defines the process it is a step of; those two pages are the
deliverable, and this record is why they say what they say.

The identifiers that carry the family name moved with it: `market:BidMatchingCapability`, the
directory, and the `BID_MATCHING` constant. (The directory was `capabilities/bid_matching/` when
this was written and is now `packages/capability/market/`, which also took the namespace — see
[a-package-owns-its-namespace](a-package-owns-its-namespace.md).) **`market:matchesBy` did not**, and neither did `propose_match`, the `Match` callable or
`market:HostStatesHowItMatchesShape` — see below. No behaviour changed.

## Why the qualifier — the collision is inside this repository

The first version of this record chose bare *matching*, on the strength of market microstructure,
where a **matching engine** is exactly the component that pairs orders and sets execution prices.
That reasoning holds and is why the root word survives. What it failed to check was the word
against **this codebase**, and that is where it breaks.

**Matching a capability to a provider is what this project does everywhere.**
`agent.provider(family)` matches a request for an ability to whichever module registered a member
of it — the central move of [capability-packages](capability-packages.md), performed by every
package. So `ag:MatchingCapability` parses two ways: *the capability of matching*, which was meant,
and *matching, of capabilities*, which is a different and equally real thing here. The class name
sat exactly on the ambiguity, and a reader hitting it had no way to tell which was intended.

*Bid matching* removes it. **Order matching** is the standard phrase and bids are our orders — the
host posts one lot and bidders answer, so there is no two-sided book to have orders in — which
makes the qualifier the ordinary construction rather than a coinage. It is also the cheapest
possible fix: every argument below is about the root word and survives untouched.

The general lesson is worth more than the rename. **A term of art is only clear relative to the
vocabulary it lands in.** Checking a candidate against the literature is half the work; the other
half is checking it against the words the codebase already uses heavily, and this record did the
first and skipped the second.

## Why matching

It is **accurate about the width of what we model**, and the width has a standard name. Mechanism
design decomposes a mechanism into an **allocation rule** (who gets what) and a **payment rule**
(what each winner pays); a member of this family supplies both, so the family is not a pricing slot
and no word implying one would do.

That decomposition also says what varies. `market:PayAsBid` and `market:UniformPrice` share an allocation
rule and differ in their payment rule — which is a property of *those two members* and not of the
family. A pro-rata member that fills everyone who cleared the reserve in proportion to what they
asked for varies the allocation rule instead, is an ordinary answer, and is still *matching*; that
possibility is why the allocation walk is written out twice rather than factored into a shared
helper, and a term that implied highest-first would have quietly contradicted it.

The bundle says **payment rule** and not *pricing rule*, which the auction literature uses for the
same axis. Both are current; one word per concept is the point of this record, and *payment rule*
is the half of a pair whose other half we also need.

## Why not format

Two reasons, and the second is the stronger.

**It over-claims.** In the literature an *auction format* — equivalently *auction type* — names a
bidding procedure and a payment rule together: Dutch is descending open outcry *with* first-price;
a first-price sealed-bid auction is one-shot sealed *with* first-price. We model the
allocation-and-payment half only. [round](/domain/round.md) describes an iterative-ascending round, which is a fact about the
bidding procedure and is fixed in the protocol rather than pluggable. Calling
`market:BidMatchingCapability` a format would advertise a second slot that does not exist.

**It is ambiguous in the wild.** To an auction theorist a "Dutch auction" is the descending-price
open outcry. In finance the same phrase usually means close to the opposite — a sealed-bid
*uniform-price* auction; Google's IPO was described that way and was uniform-price sealed-bid, and
US Treasury auctions attract the same label. When a term of art means two incompatible things
depending on who is speaking, a project has to define its own narrowly and say what it is not.
That is the whole argument for `domain/bid-matching.md` existing, and it is on the page.

## Why not rule

**`rule` already means something here.** Every capability directory has a `rules.ru` — the SPARQL
that derives capabilities and other conclusions into the derived graph. A sentence like *"the rule
is guarded on `market:hosts`"* is about `rules.ru`; *"a host that states a rule nothing implements"*
was about pay-as-bid. Two meanings, one word, in the same package. That collision is most of why
this word drifted in and why it is the one that had to go.

Where a word for *one member of the family* was needed, the corrected prose says **member**, or
names it: pay-as-bid, uniform price.

## What was corrected, and what deliberately was not

- `ag:HostStatesItsRuleShape` → `market:HostStatesHowItMatchesShape`. A shape IRI is prose that
  happens to be an identifier; it was carrying the rejected word.
- Comments, docstrings, `sh:message` texts, and four test names.
- The ontology's `rdfs:comment`s, including the two-axes scope note on `market:BidMatchingCapability`,
  so the T-Box carries the boundary rather than only the bundle.
- `decisions/an-auction-format-is-a-capability.md` → `bid-matching-is-a-capability.md`, retitled. A
  decision record is cited by name, and the most-cited record on this subject asserting the
  rejected term in its title is exactly the stale-record failure AGENTS.md warns about. Its
  argument is unchanged; only its words are.
- **`propose_match` and the `match` callable stay**, and so does `market:matchesBy`. They agree with
  the term rather than sitting beside it. *Bid matching* is the noun for the ability; *match* is
  what a member does to a lot and a set of bids; the two are the same word in different parts of
  speech, which is what a ubiquitous language is supposed to produce. **The qualifier is not
  carried where nothing could be misread**: `market:matchesBy` has a host for its domain and the family
  for its range, so *supplier matchesBy PayAsBid* admits one reading, and `ag:matchesBidsBy` would
  be noise. A qualifier exists to remove an ambiguity, not to be spelled consistently.
- `market:HostStatesHowItMatchesShape` stays, for the same reason.

# Consequences

- **A package directory name is part of the language.** `agent.loader` finds packages by
  directory, so the name is not an implementation detail. That is why renaming the term meant
  moving the directory and touching every import of it, where the earlier draft of this change had
  touched none. What the directory does NOT name is a capability: it named this one only while
  this one had a package to itself, and [a-package-owns-its-namespace](a-package-owns-its-namespace.md)
  folded it into `packages/capability/market/` shortly afterwards. The term is what survived.
- **The scope boundary is now written down twice** — in `market:BidMatchingCapability`'s comment and in
  `domain/bid-matching.md`. Unstated scope is what a ubiquitous language exists to prevent, and *we
  do not model the bidding procedure* had never been said anywhere.
- **The gates are unmoved.** `agora-validate` on all three worlds, `pytest tests`, `lint-imports`
  and `./tools/validate-okf.sh knowledge` pass exactly as before, which is the evidence that this
  was a vocabulary change and not a refactor wearing one's clothes.

# Seams left open

- **The bidding procedure is not a family.** Naming the axis is not building a slot for it. If
  ascending, descending and sealed-bid ever become interchangeable here, that is a second family
  in `packages/capability/market`, and Dutch would join *it* while still matching by pay-as-bid.
- **Nothing enforces the vocabulary.** `tests/test_store.py` scans source text for stray SPARQL
  prefixes; nothing comparable scans prose for a rejected word, and the drift this record fixes
  would recur silently. A grep in CI would catch it and would also be a new kind of gate; not
  attempted.
- **`market:BidMatchingCapability` keeps the `<X>Capability` suffix** that `sensing:SensingCapability` and
  `review:ReviewCapability` follow. Under the term the class could as well be `ag:BidMatching`, which
  already reads as an ability without help; the suffix is a live convention, and dropping it for
  one family is really a proposal to drop it for all three. Worth deciding deliberately, not as a
  side effect of a rename.
- **Nothing checks a candidate term against the codebase's own vocabulary.** That omission is what
  made this record need amending within a day of being written. A grep for a proposed word across
  `agent/` would have surfaced `provider(family)` immediately; nothing prompts anyone to run it.
