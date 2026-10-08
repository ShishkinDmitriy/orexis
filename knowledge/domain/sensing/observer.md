---
type: Role
title: Observer
term: http://example.org/orexis/sensing#Observer
description: >-
  An agent that turns its sensors' numbers into observations - the role whose part is sensing's.
  Declared in the agent's self graph, beneath the deliberator, since an observation's sides are
  revisions; it needs a sensor reporting to the agent, and a sensor reporting to an agent that is
  no observer is refused at onboarding.
---

# Who is one

An agent stated `sensing:Observer` beside its self — the terrace's, the sensing world's fern agent,
the greenhouse's grower, the allotment's growers. Declaring it loads [sensing](/domain/sensing/sensing.md)
and, because the role is beneath the [deliberator](/domain/belief/deliberator.md), belief too: what
sensing writes is a number, and which side of a range it lies on is concluded by sensing's own rules,
which only a deliberator runs. Without belief an observer would hold readings that are of nothing.

It is the one role the MQTT and HTTP transports are loaded for on a sensor's account: the MQTT member
where a sensor of the observer's publishes on a topic, the HTTP member where one is a thing with a
form ([transport](/domain/transport/transport.md)).

# What it needs

A sensor reporting to the agent — hosted by what it acts for, by a sample of that, or by a place
containing it. The shape saying so ships in sensing's own ontology, and `orexis-onboard` refuses an
observer whose world states none. The converse is refused too: a sensor that reports to an agent
that is no observer would deliver bytes no package of that agent reads
([role](/domain/kernel/role.md)).
