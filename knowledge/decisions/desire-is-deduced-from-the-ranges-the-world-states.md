---
type: Decision
title: Desire is deduced from the ranges the world states, never picked
description: >-
  An agent's desire was three decimals in a private file — a target and two band edges, in
  soil moisture and nothing else — so an agent could want exactly one thing and could pick
  where its own comfort limits lay. Desire is now a capability with its own namespace and its
  own graph class: for each property its subject states a need in, the agent DEDUCES a region
  by intersecting every operating range that applies, and carries the survival ranges as the
  envelope that makes urgency asymmetric and unit-free. The band left market:Bidding with it,
  so having an opinion about your own state no longer requires being a market participant.
status: superseded-in-part
superseded-by: a-desire-states-its-own-measure
timestamp: 2026-08-13T00:00:00Z
---

> **Superseded in part** by
> [a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md): the urgency
> formula below anchors at the region's CENTRE, and the centre was only ever standing in for
> the pick — the measure is the desire's own now, declared in the graph, anchored at the AIM
> with the centre as the no-pick fallback. Everything the formula's shape argued survives the
> re-anchoring: it rises inside the region, and it is asymmetric per plant for free, scaled by
> the survival room on the side the value sits.

> **AMENDED: it is not a capability any more.** The reasoning below stands and produced what the
> code does; what changed is WHERE it lives. Wanting, committing and deciding are the kernel's,
> granted by nothing, because the stores they read were built for every agent unconditionally
> while the code reading them was a grant. See
> [the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md).


# The question

[the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)
gave a plant a public range and made an agent's target answer to it. It closed the gap it was
written for and left the seam it named first on its own list:

> **An agent can hold exactly one desire.** `market:aboutProperty` occurs once in the whole
> repository — `water:hasTarget → water:SoilMoisture` — so a desire is a single scalar
> denominated in soil moisture. […] The temperature and humidity this society senses therefore
> feed **nothing that can want anything**.

Two things were wrong and only one of them was the arity.

**Desire was not a thing.** It was three decimals spread across a beliefs file — `water:hasTarget`,
`water:bandLow`, `water:bandHigh` — plus two methods on `BiddingBeliefs`. Nothing in the
vocabulary said *desire*, nothing owned it, and the code that judged a reading lived in the
market package, so **having an opinion about your own state required being a market
participant**. An agent acting for a plant in a world with no economy at all still knows when
that plant is in trouble; it simply has nobody to ask for help. `world/sensing` says exactly that
in a comment — *"with nothing to advance for it, this agent holds no stake — it records"* — and
nothing enforced the converse.

**And the bands answered to nothing.** The target was checked against the plant's operating range;
the bands deliberately were not, on the reasoning that an alarm threshold legitimately sits
outside the range it warns about. That reasoning was right about alarms and wrong about where the
numbers came from: `water:bandLow`'s own comment read *"a comfort limit, desire-relative — not the
rot limit, which is physical and the constitution's"* — and the rot limit is the survival range's
ceiling while the comfort limit is the operating range's. **Both are the plant's.** An agent
restating them privately was keeping a second copy of a public fact, and was free to keep a wrong
one.

# What was decided

**Desire is a capability, in its own package, with its own namespace — and a region is DEDUCED
rather than authored.**

```turtle
# what the world says (public, authored)
orexis:fern ssn-system:hasOperatingRange [ ssn-system:inCondition
          [ ssn:forProperty water:SoilMoisture ; schema:minValue 0.45 ; schema:maxValue 0.65 ] ] ;
        ssn-system:hasSurvivalRange  [ ssn-system:inCondition
          [ ssn:forProperty water:SoilMoisture ; schema:minValue 0.20 ; schema:maxValue 0.85 ] ] .

# what the agent concludes (public, derived, in its own graph) — a SHAPE, one per
# (agent, property), the region and the envelope differing only in severity
orexis:fern_agent orexis:holds orexis:bounds.fern.SoilMoisture .

orexis:bounds.fern.SoilMoisture a sh:NodeShape ;
    sh:targetNode orexis:fern_agent ;
    ssn:forProperty water:SoilMoisture ;
    sh:property [
        sh:severity orexis:ShouldBecome ;                  # a want, never a refusal
        sh:path ( orexis:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
        sh:qualifiedMinCount 1 ;                       # unmeasured IS a gap
        sh:qualifiedValueShape [
            sh:property [ sh:path sosa:observedProperty ; sh:hasValue water:SoilMoisture ] ,
                        [ sh:path sosa:hasSimpleResult ;
                          sh:minInclusive 0.45 ; sh:maxInclusive 0.65 ] ] ] .
```

