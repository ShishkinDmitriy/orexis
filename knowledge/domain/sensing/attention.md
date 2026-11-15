---
type: Domain Concept
title: Attention
term: http://example.org/orexis/sensing#Attention
description: >-
  What an observer gives the sensors it reads - which they are, and how many cadences or readings
  pass before it doubts one. An agent plays one observer and that observer attends any number of
  times, each attention naming the sensors held to its two limits, so sensors judged by different
  figures are two attentions of one role and never two roles.
---

# What it is

A `sensing:Attention` is a node the [observer](/domain/sensing/observer.md) role points at by
`sensing:attends`, in the agent's [self graph](/domain/kernel/self.md):

```turtle
:courier_a a orexis:Self ;
    orexis:plays [ a sensing:Observer ; sensing:archivedIn :series ;
        sensing:attends [ sensing:sensor :fix_a_column , :fix_a_row ; sensing:stuckAfter 100000 ] ,
                        [ sensing:sensor :thermometer ] ] .
```

It carries two things and nothing else.

**Its sensors**, `sensing:sensor`, one or more. This is the statement that makes a sensor the agent's:
declared here and derived nowhere, so a probe moved into a pot the agent acts for stays unread until
an attention names it. Sensing answers the transports with the list (`cadence::sensors`), a member
subscribing or fetching in its own words, and `orexis-mqtt` grants the agent their topics.

**Its two limits**, `sensing:silentAfter` in cadences and `sensing:stuckAfter` in readings: when a
sensor of this attention is said [silent](/domain/sensing/silence.md) and when
[stuck](/domain/sensing/stuck.md). An attention stating neither is held to the defaults its shape
states in sensing's ontology, three and six, the one place those figures live; `missed`, `received`
and the stuck rule all ask `cadence::limit_of` or read the same two statements.

# Why it is not the role

The limits were the role's own, and a sensor wanting another figure was read by a second observer
role. That made an agent play two roles of one class told apart by nothing but a number, and left
what the package is told once for the whole agent — how often it asks, where its readings are
archived — stated on each of them, to be merged by whoever read it. A role instance is told from
another of its class by a context ([role](/domain/kernel/role.md)); two groups of sensors are no two
contexts, they are one observer attending twice.

# What it is held to

Sensing's requirement, at onboarding: an attention names a sensor; each limit is one whole number;
every sensor it names reports to the agent; and no sensor is named by two attentions, since it would
then have two limits and neither would be its.
