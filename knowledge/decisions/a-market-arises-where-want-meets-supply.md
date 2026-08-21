---
type: Decision
title: A market arises where want meets supply, and stating your matching rule is opening shop
description: >-
  Market existence becomes derived — venue and topics minted from the source's id (the
  derived-stream precedent), hosts from ownership, bidsIn from the Acquire walk's own premises
  — with one authored triple as consent: the owner stating market:matchesBy IS opening shop.
  Both the plants' market and the coming refill market are then one mechanism, and the second
  genuinely appears the moment its wiring exists.
status: accepted
timestamp: 2026-08-17T18:54:31Z
---

# A market arises where want meets supply

Asked by the sovereign on seeing the seller learn to want: the refill will need someone to
sell water to the water-seller — will that second market appear dynamically, and can the
FIRST appear the same way? Yes to both, because everything a market instance states is
derivable from wiring that exists for its own reasons, except one triple that should stay
authored because it is consent.

Look at what `:barrel1_market` actually says: topics that are mechanically `market/barrel1/*`
— a function of the source's id, exactly the shape
[a-stream-is-a-thing](/decisions/a-stream-is-a-thing.md) already mints derived instances in —
a `marketFor` pointing at the source, and a host who owns it. So:

- **The venue derives** from a source + `water:suppliedBy` an owner + the owner stating
  `market:matchesBy`. The last is the design's hinge: **stating your matching rule IS opening
  shop** — consent-to-sell as a single authored triple, public because an auction's terms
  belong to whoever convenes it, and everything else minted from the source's id.
- **`market:hosts` derives**: the owner of the source hosts its venue.
- **`market:bidsIn` derives** from the Acquire walk's own premises (#189): an agent with a
  stake in the denominated property whose pot the venue's valves reach is a participant.
  Plumbing implies participation; the world stops naming buyers. Since #198 the premise
  closes through the GOOD — the source's stated stuff must be what the valuation converts —
  because "the denominated property" stopped being one thing the day the refill venue priced
  the same water in StoredLitres; see
  [the-lot-states-its-good](/decisions/the-lot-states-its-good.md).

Both markets are then one mechanism. The plants' market derives from today's wiring
unchanged — the same triples land in the derived graph with honest provenance
([who-put-the-fact-there](/decisions/who-put-the-fact-there.md)) — and the refill market
self-assembles the moment its wiring exists: a `:city_mains` source plumbed to the barrel,
owned by a city agent that states its matching rule, meeting the want the stake arc created.
Metered mains IS a market relationship, which is why the refill buys rather than Actuates;
the Actuate rung ([#190](https://github.com/ShishkinDmitriy/agora/issues/190)) stays for a
genuinely-owned source — a rain-fed cistern, where the water really is free.

This also improves the planning arc: the depth-2 plan becomes **buy upstream to sell
downstream** — both steps ordinary Acquire moves through two derived markets, the supply
CHAIN as the first real plan, no new means required.

# Seams left open

- **Implemented, in two arcs.** The derivation shipped with #199 and the plants' market
  re-derived byte-identical; the city, its mains and the refill venue shipped with the #198
  arc — and the venue genuinely APPEARED: the world file authors a source, an owner, a pipe
  and one consent triple, and the supplier woke up a bidder. What remains of the barrel plan
  is the planner (arc 5).
- **The venue's derived instances** (market node, its topics) follow the stream precedent:
  minted as a function of the source id, written to the derived graph, never authored. The
  ACL and compose generators already read the ratified dataset derivation included, so grants
  follow without new machinery — to be verified by the implementing change, not assumed.
- **What stays authored** besides consent: the host's terms (reserve, quantities, windows —
  already private beliefs), and the denomination (the domain's, as ever). A world may still
  author a venue by hand where it wants one the wiring does not imply; the derivation adds,
  never forbids.
- **Withdrawal is un-consent**: deleting `matchesBy` at the next amendment closes the shop.
  What happens to standing claims when a market vanishes is the amendment machinery's
  ordinary problem (a world version bump), not a new one.
