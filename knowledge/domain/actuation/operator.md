---
type: Role
title: Operator
term: http://example.org/orexis/actuation#Operator
description: >-
  A role an agent plays that operates devices - the role whose part is actuation's, depending on the
  executor, whose steps are what it carries out on a device. What a step commands is sent to the actuator
  through the transport member that reaches it; an agent holding an actuator plays one, and onboarding
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

What the device is told is, for now, the document the executor's command made; turning what to actuate into a
device's bytes, and keeping each act as a `sosa:Actuation`, is the operator's next work (#1220).
