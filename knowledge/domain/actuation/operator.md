---
type: Role
title: Operator
term: http://example.org/orexis/actuation#Operator
description: >-
  A role an agent plays that operates devices - the role whose part is actuation's, depending on the
  executor, whose steps are what it carries out on a device. What a step commands is made into the
  device's document and sent through the transport member that reaches it, and kept as `sosa:Actuation`s; an agent holding an actuator plays one, and onboarding
  refuses one that holds a device and plays none.
---

# Who plays one

An agent whose steps tell a device something: the greenhouse's grower, whose dose opens the pump and whose heating
turns on the heater; the allotment's supplier, the one agent holding the valves; and a courier of the lane or the
layby, whose drive is told to the van it acts for. Each says so in its self graph, `orexis:plays [ a
actuation:Operator ]`, beside its [executor](/domain/execution/executor.md), which it depends on.

An agent that `actuation:hasActuator` a device and plays no operator is refused at
[onboarding](/domain/onboarding/onboarding.md): its steps would be taken and no device told.

# What it does

The executor sizes a step's commands as the step is taken and keeps them as a command graph, saying
`execution:Commanded`; the operator hears it beneath `actuation:ActuatingTrigger` and, in `actuation:Actuating`,
sends each command to its actuator through the member of the agent's that reaches the actuator as a channel it is
sent on (`orexis_transport::Exchange::Sent`). It names no member: each adds itself to the agent's members as it makes
its core, and the operator reads them once every core is made
([the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop](/decisions/the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop.md)).
A command no member reaches is passed over, and said in the log.

What the device is told the operator makes: the command graph holds a row per setting, an actuator, a
`sosa:ActuatableProperty` of it and the value, and each actuator's values are written into one JSON document, each
at its property's `actuation:commandPointer` - `/dose_ml` for `actuation:DoseVolume`, `/heat_s` for
`climate:HeatingDuration`, `/to/x` and `/to/y` for a van's `courier:Column` and `courier:Row` - in the order of the
pointers, as sensing takes a reading out of a board's document at the sensor's `sensing:readingPointer`. A setting
whose property states no pointer is not set, and said in the log. What was sent is kept as the agent's own act, an
`actuation:ActuationGraph` of a `sosa:Actuation` per setting, the actuator, the property, the value and the instant;
what no member reached is in none.
