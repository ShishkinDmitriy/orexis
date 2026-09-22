---
type: Decision
title: >-
  "The lot states its good, and every denomination join closes through it"
description: >-
  The good becomes a node — market:Good, water:Water — because the venue tie cannot run
  venue-to-valuation or through a property: one good honestly has a valuation per kind of
  recipient (a litre raises a pot's moisture and a barrel's stock), and what disambiguates a
  venue is what flows out of its source. Every join that used to float over the T-Box now
  closes venue -> marketFor -> source -> supplies -> good <- ofGood <- valuation, plus the
  asker's own region want. Shipped together with the world it was gating: the city mains, the refill
  venue that derives from one consent triple, and the supplier as a live inventory dealer
  whose spread sits in its beliefs file.
status: accepted
timestamp: 2026-08-17T23:28:46Z
---

# The lot states its good, and every denomination join closes through it

Issue #198's finding, sharpened by building the world that made it urgent. Nothing tied a
VENUE to its denomination: the menu, the reflex, the bidder, the host and the participation
rule all joined "a market I can reach" and "a valuation about this property" as independent
facts — safe while one domain meant one denomination, and a cross-multiplication the moment a
second existed. Arc 4 of the barrel plan is that second, from inside one domain: the city
sells litres against `StoredLitres` while the barrel sells litres against `SoilMoisture`, and
both sources are water.

## Does water need to be a concept? Asked mid-arc, and yes — the good is a node

The tie could not run venue-to-valuation directly, and could not run through a property.
What a litre DOES depends on where it lands — a pot's moisture, a barrel's stock — so **one
good honestly has several valuations, one per kind of recipient**, and what disambiguates a
venue is what flows out of its source, not what any buyer will do with it. So the good is a
node: `market:Good` in the kernel of the market package, `water:Water` as the domain's one
individual, `market:supplies` stated ONCE at class level (every `WaterSource` vends water —
the datasheet pattern, entailed onto every barrel and every mains), and `market:ofGood` on
each valuation term, beside `aboutProperty` and `direction`, because the three are one
sentence: a lot of THIS GOOD, priced in THIS PROPERTY, moves it THIS WAY.

The distinction it makes precise: `market:marketFor` points at the source INSTANCE — whose
stock, whose ACL — and the good is the KIND. The venue's tie is the composition
`marketFor/supplies`, deliberately not minted onto the market node as a third triple: a copy
of a derivable fact is what [one-word-for-one-relation](/decisions/one-word-for-one-relation.md)
exists to refuse. And [the-ladder-of-means](/decisions/the-ladder-of-means.md)' "the market is
about the resource, not the lever" finally has a graph word for "the resource".

## Every asker adds its own region want, and the same join answers five questions

The venue narrows to the good; the good still fans out to a valuation per recipient kind; and
what picks ONE is the asker's region want — the same premise the participation rule always used,
asked from each side:

- **the rule** derives `bidsIn` only where the source's good meets a property the buyer's
  subject states a need in — without it, the city's venue would have claimed the plants and
  the barrel's venue the dealer;
- **the bidder** discovers what its bids are priced in (and which belief converts its
  deficit) through its venue plus its subject's ranges — the fixed `litresPerFraction` IRI
  it used to interrogate was right for every bidder exactly as long as every bidder was a
  plant's;
- **the effect rule** predicts what buying would make true along that same walk, because a
  prediction with no venue behind it is a move with no lever. (It was the reflex that asked
  this, as a DIRECTION, until the reflex was deleted; the walk is unchanged and the answer is
  now a number rather than one bit.)
- **the menu** walks the full chain and now provably yields two rows with two directions for
  two opposite levers on one property, never four — the pinned fixture authors a drying
  market by hand and watches the cross-join stay dead;
- **the host** convenes each venue on the properties its PARTICIPANTS' region wants are in — a set,
  because one venue may serve two kinds of recipient — so the dealer hosting water-for-pots
  while bidding for refill litres never confuses the two scarcities.

The conversion also left the bidding beliefs block: a block's terms are fixed at import, and
WHICH conversion a bidder needs is a fact about its venue, so the module reads its own belief
by the IRI the venue tie named. What stays in the block is what any buyer of any good needs —
a wallet, and a ceiling per unit of the GOOD.

## The world that forced it: a barrel on both sides of the wire

The city is what the supplier was before the arcs — a regionless seller
([strategic-supplier](/decisions/strategic-supplier.md)'s Design B, one rung up) — and its
venue derives from one consent triple exactly as
[a-market-arises-where-want-meets-supply](/decisions/a-market-arises-where-want-meets-supply.md)
promised: author a source, an owner, a pipe, `matchesBy`, and the supplier wakes up a bidder.
It matches by UNIFORM PRICE, so both members of the matching family run live in one world and
an uncontested refill round dissolves to the reserve
([uniform-price-dissolves-the-uncontested-round](/decisions/uniform-price-dissolves-the-uncontested-round.md)).

The supplier is now the working **inventory dealer** of
[the-market-has-no-governor](/decisions/the-market-has-no-governor.md): it buys upstream at
one venue and sells downstream at another, the barrel between them, and no claim ever changes
hands — the stock decouples the two markets. Its spread is not a mechanism anywhere: it is
two numbers in its beliefs file (buy ceiling 0.15, sell reserve 0.20), disciplined by entry
and visible to the ledger, which is that record's fairness argument made runnable.

Physics-wise the barrel is the first subject on BOTH sides of the wire: plant valves lower
its stock, the city's valve raises it. Conservation was already stated once on the class
(`modelDoseEffect -1.0`); its mirror joined it — `litresPerStoredLitre` identically 1.0, a
litre poured in is a litre held — and the stand-in's one signed conversion became two keys,
with the sign carried by WHICH SET a topic is in (dose or drain), because a number cannot say
which side of a wire it is on when a subject is on both. The refill trigger is the same
mechanism one level up the supply chain: the supplier's stock band travels on its event topic
exactly as a fern's moisture band does, and a LOW barrel is what convenes the city.

# Seams left open

- **One venue per want, still.** The tie makes a bidder in two venues on one property
  expressible — the menu yields both rows honestly — but `BiddingModule` still discovers ONE
  denomination (`LIMIT 1`) and holds one pending round. Today no agent bids in two venues, so
  nothing is wrong; the chooser — price comparison across venues, deliberation's next real
  decision — is the second-supplier world's business, already flagged in
  [the-market-has-no-governor](/decisions/the-market-has-no-governor.md)'s seams.
- **The drying market is a test fixture.** No shipped domain sells drying; the two-direction
  fixture authors its good and valuation by hand. The day a fan domain ships, the fixture
  retires into its ontology and the direction column earns its first real `Lowers`.
- **The mains is unwitnessed and never runs dry.** `capacityL 1000.0` is a constitutional
  allocation ceiling, not a stock anyone watches — honest for a mains, and it means the city
  can oversell only against the constitution, not against a level. A metered mains with a
  finite tank is just a barrel with a bigger number, and would need nothing new.
