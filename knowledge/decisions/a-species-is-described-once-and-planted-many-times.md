---
type: Decision
title: A species is described once and planted many times
description: >-
  Zamioculcas zamiifolia gets its own package, shaped exactly like a part's — a species is a
  model and the pots are units, so its care is stated on the class and reaches each pot by
  owl:hasValue. It states TWO ranges, because SSN has both words and this plant is the case
  that needs them: OperatingRange is where it grows and SurvivalRange is where it does not
  die, and the gap is asymmetric because the dry end is enormous and the wet end is a cliff.
  Also answers the structural question that prompted it — vocabulary packages already ARE
  capability-shaped, and the only difference is Python they have no use for.
status: accepted
timestamp: 2026-08-12T00:00:00Z
---

> **Current statement: [model-and-unit](/domain/model-and-unit.md).** This record is one
> application of a principle four of them share; the domain concept states the principle
> and the mechanism once.

# The structural question first, because it dissolved

The request came with a preference: *one feature has all it needs — ontology, scripts* — and a
suggestion that `packages/part/dht11/` should be restructured to match a capability.

**It already is, and nothing needed moving.** Measured rather than assumed:

| | capability | vocabulary package |
|---|---|---|
| how it is found | `loader.packages()` — "found by looking. Nothing is named" | the same call, same rule |
| `ontology.ttl`, `shapes.ttl`, `rules.ru`, `review.rq` | any subset | the same subset — `packages/core/agora/` carries a `rules.ru` |
| its own namespace | declared in its ontology | the same, and `loader.prefixes()` picked up `zz:` with no registry edit |
| Python | `__init__.py` with `PROVIDES` | **none** |

The one difference is deliberate and already written down in `loader.py`: *"vocabulary has no
Python at all"*, and *"A package with no `__init__.py` is knowledge only, and that is a legitimate
kind of package: the domain contributes vocabulary and no behaviour."* A part has no behaviour a
runtime could load — the BOARD talks to a DHT11, and nothing in this repository speaks one-wire.
Adding a `terms.py` nobody imports would be structure for its own sake.

So the division the request liked is the division that exists. What was missing was a package on
the *plant* side of the domain, and that is what this record is about.

# A species is a model, and a pot is a unit

`packages/plant/zamioculcas/` is deliberately the same shape as `packages/part/dht11/`, because the
underlying situation is the same one:
[a part is described once and fitted many times](/decisions/a-part-is-described-once-and-fitted-many-times.md).
A datasheet describes a model and a world names the soldered units; care guidance describes a
species and a world names the pots. So the facts go on the class, once, and reach each pot by
`owl:hasValue` — the construct the closure materialises.

What a world writes when it acquires one:

```turtle
ag:pot_by_the_window a zz:ZamioculcasZamiifolia ;
    ag:localId "zz" ; water:servedBy ag:tap ; water:litresPerFraction 2.0 .
```

That is the whole of it. Eight conditions — two ranges across four properties, one of which
nothing measures — arrive from the package. Nothing about how to look after a Zamioculcas is written in a world, and a second one is
one triple.

**What stays per-pot is what is about the pot**: `water:driesPerDay` is how fast *this* pot
dries, which depends on the pot, the position and the soil, not on the species.

# Two ranges, because this plant is the case that needs them

SSN has both words and we had used neither. `ssn-system:OperatingRange` is where the plant grows;
`ssn-system:hasSurvivalRange` is where it does not die. For most things that distinction is
decoration; for a Zamioculcas it is the entire care instruction, because **the gap is asymmetric**.
It stores water in rhizomes, so the dry end of survival is enormous and the wet end is a cliff: it
returns from bone dry and does not return from a rotted rhizome.

The codebase had already reached for this split without a term. `water:bandLow` is documented as
*"a comfort limit, desire-relative — not the rot limit, which is physical and the constitution's."*
The rot limit is the survival range's ceiling, and it is a fact about the **species** rather than
about anyone's desire, which is why it now lives here.

