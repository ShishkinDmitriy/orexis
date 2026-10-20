---
type: Role
title: Observer
term: http://example.org/orexis/sensing#Observer
description: >-
  A role an agent plays that turns its sensors' numbers into observations - the role whose part is
  sensing's, beneath the deliberator since what an observation is of is a revision. It declares the
  sensors it reads and how long it lets them be silent or stuck; onboarding holds the sensors it
  declares to where they are mounted, both ways.
---

# Who plays one

An agent that says it plays a `sensing:Observer` in its self graph — the terrace's, the sensing world's
fern agent, the greenhouse's grower, the allotment's growers:

```turtle
:grower a orexis:Self ;
    orexis:plays [ a sensing:Observer ; sensing:sensor :moisture_probe , :thermometer ] .
```

Playing it loads [sensing](/domain/sensing/sensing.md) and, because the role is beneath the
[deliberator](/domain/belief/deliberator.md), belief too: what sensing writes is a number, and what it
is of and its quantity are concluded by sensing's own rules, which only a deliberator runs. Without
belief an observer would hold readings that are of nothing.

It is the one role the MQTT and HTTP transports are loaded for on a sensor's account: the MQTT member
where a sensor the role reads publishes on a topic, the HTTP member where one is a thing with a form
([transport](/domain/transport/transport.md)).

# What it carries

**The sensors it reads**, `sensing:sensor`. Which sensors are an agent's is declared here and derived
nowhere: a probe moved into a pot the agent acts for is not its sensor until a role says so. Sensing
answers the transports which they are (`cadence.sensors`), so a member subscribes to their topics and
fetches their forms in its own words and names none of sensing's, and `orexis-mqtt` grants each agent
the topics of the sensors its roles read.

**How long it lets them be silent or stuck**, `sensing:silentAfter` in cadences and
`sensing:stuckAfter` in readings, read per sensor off the role that reads it. Where the role states
none, the observer shape's `sh:defaultValue` holds — three and six — and that shape is the one place
the figure lives: `missed`, `received` and the [stuck](/domain/sensing/stuck.md) rule all read it. A
sensor judged by another figure is read by another observer role.

# What it is held to

Onboarding holds the declaration to the world both ways. The shape sensing ships refuses an observer
that reads no sensor, and one that reads a sensor reporting to the agent from nowhere — mounted on
nothing it acts for, a sample it carries (a [contact](/domain/courier/contact.md), #1003), a sample of
it that nothing carries, or a place containing it — a carried sample reports where it is carried, not to
what it stands for, so a receiver standing for the other van is the carrying van's (#1004). `orexis-onboard` refuses the converse:
a sensor mounted so that it reports to the agent, which no observer role of the agent's reads, would
deliver bytes no package reads ([role](/domain/kernel/role.md)). And a sensor itself states one
`ssn-system:Frequency`, sensing's requirement too: its silent limit is in cadences, and a sensor
stating no cadence, or two, could never be silent.
