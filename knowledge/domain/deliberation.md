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

- **`deliberation:Reflex`** — the old chain, verbatim: cannot see → look; below the aim →
  pursue; otherwise nothing. Deterministic, free, always a valid fallback, and extracted
  *unchanged* so the seam provably carries the existing behaviour — every round test that held
  before the extraction holds after it.
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

# The proof the seam is load-bearing

`tests/test_deliberation.py`: silence the deliberator and a thirsty bidder with a fresh reading
in hand — everything the old welded bidder needed — submits nothing, because the whether
genuinely is not the bidder's any more. Before the extraction no test could have made that fail,
and it is the property a model member stands on: replace the answerer, touch no actor.
