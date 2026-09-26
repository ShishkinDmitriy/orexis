---
type: Service
title: Transport
description: >-
  How an agent reaches the devices and peers of its world - a family whose contract the container
  holds (`agent/transport/transport.py`) and whose member that ships is MQTT, speaking
  MQTT4SSN. It hands sensing bytes, sends what a step commands, and carries documents between
  agents; sensing and speech know nothing of it.
---

# The contract

What the container asks of any member: bring itself up from the environment (`connect`, handed
the container's `deliver`), say whether it reaches a sensor (`claims`), subscribe to the agent's
channels (`open`), turn a message into observations by calling sensing's `received` once per
sensor it is for (`handle`), and send what a device may be told — a cadence, a sense-now, and the
payload a step's command answers (`actuate`). A message arrives on the member's thread and is
queued; the container's one thread handles it.

# The member that ships: MQTT

It adopts MQTT4SSN as it stands and declares no word of its own. A sensor
`mqtt4ssn:observesTopic` a topic, a board `mqtt4ssn:listensToTopic` another, and a topic is named
by the `mqtt4ssn:hasFilterPattern` of the filters that match it: the agent subscribes by the
pattern and publishes a command to a pattern with no wildcard. Which sensors are the agent's is
derived — those hosted by what it acts for — and never authored. The broker's address and the
agent's credential come from the environment (`MQTT_HOST`, `MQTT_USERNAME` and the rest), which
[onboarding](/domain/onboarding/onboarding.md) writes; the member refuses to guess one.

A peer's document travels the same way: `tell` publishes it on the topic the recipient listens to,
and one arriving is handed to [speech](/domain/speech/speech.md)'s `heard`.
