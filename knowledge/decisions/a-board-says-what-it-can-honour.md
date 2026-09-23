---
type: Decision
title: A board says what it can honour, in SSN's words rather than ours
description: >-
  The third source `ranges()` has always named — constitution, mandate, hardware — existed
  only in a docstring, so an agent could commit to a cadence its board would never keep and a
  healthy board would read as a quiet one. A device now states an ssn-system:Frequency,
  qualified by a Condition because SSN puts "under the defined Conditions" in the definition
  itself. Borrowed and not imported, which cost one axiom: SSN's own sosa:Sensor
  rdfs:subClassOf ssn:System, restated here because borrowing an IRI brings its definition and
  none of the axioms other documents state about it.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

`ReviewModule.ranges()` has documented three narrowing sources since it was written — *"the
constitution, narrowed by this agent's mandate. Hardware limits when any exist."* **None existed.**
[a-belief-is-a-pick-within-a-range](a-belief-is-a-pick-within-a-range.md) names the same three and
[self-review-is-a-capability](self-review-is-a-capability.md) tabulates them, and for both the
hardware row was aspiration.

The world says how a device is **driven** — `sensing:senseMode`, from which its agent's
capability is derived — and never what it can **do**. So an agent could be committed to a
ten-second cadence a board would not keep, `stale_after_s` would compute freshness from the
interval it *asked* for, and every reading would arrive later than expected: **a healthy board
reading as a quiet one**, which is [#53](https://github.com/ShishkinDmitriy/orexis/issues/53)
reached from the other direction.

# The term already existed, and its definition is why

Not invented. SSN's System capabilities module says exactly this, and the definition is worth
quoting because it decides the shape of everything below:

> **`ssn-system:Frequency`** — *"The smallest possible time between one Observation, Actuation, or
> Sampling and the next, under the defined Conditions."*

Two things follow. It is a **time and not a rate**, despite the name — the smallest gap — so it
reads as a floor and maps onto `review:notBelow` with nothing to convert. And **"under the defined
Conditions" is in the definition itself**, which is why a capability is qualified by an
`ssn-system:Condition` rather than being one number with a caveat: *ten seconds on mains* and
*fifteen minutes on battery* are two capabilities of one device, and
[#78](https://github.com/ShishkinDmitriy/orexis/issues/78)'s whole argument is that the right wake
depends on the power budget.

The prose specification truncates before this term in every rendering tried. It came from the
content-negotiated Turtle at `http://www.w3.org/ns/ssn/systems/`, which is the general lesson:
**for a definition, read the RDF, not the document about it.**

## What this project adds is the number

SSN deliberately leaves values to other vocabularies, so schema.org's `value`/`unitCode` pair
carries it — the idiom the W3C's own worked example uses, adopted in place of a term of ours by
[one-word-for-one-relation](one-word-for-one-relation.md). The class says which end it is; the
properties say how far and in what. A device that can be read no faster than every thirty seconds
states `[ a ssn-system:Frequency , schema:PropertyValue ; schema:value 30 ; schema:unitCode
unit:SEC ]`.

# Borrowed, not imported — and this one cost an axiom

The rule [settlement-speaks-rea](settlement-speaks-rea.md) set for ValueFlows and
[a-board-is-a-platform](a-board-is-a-platform.md) for SOSA: reference the IRIs, load none of the
ontology, add nothing to `agent_old/inference.py`'s hand-materialised closure.

**It does not come free here, and the reason generalises.** `ssn-system:hasSystemCapability` hangs
off an `ssn:System`, and what makes that reach a sensor is `sosa:Sensor rdfs:subClassOf
ssn:System` — asserted in `http://www.w3.org/ns/ssn/`, which is **neither SOSA nor the systems
module**, and which nothing here loads. Measured before the line existed: three things typed
`sosa:Sensor` in `world/sensing`, **zero** typed `ssn:System`. The module would have attached to
nothing at all, silently, because an empty result is not an error.

So:

> **Borrowing an IRI brings its DEFINITION and none of the axioms other documents state ABOUT
> it.** For each borrowed term, ask whether what makes it apply arrives with the IRI or has to be
> restated.

`mc:carries rdfs:subPropertyOf sosa:hosts` was the same move from the other direction, and this is
the second instance — enough to call it the shape rather than the exception.

It is restated in `packages/orexis-capability-sensing/ontology.ttl`, not in the kernel's `agent_old/ontology.ttl`, though the
subject is a class this package does not own. The axiom is load-bearing only because sensors have
capabilities, and sensing is where a sensor is; the kernel would be asserting it on behalf of a
package that may not be installed.

# How the limit reaches the agent

A limit is stated on a **device** and needed by an **agent**, because `ranges()` narrows a belief
and a belief is the agent's. So a rule carries it across `sensing:polls` at genesis, into
`review:limitedTo` on the agent — derived, never typed, landing in `graph/world/derived` like
every other conclusion.

**`MAX`, and that is the whole of the arithmetic.** An agent reads all its sensors on one wake, so
it can go no faster than its slowest device. Taking the minimum would ask the slow board for a
cadence it never keeps — the exact failure this exists to prevent, arrived at from the other side.

`review:limitedTo` is shaped like a `review:Mandate` and deliberately is not one. Both narrow
the same term the same way, so `ranges()` intersects them with one alternation and one arithmetic —
but **a mandate is a governance fact somebody ratified and could have written differently, and this
is a fact about a board that nobody chose.** Collapsing them would make `review:commits` mean two
things and lose which of the two refused a revision.

## Said twice, and held to agreeing

A part's floor is a datasheet fact, so it lives on the **class** in the vocabulary — every DHT11
has it, unlike `probe:rawDry`, which is measured per probe in the pot it sits in. An agent is never
given the wiring, so the society restates it on each sensor that part hosts.

**How the class states it was wrong here, and is fixed.** This record wrote it as
`dht11:Dht11 ssn-system:hasSystemCapability […]` — punning, which says the class has a capability
and entails nothing about any DHT11 in the world. It is an `owl:hasValue` restriction now, and
`agent_old/inference.py` materialises it onto the device the wiring declares. The society's copy is
therefore a projection of something entailed rather than a second hand-written assertion, and the
repetition survives for a reason this record only half stated: not "an agent is never given the
wiring" as a matter of file layout, but **an agent may know a part's properties and not its
identity**. See
[what-is-true-of-a-part-is-true-of-every-one-of-them](what-is-true-of-a-part-is-true-of-every-one-of-them.md).

`test_the_society_repeats_every_limit_the_wiring_states` holds the two together, following
[a-board-is-a-platform](a-board-is-a-platform.md)'s guard. **Not symmetric, and for a different
reason than that one.** There, a hardware-only part must not be forced into the society. Here, a
society *may* state a floor the wiring does not: a simulated device has no part and no datasheet,
and a deployment that knows its board wakes slowly on battery is stating something true no class
declares. Extra is allowed; missing and contradicting are not.

# And a shape refuses a world that contradicts its own hardware

`MandateWithinTheConstitutionShape` checks what the **society** permits anyone;
`MandateWithinWhatTheEquipmentCanHonourShape` checks what the **hardware** permits this one. Both
stated ends of a mandate must sit inside what the board can honour — a floor below it claims a
cadence the device will never keep, and a ceiling below it leaves no legal value at all.

Only **stated** bounds are checked. A mandate naming neither inherits the constitution and has
claimed nothing, so the shape refuses an author who contradicts a datasheet rather than one who
did not repeat it.

# Nothing shipped is slower than the constitution, and that is stated rather than hidden

The KY-015 declares two seconds — its specified sampling period, below the society's own floor of
ten. **So the mechanism constrains nothing in this repository today.** The capacitive probe
declares nothing at all, because an ADC read has no meaningful floor, and absence is the ordinary
case rather than a gap.

That is the honest outcome and the alternative was worse: inventing a hardware fact nobody measured
to make a demonstration. The binding path is proved by tests that state a floor above the
constitution on a mutated world, which is how every shape here is proved.

# What was mapped and deliberately not taken

The module has terms three open issues would otherwise invent. Recorded, unused, because adopting
terms nothing uses is how a vocabulary rots:

| issue | terms |
|---|---|
| [#78](https://github.com/ShishkinDmitriy/orexis/issues/78) — the wake a shared channel resolves to | `ssn-system:OperatingPowerRange`, `BatteryLifetime` — *"Total useful life of a System's battery in the specified Conditions"* |
| [#26](https://github.com/ShishkinDmitriy/orexis/issues/26) — interpreting raw counts | `MeasurementRange` (*"the set of values the Sensor can return"*), `Accuracy`, `Resolution`, `Drift` (*"a continuous or incremental change in the reported values over time for an unchanging Property"*), `MaintenanceSchedule` |

`Drift` is the one to notice: it is the reason a calibration is re-run, so #26's calibration mode
has a term for *why* before it has one for *how*.

# Consequences

- **`ranges()`'s third source is real.** Its docstring stops describing something that does not
  exist, which it did from the day it was written.
- **A second borrowed-axiom case.** After `mc:carries`, this is the pattern: the check is whether
  an alignment is a definition or an axiom, and axioms have to be restated.
- **`ssn:` is in the kernel prefix list for exactly one axiom** and would otherwise not be there.

# Seams left open

- **Only a floor.** `ssn-system:Frequency` is the smallest gap; SSN has no term for the largest,
  and none was invented. A board that must be read *at least* every hour cannot say so.
- **One condition each.** Every shipped device states a single `Condition`, so the qualifier is
  modelled and unexercised — the machinery for *ten seconds on mains, fifteen on battery* exists
  and nothing here is battery-powered.
- **The carry is per-agent, not per-sensor.** An agent polling a fast board and a slow one is held
  to the slow one for *both*, because a cadence is a property of the wake and
  [#78](https://github.com/ShishkinDmitriy/orexis/issues/78) owns whether one board may wake apart
  from another.
- **Nothing checks a floor against reality.** A world may state that a board honours ten minutes
  when it honours ten seconds; the society believes it, exactly as it believes a topic.