`water:RangesAgreeShape` refuses a species whose operating range leaves its survival range, per
property. That is arithmetic rather than horticulture, so it is stated once for all plants rather
than in each species package — and it catches the edit that actually happens, which is a ceiling
raised in one range and not the other.

# What it buys, in one test

`world/simulation`'s fern agent wants 0.55 — correct for a fern. Replant that pot as a Zamioculcas,
change nothing else, and **the agent refuses to start**:

> the target sits outside the operating range the plant states for that property — a desire is a
> pick within a range, not a number of its own

Nothing about the agent changed. The plant did. That is
[the range is the plant's and the pick is the agent's](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)
with a species behind the range, and it is the reason to describe a species at all rather than
writing 0.20 into a beliefs file and hoping.

# Light, and a range for a property nothing measures

Light was left out of the first version on the grounds that no `sosa:ObservableProperty` for it
existed and nothing senses it. The first half was a reason to **add the term**, not to stay silent;
the second half turned out not to be a reason at all.

`water:Illuminance` went into the **domain** package rather than this one, and that placement is
the general rule: light is nobody's species in particular, so `zz:Illuminance` would have made
every other plant borrow a term from the Zamioculcas. It sits beside `water:AirTemperature` and
`water:AirHumidity`, which are no more "water" than it is — a property earns its place in that
module by being something a plant cares about. The module's own header said *"soil moisture and
water"* and had been wrong since the temperature sensor landed; it says what it holds now.

**A range for an unmeasured property is worth stating.** Nothing in this repository reports lux,
and the range is still a checkable fact about the plant rather than a sentence in a comment — it
becomes live the day a light sensor appears, with no edit to this package. `water:RangesAgreeShape`
already covers it, because that rule is per-property: raising the operating ceiling to direct
sunlight is refused with no shape change at all.

The provenance differs from the other three and is the part most likely to be over-trusted. The
**lux bands are a convention**, not a measurement — "low light", "bright indirect" and "direct sun"
are the categories houseplant sources are written in, at roughly 250-1000, 2500-10000 and 10000+
lux. What is guidance about *this* plant is where it sits in them: medium to bright indirect,
tolerant of low light beyond almost anything else sold, scorched by direct sun. **The bands are the
claim; the endpoints are a reading of them.**

# Where the figures come from, and where they do not

Stated in the ontology and repeated here because it is the part most likely to be trusted too far.
Temperature and humidity are ordinary published care guidance, in the units that guidance uses.
**The soil-moisture figures are not.** No horticultural source states a volumetric fraction for a
houseplant; care guidance says *"let it dry out almost completely"*, and the numbers here are that
sentence put on the 0-1 saturation scale `water:SoilMoisture` is denominated in. The durable claim
is the **ordering** — a ZZ sits drier than a succulent, far drier than a fern, and its ceiling is a
cliff rather than a preference. The exact numbers belong to whoever calibrates a real pot with a
real probe.

# Seams left open

- **Toxicity.** The sap is a calcium-oxalate irritant. It is a fact someone caring for one should
  meet and there is nothing in this system it could inform, so it stays in the class comment where
  a person will read it. No term would fix that — unlike light, below.
- **Winter is the regime this plant most obviously needs**, and it is still unsayable for the
  reason recorded on the previous decision: `ssn-system:inCondition` cannot mark which of its
  conditions is the qualifier. A ZZ genuinely wants *less water* in winter rather than the same
  water less often, so it is the example to reach for when that is finally built.
- **One species, and no second to generalise from.** Whether every species wants its own package
  or a `species.ttl` per world is a question a second one will answer better than argument.
- **The agent cannot want most of what the species states.** Temperature and humidity ranges are
  now expressible and no agent can hold a desire in them — [#110](https://github.com/ShishkinDmitriy/agora/issues/110).
