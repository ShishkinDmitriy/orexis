---
type: Domain Concept
title: Chat
term: http://example.org/orexis/speech#Chat
description: >-
  Who speaks with whom, through what - a standing thing of the society with its participants, an
  agent and a person, and its channel, the thing their prose goes through, whose type is the carrier.
  Speech names no carrier; the translator stands in the chat for the person, and onboarding derives
  the topic's name and the grants from it.
---

# What it is

```turtle
:seeker_and_boris a speech:Chat ;
    speech:participant :seeker , :boris ;
    speech:channel :boris_topic .
:boris_topic a mqtt4ssn:Topic .
```

A **chat** is the standing fact that an agent and a person speak with each other, and through what. It
has **participants**, `speech:participant`: an agent of the society and a person it speaks with. It has
one **channel**, `speech:channel`: a thing of the carrier's own vocabulary, whose type says the carrier
and which speech does not name — a `mqtt4ssn:Topic` is the bus, a `schema:ContactPoint` with a
`schema:email` is mail, and a chat of a messaging service would be its own vocabulary's. A conversation
is one exchange inside a chat; the chat stands for as long as the world states it, as a sensor's topic
does.

The agent in a chat knows nothing of it. It says statements and hears them as with any peer, on the
inbox the person `mqtt4ssn:listensToTopic`, where the agent's MQTT member publishes to a person as to an
agent. What the chat adds is for the [translator](/domain/speech/translator.md), which stands in it for
the person, and for onboarding, which reads it to wire the bus.

# Who connects for whom

A person does not connect to the bus; a **user agent** does, a client of the society that
`prov:actedOnBehalfOf` them — a phone, a terminal, an app — with a client id and a credential of its own,
as a board has. The translator connects as the client that `translation:translates` the chats it stands
in. Both publish prose on a chat's topic, each message saying who said it, and the translator skips its
own when the broker hands it back.

# What is derived from it

Onboarding names a chat's topic `chats/<chat>` and grants it to the translator and to every client acting
on behalf of a participant; the agent in a chat is granted to write each person's inbox and the translator
to read them. The translator's [requirement](/domain/onboarding/requirement.md) holds a chat to one
channel of a kind it carries, to a person and an agent in it, each listening on an inbox, and to one
client translating it.
