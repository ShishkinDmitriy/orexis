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
payload a step's command answers (`actuate`), and say whether it `reaches` a sensor or an
actuator. A message arrives on the member's thread and is queued; the container's one thread
handles it. Where more than one member is loaded, the container holds them behind `Transports`,
which hands a message back to the member that queued it and a nudge or a command to the member
that reaches its device.

Whether a member is loaded at all is not asked of it, since asking would import it: it is the
member's premise, read off the world before anything of the member is
([package](/domain/kernel/package.md)). A member imports sensing's `received` and speech's `heard`
only where a message is for one of them, so an agent that only listens never loads sensing.

# The member that ships: MQTT

It adopts MQTT4SSN as it stands and declares no word of its own. A sensor
`mqtt4ssn:observesTopic` a topic, a board `mqtt4ssn:listensToTopic` another, and a topic is named
by the `mqtt4ssn:hasFilterPattern` of the filters that match it: the agent subscribes by the
pattern and publishes a command to a pattern with no wildcard. Which sensors are the agent's is
derived — those hosted by what it acts for, a sample of it, or a place that contains it — and
never authored. The broker's address and the
agent's credential come from the environment (`MQTT_HOST`, `MQTT_USERNAME` and the rest), which
[onboarding](/domain/onboarding/onboarding.md) writes; the member refuses to guess one.

A peer's document travels the same way: `tell` publishes it on the topic the recipient listens to,
and one arriving is handed to [speech](/domain/speech/speech.md)'s `heard`.

# The member that ships: HTTP

It adopts the W3C WoT Thing Description as it stands and declares no word of its own. A sensor
reached over HTTP is also a `td:Thing`, and its `td:hasForm` is a form whose `hctl:hasTarget` is a
URI template; `{latitude}` and `{longitude}` are filled from the `schema:geo` of what the sensor is
hosted by, variable by local name. `sense_now` fetches it on a thread of its own, once at a time
and not again within a minute of the last attempt, and the response is queued like a message.
The one sensor it serves today is a [forecast](/domain/sensing/forecast.md) service, whose
address is public and is read off the world, not told
([a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md)).
