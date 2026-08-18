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

# The two members

- **`deliberation:Reflex`** — the old chain, generalised one honest step: cannot see → look;
  a gap on the side a lever moves → pursue; otherwise nothing. WHICH side is read off the
  T-Box, not known (#127): the domain states `market:direction` beside the denomination —
  water Raises moisture — so a heater against a cold snap is the same rule with no code
  change, and a missing direction means the reflex refuses rather than letting the old
  hardcoded sign sneak back as a default. Still deterministic, still free.
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
  hand a subject-shaped answer to a venue-shaped question.

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
probe; look at temperature through the thermometer; raise moisture through the market.* The
row that is **absent** is a finding too: fern wants a temperature it can see and cannot move —
a want with no lever, legitimate and now legible. This is the Consulting member's prompt
substrate, shipped before that member exists so "the menu is derived, not written into a
prompt" is checkable now.

# The gaps — what I should decide about, noticed by whoever is positioned to (#208)

Deliberation used to run only when the market knocked: an offer arrived, or birth. So an
agent's watching of a property no market relieves lived in cadence machinery and never
reached the intention ledger — the sovereign inspecting intentions saw market conduct only.
Noticing is now the choir again: `Module.gaps()` beside `annotate`/`urgency`/`quiet`, each
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
