---
type: Decision
title: A forecast is a series a sensor reads, reached by its Thing Description
status: accepted
timestamp: 2026-09-28T21:00:00Z
description: >-
  The sovereign's choices for #851, made 2026-09-28. A weather service is a sosa:Sensor that
  reads a SERIES; sensing writes one sensing:ForecastGraph per stretch, holding during it, and
  the next forecast replaces the last. The service is reached over HTTP by a transport member
  that adopts the W3C WoT Thing Description as it stands, its target a URI template the
  place's schema:geo fills. The location is private and lives in a world's secrets/, which a
  boot reads. The runtime holds several members. Refused - the member writing beliefs, the
  endpoint in a deployment graph, the location in the world graph, and the agent acting for
  the place.
---

# The claim

**A forecast service is a sensor, and what it reads is a series.** SOSA admits software as a
`sosa:Sensor`, and a weather service observes a property - `climate:Precipitation` - of a
feature of interest, the place. What sets it apart is that one response carries many values,
each about a stretch ahead. A sensor stating `sensing:endsPointer` (or `sensing:startsPointer`)
beside its `sensing:readingPointer` reads a series: the one pointer finds the instants, the
other the values, and each value holds over the stretch between one instant and the next.
`received` writes one [forecast](/domain/sensing/forecast.md) graph per stretch still ahead,
`sensing:ForecastGraph` beneath `orexis:BeliefGraph`, holding during the stretch, and forgets
every forecast graph the sensor wrote before, so the next forecast replaces the last.

**Sensing asks for it when it falls due.** A pushed reading tells the agent it arrived; a series
must be pulled. `missed` answers a series sensor of the agent's as due when no forecast of its
stands, or when the one standing was issued a cadence ago, and the container nudges the
transport, which is the one way anything is fetched: no member keeps a timer.

**The service is reached by its Thing Description.** The HTTP member (`agent/transport/http/`)
adopts the W3C WoT Thing Description as MQTT's adopts MQTT4SSN: it declares no word, the sensor
is also a `td:Thing`, and its `td:hasForm` is an `hctl:Form` whose `hctl:hasTarget` is a URI
template. The template's variables are filled from the `schema:geo` of what the sensor is hosted
by, variable by local name - `{latitude}` from `schema:latitude` - so no code names a service, a
place or a coordinate. The response arrives on the member's thread and is queued, as a broker's
message is, and `handle` hands it to sensing.

**The runtime holds several members.** A world may reach its board over MQTT and its forecast
over HTTP, so the runtime connects every member whose premise holds and, where there is more
than one, holds them behind the family's `Transports`: a message goes back to the member that
queued it, and a nudge or a command to the member that `reaches` the sensor or the actuator.

**A sensor of the agent's may be hosted by the place its subject is in.** The forecast is of the
terrace, and the agent acts for the bed. A sensor is the agent's when it is hosted by what the
agent acts for, a sample of it, or a place that contains it (`schema:containedInPlace`); the
premises and the MQTT member read it the same way.

**The location is private, and lives in the world's `secrets/`.** Where a home is, is not a thing
to publish with a world. A document in a world's `secrets/` is read by a boot like any other of
the world's and mounted by `orexis-compose`, and `secrets/` is not committed. A world without it
still boots; its forecast cannot be asked for, and the member says so.

# What was refused

- **The member writing the forecast graphs**, which #851 first said. A transport hands bytes and
  the translation row writes beliefs ([the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md));
  a member that wrote graphs would be a second translation, and sensing's due, silence and
  keying would be rebuilt beside it.
- **The endpoint in a deployment graph, told as environment.** A broker's address is the
  installation's or allocated by it, and the agent is told it so no world names the host
  (#823, #839). A public service's address is neither: it is how the sensor is reached, as a
  topic is, and it belongs with the wiring the agent reads. Onboarding would have written one
  variable per source for no isolation it buys.
- **The location in the world graph.** It would be committed.
- **The agent acting for the place.** `orexis:actsFor` is read as one subject where a rule binds
  `$subject` (`take.py` asks with `LIMIT 1`), and the terrace is not what the agent cares for; the
  place contains what it does.

# Seams left open

- **A forecast reaches the soil's prediction at the soil's next reading.** `predict` runs for a
  sensor that has just reported, and the forecast sensor has no stretch of its own to predict.
- **A series sensor is asked only on a pass that received something**, since `missed` runs there;
  that is [#843](https://github.com/ShishkinDmitriy/orexis/issues/843).
- **A silent forecast service is not said silent**, and no forecast is told to history: a point
  stamped in the future is not what a series store is watched for.
- **A time with no offset is UTC**, as a service asked in GMT answers.
