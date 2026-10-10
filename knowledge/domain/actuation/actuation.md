---
type: Domain Concept
title: Actuation
term: http://example.org/orexis/actuation#Valve
description: >-
  How a device an agent holds changes the subject it acts for - a valve dosing soil from a
  source, a heater warming air. A domain of documents - the devices and what they move in
  `domains/actuation/`, the heater in `domains/climate/` - whose actions take the subject, predict
  its state in climate's words, and whose commands size the act from the present when a step is
  taken.
---

# What a world states

```turtle
:agent actuation:hasActuator :pump .
:pump a actuation:Valve ; actuation:actuates :bed ; actuation:actuatesProperty climate:SoilMoisture ;
      actuation:drawsFrom :barrel ; actuation:mlPerSecond 20 ; actuation:maxDoseMl 500 .
```

An agent may take a step only through a device it `actuation:hasActuator`: a grower that wins
water still cannot open the supplier's valve.

# The dose, and the heating

`actuation:Dosing` takes a valve and a [subject](/domain/actuation/subject.md), and is admitted where
the subject's [soil](/domain/actuation/soil.md) is believed `climate:Dry` and the valve moves its soil's
moisture. Its effect speaks the state the soil's transition concludes — dry is deleted and
`climate:Moist` inserted — and no number, since the search runs no rules and the mind reads no
reading (#944). `climate:Heating` is the same shape for a heater and the subject's
[air](/domain/actuation/air.md), `climate:Cold` to `climate:Comfortable`. Each lands within a cadence
of its sensor, found through the world's description since no belief says when the subject is next
revised.

How much is not the search's. The action's `execution:Command` runs over the present when the step
is taken and answers the device and the payload: for a dose, how far the subject's latest reading is
below the middle of the range, by the subject's litres per fraction, at most the
valve's cap. The runtime sends it through the [transport](/domain/transport/transport.md). The
executor answers the step when the next reading's transition says the soil moist. A dose the agent
is committed to is a flow its subject's prediction accumulates (`domains/actuation/drifts.ttl`), its
rate read off the committed step's subject and that subject's observation — prediction is the other
reader of the number, an estimator at the boundary.
