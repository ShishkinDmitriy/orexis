---
type: Role
title: Observer
term: http://example.org/orexis/sensing#Observer
description: >-
  A role an agent plays that turns its sensors' numbers into observations - the role whose part is
  sensing's, depending on the deliberator since what an observation is of is a revision. An agent plays
  one, which attends the sensors it reads and says how often sensing asks after them and where their
  readings are archived; onboarding holds the sensors it attends to where they are mounted, both ways.
---

# Who plays one

An agent that says it plays a `sensing:Observer` in its self graph — the terrace's, the sensing world's
fern agent, the greenhouse's grower, the allotment's growers:

```turtle
:grower a orexis:Self ;
    orexis:plays [ a sensing:Observer ; sensing:attends [ sensing:sensor :moisture_probe , :thermometer ] ] .
```

Playing it runs [sensing](/domain/sensing/sensing.md), and it depends on the
[deliberator](/domain/belief/deliberator.md), which the agent plays beside it: what sensing writes is a number,
and what it is of and its quantity are concluded by sensing's own rules, which only a deliberator runs. Without
belief an observer would hold readings that are of nothing ([role](/domain/kernel/role.md)).

It is the one role the MQTT and HTTP transports are loaded for on a sensor's account: the MQTT member
where a sensor the role reads publishes on a topic, the HTTP member where one is a thing with a form
([transport](/domain/transport/transport.md)).

# What it carries

**What it attends**, `sensing:attends`, each an [attention](/domain/sensing/attention.md): the sensors
it reads and the limits it holds them to. Sensors judged by different figures are two attentions of the
one role.

**How often its readings are archived**, `sensing:archivedEveryS` in the agent's seconds, where the role names a
series store (`sensing:archivedIn`); ten where it states none, read by `orexis-sensing-influxdb/`.

**How often sensing asks after its sensors**, `sensing:askedEveryS` in the agent's seconds: how long a
[silence](/domain/sensing/silence.md) may go unsaid, sixty where the role states none.

**One per agent.** What the role says besides its attentions is said to sensing once for the whole
agent, so a second observer role would be a second answer to one question: sensing refuses it as it
starts, which onboarding finds when it boots the agent to check its world.

# What it is held to

Onboarding holds the declaration to the world both ways. The shapes sensing ships refuse
an observer that attends nothing, and an attention naming a sensor reporting to the agent from nowhere — mounted on
nothing it acts for, a sample it carries (a [contact](/domain/courier/contact.md), #1003), a sample of
it that nothing carries, or a place containing it — a carried sample reports where it is carried, not to
what it stands for, so a receiver standing for the other van is the carrying van's (#1004). `orexis-onboard` refuses the converse:
a sensor mounted so that it reports to the agent, which no observer role of the agent's reads, would
deliver bytes no package reads ([role](/domain/kernel/role.md)). And a sensor itself states one
`ssn-system:Frequency`, sensing's requirement too: its silent limit is in cadences, and a sensor
stating no cadence, or two, could never be silent.
