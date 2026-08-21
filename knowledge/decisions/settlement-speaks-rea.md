---
type: Decision
title: A claim is a commitment, not a claim, and REA already had both words
description: The settlement half is aligned to the REA accounting ontology through its RDF form, ValueFlows — offer and bid are intents, the trade is an agreement, the claim is a commitment and actuation is the event that fulfils it. The words are borrowed and the IRIs are not, because a hand-materialised RDFS closure has to cover every axiom it imports. Naming the one REA term we have no use for says something true about the design.
status: accepted
timestamp: 2026-08-10T00:00:00Z
---

# Context

Two vocabulary passes in a row found this project using a word two ways
([bid-matching-is-the-word](bid-matching-is-the-word.md),
[a-round-is-an-iteration-not-the-auction](a-round-is-an-iteration-not-the-auction.md)), and both
were found by a reader rather than by a gate. The obvious next move is to stop inventing terms
where a standard already has one, and check the ones we have against it.

There is **no canonical auction ontology** — nobody owns `Auction` the way SOSA owns observation
or PROV owns provenance. What exists is four adjacent families: e-commerce offer vocabularies
(GoodRelations, absorbed into schema.org), finance (FIBO), agent interaction protocols (FIPA), and
accounting (REA). None of them models matching or clearing, which is the part it would be most
useful to borrow.

But the **settlement half** — offer, bid, trade, claim, actuation, debit — is ordinary economic
exchange, and that is exactly what REA has modelled since McCarthy's work and what
**ISO/IEC 15944-4:2015** standardised as the Open-edi accounting and economic ontology. Its
modern RDF form is **ValueFlows** (`vf:`, `https://w3id.org/valueflows/ont/vf#`).

# Decision — borrow the words, not the IRIs

The bundle uses REA's terms where they fit, and cites ValueFlows for their definitions. **Nothing
imports `vf:` and no `world.ttl` gains a prefix.**

That is not timidity, it is the local cost. `agent/inference.py` materialises RDFS closure **by
hand**, and [one-graph-both-engines-read](one-graph-both-engines-read.md) exists because shapes
inferring while the runtime did not let a world validate against a relationship no code would ever
observe. Every imported vocabulary's subclass axioms have to be covered or that trap reopens. SOSA
and PROV are safe because a dozen terms of each are used; importing an accounting ontology to gain
naming is paying the closure cost for interoperability nothing here wants.

So this is a **ubiquitous-language decision, not a dependency**. The value is that our words are
checked against a standard and the deviations are stated.

## The mapping

| here | ValueFlows / REA | |
|---|---|---|
| water | `vf:EconomicResource` | |
| the host's offer — lot, reserve, deadline | `vf:Intent` | *"a desired or proposed or planned economic flow, usually with only one agent associated"* — which is the offer exactly: proposed, and promised to nobody yet |
| a bid | `vf:Intent` | the other side. Two intents meeting is what an auction resolves |
| the trade — every line of it | `vf:Agreement` | *"a set of reciprocal commitments among economic agents"* |
| a claim | `vf:Commitment` | *"a planned economic flow that has been scheduled or promised by one agent to another agent"* |
| the valve opening | `vf:EconomicEvent` | *"an observed economic flow"*, and `vf:fulfills` is the link back to the commitment |
| the wallet debit | the reciprocal `vf:EconomicEvent` | the other half of the duality |
| **nothing** | `vf:Claim` | see below |

## Which corrects us: a claim is a commitment

`domain/claim.md` has always called a claim *"a co-signed, single-use **claim** on the
supplier for N litres"*. That is the loose English word, and REA has a precise one that means
something else.

A **claim** in REA is what exists when a flow has happened and its reciprocal has not — someone
delivered, someone owes. A **commitment** is a promised future flow. A claim is issued *before
anything moves*: it carries `amount_l` and `debit` together, both legs, neither performed. So it
is a commitment, and the reciprocal commitment is in the same token.

**We have no claims at all**, and naming the term we do not use is the most informative row in the
table: nothing here is delivered before it is settled. There is no moment where water has flowed
and payment has not, so the concept that would cover it has nothing to cover. That is a real
property of the design — it says settlement is atomic — and it was invisible while the word *claim*
was being used loosely for something else.

The *contrast* `claim.md` was drawing with that word is untouched and still right: a claim is
against the **supplier**, not a command naming a valve. Only the noun changes.

## What was checked and rejected

- **GoodRelations / schema.org** — `gr:Offering`, `UnitPriceSpecification`, `eligibleQuantity`,
  `validThrough` would cover a lot, a unit price and a deadline. No reserve, no bid, no auction, no
  clearing, and it brings a consumer-commerce frame — business entities, payment methods, delivery
  — that does not describe agents bidding for water. Rejected for shape, not for quality.
- **FIBO** — real trading and market concepts, wrong scale: thousands of classes modelled for
  regulatory semantics on financial instruments. Under the hand-materialised closure this is not a
  close call.
- **FIX** — the actual industry term set for orders and executions, and not RDF. Useful as a naming
  reference if bid and trade fields ever need standard names; nothing needs that now.
- **FIPA's auction protocols** — English, Dutch, Contract Net, Iterated Contract Net. These cover
  the *choreography* rather than the vocabulary, which is the one thing REA does not, and
  `domain/round.md` already carries a `contract-net` tag. **Not examined here**, and the most
  promising thing left unread.

# Consequences

- **`domain/claim.md` says commitment** and explains why the REA claim is a different thing we
  do not have.
- **The absence of `vf:Claim` is documented rather than incidental.** If futures land — a claim
  held and spent later, which [roadmap](roadmap.md) has — delivery and payment come apart in time
  and a claim may become real. That is the trigger for revisiting.
- **A standard vocabulary is a check, not just a source.** The value here was not a term we lacked;
  it was finding a term we were using for the wrong thing. That is the second time in three
  vocabulary passes that the fix was a word already in the file.

# Seams left open

- **Nothing imports `vf:`, so nothing is interoperable.** An outside tool reading a world learns
  nothing from this record. If external legibility is ever wanted, importing is a separate decision
  with the closure cost attached, and the mapping above is what it would implement.
- **FIPA's interaction protocols are unread.** Whether our round matches an established
  choreography — and what it should call its messages — is open, and it is the cheapest remaining
  reuse.
- **`vf:Process` has no counterpart here.** Watering is arguably a conversion of a resource, and
  nothing models it as one. Nothing depends on the answer.
- **The alignment is prose.** No shape, test or rule enforces that our words keep meaning what this
  record says they mean, which is the same seam the two previous vocabulary records left.
