---
type: Service
title: Transport
description: >-
  How an agent reaches the devices, services and peers of its world - a family whose contract the
  container holds (`agent/transport/transport.py`), with two members that ship: MQTT, speaking
  MQTT4SSN, and HTTP, speaking the WoT Thing Description. It hands sensing bytes, sends what a
  step commands, and carries documents between agents; sensing and speech know nothing of it.
---

# The contract

What the container asks of any member: bring itself up from the environment (`connect`, handed
the container's `deliver`), subscribe to the agent's
channels (`open`), turn a message into observations by calling sensing's `received` once per
sensor it is for (`handle`), and send what a device may be told — a cadence, a sense-now, and the
payload a step's command answers (`actuate`), say whether it `reaches` a sensor or an actuator,
and **start itself** (`start`, handed the runtime): its thread's messages submitted as jobs the
runtime's one thread runs, what it listens on opened, what it does of its own accord scheduled, and
the agent held running, since what it senses goes on arriving. A member is a [part](/domain/kernel/part.md) of its own:
execution's part and speech's, linked to it, hand it a step's command (`command`) and a document
told (`tell_to`), which it sends where it reaches the recipient. Several are held behind
`Transports`, which sends a nudge or a command to the member that reaches its device.

Whether a member is loaded at all is not asked of it, since asking would import it. A transport is
no [role](/domain/kernel/role.md) and no author declares one: the runtime loads a member where a role
the agent is declared in needs bytes and the society wires a bus — MQTT for an
[observer](/domain/sensing/observer.md)'s sensor on a topic or a [speaker](/domain/speech/speaker.md)
listening to one, HTTP for an observer's sensor with a form — read off the world before anything of
the member is ([package](/domain/kernel/package.md)). A member imports sensing's `received` and
speech's `heard` only where a message is for one of them, so an agent that only listens never loads
sensing. The MQTT member's ontology ships the speaker's one need, a topic it listens to, since a
topic is its word.

# The member that ships: MQTT

It adopts MQTT4SSN as it stands and declares no word of its own. A sensor
`mqtt4ssn:observesTopic` a topic, a board `mqtt4ssn:listensToTopic` another, and a topic is named
by the `mqtt4ssn:hasFilterPattern` of the filters that match it: the agent subscribes by the
pattern and publishes a command to a pattern with no wildcard. Which sensors are the agent's is
derived — those hosted by what it acts for, a sample of it, or a place that contains it — and
never authored. The broker's address and the
agent's credential come from the environment (`MQTT_HOST`, `MQTT_USERNAME` and the rest), which
[onboarding](/domain/onboarding/onboarding.md) writes; the member refuses to guess one. Started, it
asks every minute of the timeline after its sensors' missing readings, telling each such board to
sense now.

A peer's document travels the same way: `tell` publishes it on the topic the recipient listens to,
and one arriving is handed to [speech](/domain/speech/speech.md)'s `heard`.

# The member that ships: HTTP

It adopts the W3C WoT Thing Description as it stands and declares no word of its own. A sensor
reached over HTTP is also a `td:Thing`, and its `td:hasForm` is a form whose `hctl:hasTarget` is a
URI template; `{latitude}` and `{longitude}` are filled from the `schema:geo` of what the sensor is
hosted by, variable by local name. Started, it polls each sensor at once and then every
`ssn-system:Frequency` the sensor states; a fetch runs on a thread of its own, one at a time per
sensor, and the response is submitted like a message.
The one sensor it serves today is a [forecast](/domain/sensing/forecast.md) service, whose
address is public and is read off the world, not told
([a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md)).
