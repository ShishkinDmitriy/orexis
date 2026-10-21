---
type: Domain Concept
title: Contact
term: http://example.org/orexis/courier#RelativeColumn
description: >-
  What a van's instruments see of another thing on the grid - a `sosa:Sample` the van carries, standing
  for a peer van it `isSampleOf`, a receiver, or for nothing named, a radar's slot; two sensors hosted by
  the contact report its column and row relative to the carrying van, inside the range each declares,
  and the courier's transitions add the van's own coordinates. A vector outside the declared range is
  a contact beyond the area the agent sees, believed nowhere. Identity is which contact reported,
  never a number in the reading.
---

# What it is

A contact is a `sosa:Sample` hosted by the van that carries it, with two `sosa:Sensor`s hosted by the
contact observing `courier:RelativeColumn` and `courier:RelativeRow`: the offset from the carrying van to
what the contact stands for, in the grid's own coordinates. The sovereign's picture is a radar that
shows numbers and a second instrument that says what the contact is; here both are numeric and the
identity is structural:

- **A receiver**, one contact per known van, `sosa:isSampleOf` that van, as a ship's AIS receiver keeps a
  track per vessel it has heard. Which van is in range is which contact reported a vector inside its range.
- **A radar slot**, a contact standing for nothing named, which the simulator fills with the nearest
  thing no receiver of that van identifies - a parked van, a fallen tree, a hedge. A slot is typed an
  [obstacle](/domain/courier/obstacle.md) by the world, and that is all a plan needs of it.

**Each sensor declares the area it sees**, an `ssn-system:MeasurementRange` with a least and a most
offset, which `domains/courier/requirements.ttl` holds a world to: the agent sees what its instruments
see and no further (the-grid-is-infinite-and-a-position-is-two-coordinates). An observer role reads a
contact's sensors as it reads the van's own, and onboarding admits them: a sensor on a sample the subject
carries reports to the agent that carries it, and to no agent of what it stands for
([observer](/domain/sensing/observer.md)).

# What the rules make of it

`relativeColumnRule` and `relativeRowRule` in the courier's `rules.ttl`, order 0 beside the fix's own
rules, read a contact's arriving offset and, where it is inside the sensor's declared range, add the
coordinate held of the carrying van and write the sum as the `courier:x` or `courier:y` of the peer the
contact stands for, or of the contact itself where it stands for nothing; outside the range they delete
the coordinate held and write none. So a contact beyond range is not a sentinel and not a silence: the
simulator reports a vector one past the most of each sensor, the rules believe no coordinate of it, and
the peer or the slot is believed nowhere, which frees the position it stood at. The range is the
instrument's own declaration, the one figure the simulator and the rules both read.

A contact is testimony about where a thing is, never about what it will do: a peer's position is a
present fact the [constraint](/domain/planning/constraint.md) keeps a plan out of, and what the peer
intends is asked of the agent that plays its [driver](/domain/courier/driver.md) (#923).
