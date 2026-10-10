---
type: Domain Concept
title: Soil
term:
  - http://example.org/orexis/climate#soil
  - http://example.org/orexis/climate#Dry
  - http://example.org/orexis/climate#Moist
  - http://example.org/orexis/climate#Wet
description: >-
  How a subject's soil is believed, in climate's words - dry, moist or wet by its moisture against
  the subject's operating range, held past the range's margin - as climate's soil transition makes it
  of each soil-moisture observation arriving.
---

# What it is

```turtle
:bed climate:soil climate:Dry .
```

The **soil** of a subject is the state it is believed in for `climate:SoilMoisture`: `climate:Dry`
under the floor of the subject's operating range for it, `climate:Moist` within, `climate:Wet` over
the ceiling. It is a [subject belief](/domain/belief/transition.md), one state per subject.

Climate makes it: `climate:soilRule` (`domains/climate/rules.ttl`) is a
[transition](/domain/belief/transition.md) triggered by every reading, acting where the observation
is of soil moisture. It reads the reading, the operating range of the observation's feature of interest
or what that is a sample of, the range's [margin](/domain/sensing/margin.md), and the soil held
before; it deletes that and inserts the new state. Words, hold and all are climate's, since what
a dry bed is, and when it stops being one, is climate's meaning.

A bed believed dry at 0.2990 stays dry at 0.3001 with the greenhouse's margin of 0.0002, and is moist
at 0.3002; a moist bed reading 0.2999 is dry at once.

# Who reads it

The mind, and nothing of it reads the soil's readings instead (#944). The greenhouse's and both
allotment growers' desires ask that no subject they act for is believed dry; the
[dose](/domain/actuation/actuation.md) and the market's presenting are admitted where it is, and
their effects delete `climate:Dry` and insert `climate:Moist`. A ground the planner lays ahead holds
the soil a predicted reading's transition makes there, beside the soil the ground before held
([transition](/domain/belief/transition.md)).
