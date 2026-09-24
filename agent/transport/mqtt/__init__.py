"""The MQTT transport of Agent 0.2.0: how an agent's sensors reach it over a broker, in MQTT4SSN's words.

**THE VOCABULARY IS MQTT4SSN'S, ADOPTED AS IT STANDS.** A board is a `mqtt4ssn:Client` that
`mqtt4ssn:hosts` its sensors and `mqtt4ssn:isConnectedToBroker` a `mqtt4ssn:Broker`; a sensor
`mqtt4ssn:observesTopic` the `mqtt4ssn:Topic` it publishes its observations on; a board that takes
commands `mqtt4ssn:listensToTopic` another. A topic is named only through the `mqtt4ssn:TopicFilter`s
that `mqtt4ssn:matchesTopic` it, each with its `mqtt4ssn:hasFilterPattern` — which is MQTT's own
shape, since a topic name is a valid filter — so the agent subscribes by the pattern and publishes a
command to a pattern with no wildcard in it. The agent is a `mqtt4ssn:Client` too. This package
declares no word of its own; its ontology imports MQTT4SSN and says which of its terms the code reads.

**WHAT IS DERIVED, NOT AUTHORED.** Which topics the agent listens to follows from what it acts for:
its sensors are those `sosa:isHostedBy` the subject it `orexis:actsFor`, or a sample of it, and their
topics' filters are its subscriptions. The world never says "the agent polls this sensor".

**THREE PARTS, AND THE SOCKET IS THE CONTAINER'S.** `Mqtt` implements sensing's `Driver` contract —
claims, subscriptions, own, cadence, nudge — and hands a command to whoever publishes for it.
`handle` is the listener: a message's topic and bytes, at an instant, become one call of sensing's
`received` per sensor of the agent's whose filter matches the topic. `Link` wraps an MQTT client the
container has connected — subscribes what the world implies, routes each message to `handle`, and
publishes what the driver hands it. The broker's address and credentials are deployment facts and
stay in the environment; nothing here reads a host or a port off the world.
"""
