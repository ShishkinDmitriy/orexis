---
type: Capability
title: Actuation
term: actuation:Actuation
description: >-
  The power to touch the physical world, held by whoever OWNS the hardware and by nobody else —
  a plant agent that wins water still cannot open a valve, because it owns none. Never declared:
  it falls out of holding an actuator, which is the shortest premise any capability here has.
  What it can do is bounded twice over, by a validated claim and by the device's own cap, and
  the device enforces the second itself so that a bug upstream cannot become a flood. Dosing
  figures live on the DEVICE, so recalibrating is a genesis edit rather than a code change.
---

# What it is

**Actuation is the ability to drive actuators you own.** One capability, one member today, and
the shortest premise in the project: `?agent actuation:hasActuator ?device . ?device a
sosa:Actuator`. Hold a valve, get the capability.

**No plant agent has it.** Winning water is not the same as being able to open a valve — a
[claim](/domain/claim.md) is a claim *on the owner*, redeemed by the owner — and that separation
is what keeps a market from being a way to gain physical powers you were never wired for.

# The premise is ownership, and it is deliberately not a grant

Every other [capability](/domain/capability.md) here is granted by something arguable — a stake,
a mandate, a position in a market. This one is granted by *holding the thing*, and the reason to
keep it that blunt is that actuation is the only capability whose misuse is irreversible.

A world cannot hand an agent the power to actuate without also handing it a valve, and a valve is
a physical fact somebody wired. There is no path from "the world says so" to "it can pour water"
that does not go through plumbing.

# Bounded twice, and the second bound is the device's own

What a dose may be is limited in two independent places, and the redundancy is the design:

- **by the claim** — a validated, co-signed entitlement to a quantity, single-use;
- **by `actuation:maxDoseMl`** — the device's own cap, which the firmware enforces whatever
  arrives on the wire.

The second exists precisely because the first can be wrong. A bug in matching, a replayed claim
or a mistaken decimal reaches a device that will still not pour more than its cap, so the failure
mode is a short pour rather than a flood.

`actuation:mlPerSecond` and `actuation:maxDoseMl` live **on the device**, in the world — so
recalibrating a pump is a genesis edit, and nothing about it is a code change.

# A dose is timed by the valve, not by whose pot it fills

`min(litres, the cap) / the calibration` is the open-seconds, and it is a fact about the
**valve** — a host dosing a buyer's pot needs it exactly as much as an agent dosing its own. The
first version of the rule joined through the stake instead, so every market dose fell back to a
local computation and the single source held only for self-doses, which is the half that needed it
least.

That number is the [effect](/domain/effect.md)'s `ag:landsAfter`, and the same arithmetic goes on
the wire as the command's duration. Two copies would mean planning against one timeline and
verifying against another, and the disagreement arrives looking like a device lying.

# An unconfirmed dose is not a delivered one

The valve reports that it opened; only a later [reading](/domain/reading.md) says the water
reached the pot. Those are different questions on different channels, and an agent that treats
the report as the outcome will keep dosing a pot the water never reached.

So the [intention](/domain/intention.md) that commits to a dose carries an expectation with a
baseline and a deadline, and the verdict lands beside the outcome — which is what makes
*satisfied-and-unmet* recordable rather than invisible.

# Related

- [executor](/domain/executor.md) — the supplier's actuation arm, and what it must never do.
- [claim](/domain/claim.md) — the entitlement a dose is opened against.
- [lever](/domain/lever.md) — a valve in the role it plays on a menu row.