The envelope is a second shape alongside it, at `sh:Warning`, and asks the opposite question —
`sh:qualifiedMaxCount 0` over `sh:not` in the range, because silence is not evidence of
catastrophe where it *is* evidence of a gap. See
[a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md) for why, and for the vocabulary this
example used to be written in.

| | where it lives | what it is | who may move it |
|---|---|---|---|
| the plant's two ranges | `world.ttl` / a species package, **public** | horticultural fact | the sovereign, by ratifying |
| the agent's **region** | `…/graph/constraint`, **public, derived** | what it will try to hold | nobody — it is a function of the above |
| the agent's **target** | `beliefs/<id>.ttl`, **private** | the point it aims at inside the region | the agent, via [review](/decisions/self-review-is-a-capability.md) |

The middle row is new, and it is the one that was missing. Range public, pick private, exactly as
before — but the range is now *stated by the store* instead of being a join every reader had to
remember to perform identically.

## The arithmetic is intersection, and both bearers contribute

A region is where **every** range that applies agrees: the highest floor anyone states, the
lowest ceiling. Two sources contribute.

- **the subject** — the plant's own operating range, per pot in the world or per species through
  the `owl:hasValue` closure. This is what it *needs*.
- **its instruments** — the operating range of anything `sensing:monitors` it. This is what
  can be *witnessed*, and it belongs in the same intersection rather than in a separate check: a
  region an agent cannot see itself inside is not a region it can hold.

The property is bound from the **subject's** conditions and never from an instrument's. A DHT11
rated 0-50 °C states a fact about the DHT11; it must not become a desire to hold a pot anywhere
in that band. **An instrument may narrow a desire and may never create one.**

