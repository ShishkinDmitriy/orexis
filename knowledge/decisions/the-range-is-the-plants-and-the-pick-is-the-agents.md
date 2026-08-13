---
type: Decision
title: The range is the plant's and the pick is the agent's
description: Desire was three bare numbers in an agent's beliefs with nothing to answer to, so 0.55 was as defensible as 0.95. A plant now states the range it needs, publicly in the world, using SSN's OperatingRange and Condition; the agent's target is a pick inside that range, privately in its own beliefs, and an agent whose target leaves the range will not start. Only the target is held to it — the bands are alarm thresholds and legitimately sit outside. It also records what is still missing: an agent can hold exactly ONE desire, denominated in soil moisture, so the temperature and humidity this society now senses feed nothing that can want anything.
status: accepted
stage: v1
tags: [beliefs, desire, bdi, domain, ssn, market, constitution]
timestamp: 2026-08-12T00:00:00Z
---

# The question

Where is the goal? The belief base was easy to point at, and BDI's other two letters were not.

The honest answer is that **desire was already there and unnamed**. `water:hasTarget` carries the
comment *"Desire: the moisture fraction this agent is trying to hold"*, beside `water:bandLow` /
`water:bandHigh` (comfort limits) and `water:maxValuePerL` (the private value curve). All of them
live in the agent's own belief graph, never the world, and `water:PlantShape` already enforced the
boundary: *"a plant holds no desire — the target belongs to its agent's beliefs."*

What was missing is that the desire **had nothing to answer to**. `water:hasTarget 0.55` was one
number in a private file, and `0.95` would have validated exactly as well. That is a strange gap
in a repository whose beliefs are otherwise
[a pick within a range](/decisions/a-belief-is-a-pick-within-a-range.md) — the review capability
already refuses a re-pick outside its mandate, while the *original* pick answered to nothing at
all.

# What was decided

**A plant states the range it needs; its agent picks a target inside it.**

```turtle
ag:fern a water:Plant ;
    ssn-system:hasOperatingRange [ a ssn-system:OperatingRange ;
        ssn-system:inCondition [ a ssn-system:Condition , schema:PropertyValue ;
            ssn:forProperty water:SoilMoisture ;
            schema:minValue 0.45 ; schema:maxValue 0.65 ] ] .
```

| | where it lives | what it is | who may move it |
|---|---|---|---|
| the plant's operating range | `world.ttl`, **public** | horticultural fact — the **range** | the sovereign, by ratifying a world |
| the agent's target and bands | `beliefs/<id>.ttl`, **private** | desire — the **pick** | the agent, via [review](/decisions/self-review-is-a-capability.md) |

This is the same shape as the mandate/pick split already recorded, one level out: there the range
came from `review:commits` and bounded a *re-pick*, here it comes from the plant and bounds the
*first* one. A fern and a succulent want different things because they *need* different things,
and now that difference is stated where anyone may read it rather than being implicit in two
numbers nobody could check.

**`ssn-system:OperatingRange` is SSN's, not ours**, and it is the right term rather than a near
one: *"the conditions in which a system is expected to operate"*. We already load it — the DHT11
states its sampling floor the same way — so this cost no new vocabulary. `ssn:forProperty` names
which property a condition is a range of, and `sosa:ObservableProperty rdfs:subClassOf ssn:Property`
makes that well-typed.

# Only the target answers to it

The bands do not, and the distinction is worth keeping. A fern's `bandLow` is 0.35 while its ideal
floor is 0.45 — **that is exactly right**, because the band is when it should start complaining and
the range is where it wants to live. Holding an alarm threshold inside the range it exists to warn
about would be confusing a comfort limit with a requirement.

The constraint matches on the property the desire declares (`market:aboutProperty`), not on the
first condition it finds. A plant that later states a humidity range must not have its moisture
target judged against it — the same error `_is_mine` exists to prevent in the bidder, arriving by
another door.

# Where it is checked, and why it can be

