---
type: Domain Concept
title: Actuation
term: http://example.org/orexis/actuation#Valve
description: >-
  How a device an agent holds changes the subject it acts for - a valve dosing soil from a
  source, a heater warming air. A domain of documents - the devices and what they move in
  `domains/actuation/`, the heater in `domains/climate/` - whose actions predict a side and whose
  commands size the act from the present when a step is taken.
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

`actuation:Dosing` is admitted where a reading of what the valve moves lies `sensing:below` a range
of the subject it acts on. Its effect speaks the concept the rules conclude — the reading comes to
be `sensing:inside` — and not a number, since the search runs no rules. `climate:Heating` is the same
shape for air temperature and a heater.

How much is not the search's. The action's `execution:Command` runs over the present when the step
is taken and answers the device and the payload — for a dose, how far the reading is below the
middle of the range, by the subject's litres per fraction, at most the valve's cap — and the runtime
sends it through the [transport](/domain/transport/transport.md). The executor answers the step when the
next reading is revised inside.
