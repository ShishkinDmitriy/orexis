---
type: Domain Concept
title: Deliberation
description: The whether, extracted into a family — given the gap and the standing commitments, name the next move; the acting modules carry it out. Reflex is the old welded chain as the first member, deterministic and free; Consulting is the declared, unimplemented seat for a model, constrained before it exists — a move from the vocabulary's menu, never free text-to-action, with the bid number staying deterministic and the keeper's patience bounding how often it is consulted.
tags: [deliberation, bdi, llm, capability, market, intention]
timestamp: 2026-08-13T00:00:00Z
---

# What it is

The **whether**. Whether to look and whether to pursue used to be welded into the bidder — a
reading arrived and `value_bid`'s cede was the whole of deciding — which meant the one place
this project intends to seat a model
([llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md)) had no seam to drop into. It is
a family now: a deliberator is asked `propose(property, freshest value or None)` and answers
with a move — `Observe`, `Acquire` — or with None, **which is a decision, not an absence of
one**: the actors treat it exactly as they treat their own cooldowns.

`propose_for(goal)` is the same question asked properly. A property and a value can only ever
express a stake, and an agent also wants things that are not distances — "this claim redeemed"
is a state, wanted, with a deadline. A goal carries either shape and one urgency, so a duty is
ranked against a thirst rather than running down a second path that never meets the first.