The check spans a **public** range and a **private** target, which meet in exactly one place: inside
the agent, whose store holds the world it booted with and its own beliefs. `validate_agent` flattens
precisely those graphs, so an agent whose target has left its plant's range **refuses to start**,
and nothing outside the agent ever sees the number. The world gate catches it too, because the
sovereign holds every belief file it authored.

# The link that was asked about: low moisture to auction

Recorded here because it was hard to find and is now easy to describe:

```
reading → _is_mine(subject, property) → annotate() → band → the agent's announcement
       → hosting.on_participant_event(band == "LOW") → announce() → offer
       → value_bid(): deficit → litres, deficit/target → urgency → price
       → match → voucher → actuate
```

The trigger is `hosting.py:on_participant_event`, whose own comment is *"A participant said it is
in trouble. Scarcity is what condenses an auction."* Two properties of it are deliberate: a
**band and never a number** crosses the wire, so the host learns that a participant is in trouble
and not how wet it is; and a cooldown means a flapping participant cannot spam the market. See
[round](/domain/round.md).

# One range is one regime, and SSN cannot say which condition is the qualifier

A plant does not want the same thing at midnight as at noon, in January as in July, or in bloom
as out of it. SSN's answer is the mechanism already in use: a range holds **under conditions**,
which is why the DHT11 states "continuous operation" rather than a bare number, and a thing whose
figures differ states *several* ranges rather than one number with a caveat.

The limit is real and should be known before anyone writes the second range. `ssn-system:inCondition`
is the only link an OperatingRange has, so on a range with two conditions there is **no way to say
which is the qualifier and which is the requirement** — "when illuminance is low" and "moisture
must be 0.30-0.50" are the same predicate. For a capability SSN separates them (`inCondition`
qualifies, `hasSystemProperty` carries the content); for an OperatingRange it does not, because
that class was built to answer "where does this work" and not "what does it need, when".

So regimes are **sayable and not yet said**, deliberately. Nothing could act on them: an agent
holds one desire in one property (below), so it has nothing to select a regime *with* and nothing
to do differently if it could. Modelling seasons now would be modelling ahead of every consumer.

**The symmetry is the part worth keeping.** A sensor states the conditions it operates in and a
plant states the conditions it needs, in the same terms — so "is this sensor's operating range
wide enough for the pot it is in?" becomes a question the sovereign could answer at validation,
from two facts it already holds. That check does not exist yet and is worth more than seasons.

# Seams left open

- ~~**An agent can hold exactly one desire.**~~ **CLOSED** by
  [desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md),
  which found the seam was two. A desire is per property now, and it is **deduced** rather than
  picked: `desire:Deducing` intersects every operating range that applies to the subject and
  carries the survival ranges as the envelope that scales urgency.
- **Two things above did not survive that**, and are corrected here rather than edited away,
  because both were argued for at the time and the arguments are worth being able to find.
  - **The bands are gone.** The section *"Only the target answers to it"* defended
    `water:bandLow` sitting outside the operating range on the grounds that an alarm threshold
    legitimately does. That was right about alarms and wrong about ownership: a comfort limit is
    the operating range's edge and a rot limit is the survival range's, both are the *plant's*,
    and an agent restating them privately kept a second copy of a public fact that it was free to
    get wrong. `water:bandLow` and `water:bandHigh` no longer exist.
  - **The band was never the bidder's.** The link traced under *"low moisture to auction"* still
    runs, but its first two steps moved: `annotate` and `urgency` are desire's, so an agent with
    a stake and no market still knows it is in trouble.
- **Nothing yet justifies a target against the range.** Still open, and sharper now that the
  range is derived: a region can move under a target that stays merely *legal* rather than still
  sensible. `capabilities/review/` could be asked to explain a pick within it rather than only to
  stay inside it.
- **Intention is still unnamed.** A bid and a voucher are the closest things to one, and neither
  is described in those terms. Whether that is a gap or a happy absence is not settled here —
  naming BDI's third letter for its own sake would add a word and no capability.
- **The ranges shipped are illustrative.** A synthetic world's figures, chosen so a succulent and
  a fern differ. Nothing measures them, and nothing here depends on their being right.