Nothing states an instrument range today, so that branch is inert and was shipped anyway — the
day a part's datasheet range lands in a world, every agent watching through that part narrows
with no edit to the rule. It does not make
[#111](https://github.com/ShishkinDmitriy/orexis/issues/111) redundant: silently narrowing a
badly-specified rig is not the same as refusing it, and the sovereign should still refuse.

## The survival range is what makes urgency mean anything

This is the half that could not have been done before, because nothing carried the second range
to where the arithmetic was.

The **band** is the region: LOW below it, HIGH above it, OK inside. The three words are
unchanged and still never stored — the same 0.30 is LOW for a fern and OK for a succulent.

**Urgency is measured from the centre of the region toward the survival bound on that side.**

```
urgency(v) = |v − centre| / |survival bound on v's side − centre|,  clamped to 1
```

Two properties fall out of that and neither is coded:

- **it rises inside the region.** A step function would tell sensing to relax completely
  anywhere inside and then panic on the way out. An agent at the edge of comfortable is already
  worth watching more closely than one in the middle, so the band answers *am I in trouble* and
  urgency answers *how close am I getting*. They are not each other's complement.
- **it is asymmetric, per plant, for free.** How bad it is to be 0.05 out depends on how much
  room there is in that direction. A Zamioculcas comes back from bone dry and does not come back
  from a rotted rhizome; with both ranges in hand the wet side reads as sharper than the dry one,
  and no line of code knows what a rhizome is.

A world stating no survival range gets the region's own edge as the scale — cruder, honestly
reached, and uniformly *sharper* rather than more relaxed. Not knowing how much slack there is
must not be read as knowing there is a lot.

## Deduced, not declared — which is what makes it a capability

The premise is **a stake**: `orexis:actsFor` a subject that states what it needs. AGENTS.md's rule is
that each capability is granted by whatever fact makes it meaningful and that the fact is its
own — sensing's is equipment, review's is latitude, and this one's is having something to
advance for. `world/sensing`'s agent is wired to three sensors and acts for nothing, so it
derives no desire and records; the supplier holds a market and no stake, so it derives none
either.

And it passes rule 2's test, which is that the *how* could differ. `desire:Deducing` takes the
strict intersection and has no latitude at all — two agents over the same world reach the same
region. `desire:Consulting`, asking something else where inside wide ranges to aim, is a
different answer to the same question; it is declared and deliberately unimplemented, exactly as
`review:Consulting` is.

## A graph class, not a graph

`orexis:ConstraintGraph` is a **class**, and `…/graph/constraint` is the one instance today. That is the
same arrangement `orexis:PublicGraph` has and it is here for the same reason: **a reader asks by type
and unions whatever it finds**, so a second source of desire — an operator's override, a regime
selected for the season, a region an agent narrowed for itself — is a vocabulary edit that
touches no Python.

Making that work needed one generic addition to the kernel. A rule could previously write only to
`$derived`, the world's derived graph, so a package could not own one. It may now write
`$into(pkg:SomeGraphClass)`: the rule names the **class**, `agent.genesis` resolves it to the
single graph the vocabulary types that way, and refuses if there is not exactly one. **No rule
names a graph** still holds — a graph IRI is an instance, and rule 1 applies to it. Three things
that used to be true of exactly one graph because there *was* exactly one are now asked of the
rules rather than remembered: what derivations may read (`$given` excludes every write target),
what is cleared before a recompute, and what the provenance graph must account for.

# What moved, and what that cost

- `water:bandLow` and `water:bandHigh` are **gone** from the vocabulary, the shapes and three
  beliefs files.
- `BiddingBeliefs` keeps a wallet, a target and a value curve. `annotate` and `urgency` left
  `market:Bidding` entirely.
- `water:WaterBidderShape` checks the target against the agent's **region** rather than
  re-deriving the join from the plant. The shape and the module now agree by construction instead
  of by two authors performing the same join from memory.
- **Two latent defects became live and were fixed in the same change**, both consequences of
  there having only ever been one band:
  - a host opened a round on *any* `band == "LOW"` it was sent. A fern now announces a
    temperature band too, and nothing relieves a hot afternoon by dispensing water. Hosting
    filters on the property the **domain** says a bid is priced in — asked of the domain and not
    of the market, because a market is a lot.
  - `set_cadence` **merged** verdicts across the sensors sharing a board, so with two bands the
    device would display the comfort of one property while the other was the reason it was being
    read every thirty seconds. The verdict now travels with the sensor that set the cadence: one
    interval, and the reason for it.

# What this closes

[#110](https://github.com/ShishkinDmitriy/orexis/issues/110) in full, including the slice it
called cheapest: *"a desire in a property no market relieves is still worth holding — it changes
urgency, and therefore polling cadence, without anyone bidding."* `world/simulation`'s fern now
states an air-temperature range as well as a moisture one, holds two regions, and lets whichever
is more urgent set how closely its board is watched. Nothing bids on air temperature.

# Seams left open

- **A region is one regime.** The limit
  [the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)
  recorded is unchanged: `ssn-system:inCondition` cannot say which of its conditions qualifies and
  which is the requirement, so *"0.30-0.50 when illuminance is low"* is not expressible. What has
  changed is that there is now somewhere for a selected regime to land — a second
  `orexis:ConstraintGraph` — so the missing half is the selection and no longer the representation.
- **Nothing weighs one desire against another.** Urgency is per property and sensing takes the
  max. An agent that is both too dry and too cold has no way to say which matters more, and a
  weight would have to come from somewhere no ratified file currently is.
- **The target is still a separate belief.** A region and a point are different things and the
  split is deliberate, but nothing stops an agent whose region moved from keeping a target that
  is merely still legal rather than still sensible. `packages/orexis-capability-review/` could be asked to
  justify a target against its region; today it only refuses one outside it.
- **Only the bidder consumes a region for anything but attention.** Actuation doses against a
  claim, not against a region, so *"keep the value inside the region"* is a market's job
  wherever a market exists and nothing's job where one does not. A controller that acts directly
  on a region — the obvious next reader of `desire:Deducing` — is not written.
- **The instrument branch is inert.** No part states `ssn-system:hasOperatingRange`; the DHT11
  states `MeasurementRange` instead. Whether those are the same claim is
  [#100](https://github.com/ShishkinDmitriy/orexis/issues/100)'s territory, not this record's.