**And it is where not-seeing is answered** (#240). `propose` used to open with
`if value is None: return OBSERVE` — a first line that read a missing number as ignorance. It
said the right thing for the wrong reason, because None meant two things: *never read*, and
*the caller has no number to hand you*. The keeper exploited the second to ask the first,
sweeping noticed gaps and passing None deliberately to mean "should I look?". A goal says which
epistemic failure it is — `unmeasured` or `stale` — so the question is now asked in the words it
means, both are answered by the same move, and the bare-value door steers only. One sentinel
answering two questions is a sentinel that eventually answers the wrong one.

# The three members

- **`deliberation:Reflex`** — the old chain, generalised one honest step: cannot see → look;
  a gap on the side a lever moves → pursue; otherwise nothing. WHICH side is read off the
  T-Box, not known (#127): the domain states `market:direction` beside the denomination —
  water Raises moisture — so a heater against a cold snap is the same rule with no code
  change, and a missing direction means the reflex refuses rather than letting the old
  hardcoded sign sneak back as a default. Still deterministic, still free.
- **`deliberation:Planning`** — the reflex one level up (#205): bounded search over menu
  rows, depth 2 and no deeper, granted by the DEALER premise — acting for a source you offer,
  refillable from a source another offers: levers that compose. It subsumes the reflex and
  adds exactly one deduced goal past the region: the hosted lot must be serveable, every
  downstream buyer's silent Acquire precondition. Its plan — acquire upstream, then offer
  downstream — is data twice over: `plan_for` in code and `plan.rq` on the ask channel, one
  text, two readers. A planner always also derives Reflex (the premises nest); a pinned test
  holds `provider` to handing actors the planner.
- **`deliberation:Consulting`** — RESERVED. One model call over the beliefs, the T-Box, the gap
  and what already stands, emitting a move **from this vocabulary's menu, never free
  text-to-action**. Its constraints are fixed before it exists: the bid *number* stays
  deterministic ([deterministic-bid](/decisions/deterministic-bid.md) — the model picks whether
  and when, code computes how much); an intention it leads to validates against the same shapes
  or is not adopted; and the [keeper's patience](/domain/intention.md) bounds how often it is
  consulted at all, which is what makes it affordable.

# What stays out

- **The how.** A bid's quantity and price, a cadence, a dose — the actors', whoever said to act.
- **The keeping.** A deliberator may read what stands and never writes the ledger: deciding and
  remembering what was decided are different abilities, which is why keeping and deliberating
  are two capabilities on one granting premise (a stake and a lever) rather than one.
- **The host's trigger.** A host has no gap — its "whether to sell" is a stake in the *market*,
  the [strategic-supplier](/decisions/strategic-supplier.md) seam, and putting it here would
  hand a subject-shaped answer to a venue-shaped question. (An owed round is not a counter-
  example: physics defers it and the keeper remembers it — nothing here decides it. #206.)

# The menu — what I could do, derived

The menu is THE UNION OF WHAT THE LOADED PACKAGES CONTRIBUTE (#207): each package may ship an
`affordances.rq` — its rows, its preconditions as its own walk — and `menu_of` collects them.
Sensing ships the Observe branch, the market ships Acquire; this package keeps only the frame
and its consumers. It shipped one big `menu.rq` here first, which made the menu's KINDS a
registry in this directory — the sovereign caught the overclaim ("how is it dynamic if the
list is hardcoded?"), and the fix was the repo's mechanic applied a fourth time: a new way of
acting is a new directory, with no Python at all where execution reduces to an existing
actor. One row per (means, property, lever, direction), joined from facts that exist for
their own reasons — regions, wiring, denominations. For fern: *look at moisture through the
probe; look at temperature through the thermometer; raise moisture through the market.* For
the loner world's gardener: *raise it through your own pump* — the Actuate rung (#190), offered
exactly where the lever AND the resource chains both end at the agent, and preferred by the
now menu-driven reflex because the ladder's order is the preference: act with what is yours
before buying what is not. The
row that is **absent** is a finding too: fern wants a temperature it can see and cannot move —
a want with no lever, legitimate and now legible. This is the Consulting member's prompt
substrate, shipped before that member exists so "the menu is derived, not written into a
prompt" is checkable now.

# What a lever DOES — the effect a means carries (#238)

A row says a lever is available. It does not say what pulling it would achieve, and a goal that
is a graph needs that: matching a want to a lever means asking what the lever would MAKE TRUE.

So a package ships `effects.ttl` beside its `affordances.rq`, found the same way and named by
nothing — a `sh:SPARQLRule` per means, loaded into the effect graph at genesis. The vocabulary is
SHACL Advanced Features': `sh:condition` for the shape that must hold before it may run, and
`sh:construct` for the query yielding the triples applying it would add. One term is ours,
`ag:retracts`, because the standard has none: SHACL rules exist to add entailments, so nothing in
it can say a thing stops being true.

**Retraction is not decoration.** The sensed graph upserts — one observation node per (subject,
property), DELETE then INSERT — so an effect predicting a reading that left the old one standing
would put two results on one node. A shape asking whether ANY reading sits past an edge would
then answer about the reading the dose just replaced, and a planner would reject the plan that
works.

Two rules ship today and the pair is instructive:

- **Observe** carries the current value forward with a new `sosa:resultTime`. Looking changes
  what you KNOW and nothing else, and the tempting error — predicting a reading inside the
  region, since that is what the agent wants — would teach a planner that a thirsty plant can be
  watered by looking at it.
- **Actuate** predicts the post-dose reading, which is the case that decided the whole shape of
  this: **opening a valve adds no triple.** It changes a number a later observation reports, and
  only a template that can predict the number can say so.

**The prediction has ONE source, and that is enforced rather than intended.** `litres /
conversion` was already written twice in Python — the bidder sizing its expectation, the actuator
sizing its self-dose — before anything asked what a dose would do. The actuator now runs the rule
and subtracts rather than computing its own, so the number a planner uses to decide whether
dosing helps is the number the keeper later holds the world to. Two numbers would mean an agent
planning against one future and verifying against another, and the failure would look like a
device lying rather than like arithmetic disagreeing with itself.

# When it lands, and how you would know (#247)

A rule says two more things, and a planner needs both: **when it may re-decide** — never before
an effect could have landed, which states the flooding failure as a rule rather than patching it
with patience — and **when to call an act failed**, which is when "nothing happened" stops being
impatience and becomes a verdict.

`ag:landsAfter` is a SELECT yielding `?seconds`: how long until the WORLD CHANGE completes. A
query and not a number, because the duration is a function of the act — a two-litre dose holds a
valve open longer than a half-litre one — and `min(litres, the device's cap) / its calibration`
is arithmetic the rule is already the home of. **Zero is a real answer**, and the honest one for
a look: observing changes nothing about the world, so the change completes instantly and emptily.
What a sensing act delays is knowledge, which the other term is for.

`ag:confirmedBy` names the route by which the effect becomes knowable, and the four are worth
distinguishing because one of them is not causal at all:

| route | means | example |
|---|---|---|
| `ag:ByConstruction` | saying makes it so | a claim issued, a debt demanded |
| `ag:ByReport` | a device says what it did | a valve's status channel |
| `ag:ByObservation` | a later reading shows it | the pot moved |
| `ag:Unconfirmed` | nothing will ever say | a valve with no status channel and no witness |

**Constitutive effects are the ones worth naming.** Conflating them with causal ones produces
code that verifies an agent really did write down what it just wrote down — and, worse, leaves a
planner waiting for a confirmation nobody will send. Issuing a claim MAKES the claim issued;
opening a valve does not make a plant watered.

`ag:Unconfirmed` stays expressible on purpose. A valve wired without a status channel is a real
deployment, not an oversight, and the honest response is to say so — an agent that cannot verify
should restore its observation before acting again, rather than dosing blind.

**Both readers now ask instead of computing**, which is the single-source argument one axis over
from the prediction. The dose deadline is the rule's answer plus the bus slack the agent already
believes (`actuation:doseGraceS`); the keeper's watch is the rule's answer plus how long a
reading of that property may honestly take to arrive (`stale_after_s` — the cadence the agent
itself commanded, plus its own grace). A second copy of either would be a second claim about when
the world should have answered, and the disagreement arrives as a false UNMET that looks like a
device lying.

That closed a seam the keeper's own docstring had recorded: the deadline used to be the
`patienceS`, and patience was never *wrong*, only unrelated — it is how long an agent waits
before re-deciding, not how long the physics takes. Holding a dose to it judged a valve at 120s
while the pot's sensor reported every 600. **Patience remains the answer when an act cannot size
itself**, which is the buyer's case: it holds a claim on somebody else's valve and cannot ask its
own rules how long that valve stays open.

The rules are a SCHEMA, which is why they live in the store while rows stay computed: a stored
row can outlive the plumbing it was concluded from, and a rule about a means cannot. Both are the
same modality — what I could do — and they differ in arrival, which is what `ag:arrivedBy`
records.

**The vocabulary is SHACL-AF's; the engine is not.** pySHACL will execute these rules, and
measurably does — but only `inplace=True`, because its rules are forward-chaining inference run
to a fixpoint over every target, where a plan step is one rule against one hypothesis. A stored
`sh:construct` is just a query, and this project already has an engine that runs queries.

# Two modes: what I choose, and what I honour (#218)

A menu row says what happens THROUGH an agent, and there are two kinds. **Chosen** rows are
options — what a deliberator ranges over. **Honoured** rows are duties — what happens through this agent because
others hold paper against it.

They used to be *never proposed*: the whether was settled elsewhere and by others (the winner's
Apply, the auction's allocation, the signature chain), and the fear was that a host free to
deliberate over honouring claims is a host that can defect politely, one "None is a decision" at
a time. That is no longer the arrangement, and the fear was answered rather than ignored —
**enforcement was never the deliberation**. The dose still opens against a claim the pump's
firmware verifies, clearing still validated the trade, the ACL still bounds who may speak. What
deliberation controls is only whether the agent *tries*, so making the duty a want converts an
invisible non-event into a hot unpursued goal — evidence instead of silence. An honoured row is
now what lets a duty FIND ITS LEVER: an obligation names who it is owed to, and the row honoured
for exactly that counterparty is the means. See
[an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md). The mode is this package's term, not the market's — a mode is a fact about a menu row, and
sensing saying `market:Chosen` about its own Observe row was a package reaching into
another's vocabulary to describe itself. Packages ship duties in `honoured.rq` beside their
options in `affordances.rq` — a second file rather than a flag, because an author writing options
should not be one FILTER away from writing duties.

What this bought: the menu used to answer only *what could I do about MY gaps*, so an
ability that serves others — claims against my valves are redeemed — was a true fact about
the agent that lived nowhere queryable, and the sovereign asking what an agent does saw half
its conduct. Now one query answers both, the reflex filters to chosen, and the dealer's own
menu reads honestly: buy upstream, watch my stock, and honour three pots' claims.

# The gaps — what I should decide about, noticed by whoever is positioned to (#208)

Deliberation used to run only when the market knocked: an offer arrived, or birth. So an
agent's watching of a property no market relieves lived in cadence machinery and never
reached the intention ledger — the sovereign inspecting intentions saw market conduct only.
Noticing is now the choir again: `Module.notices()` beside `annotate`/`urgency`/`quiet`, each
module reporting the (subject, property) pairs it can see are unknown or too stale to act on
— sensing's are the archetype — and the KEEPER ticks on its own patience clock, handing each
gap to the ONE deliberator and committing what it proposes. Deciding and remembering stay
singular, and the boundary is pinned by a source-scan test: one deliberator, one pen on the
ledger. Only Observe is carried out from the tick — an Acquire needs a round nobody may
convene from this side, which is the-lot-is-the-hosts-standing-offer's seam, not this
mechanism's.

# The proof the seam is load-bearing

`tests/test_deliberation.py`: silence the deliberator and a thirsty bidder with a fresh reading
in hand — everything the old welded bidder needed — submits nothing, because the whether
genuinely is not the bidder's any more. Before the extraction no test could have made that fail,
and it is the property a model member stands on: replace the answerer, touch no actor.
