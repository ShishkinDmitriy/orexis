---
type: Domain Concept
title: Chat
term: http://example.org/orexis/speech#Chat
description: >-
  Who speaks with whom, through what - a standing thing of the society with its participants, an
  agent and a person, and its channel, the thing their prose goes through, whose type is the carrier.
  Speech names no carrier; each agent in it translates for itself, and onboarding derives the topic's
  name, the grants and each agent's carriers from it.
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
`schema:email` is mail, a `telegram:Chat` with the id the Bot API names it by is Telegram, in the
Telegram member's own words (`orexis-transport-telegram/ontology.ttl`). A chat may hold several agents
and several people: a group. A conversation
is one exchange inside a chat; the chat stands for as long as the world states it, as a sensor's topic
does.

An agent in a chat is a [translator](/domain/translation/translator.md): the chat says which of its
transport members' channels carry a person's prose rather than a reading or a peer's document, and to
whom what the agent says to a person goes. Onboarding reads it to wire the bus and to hand each agent
its carriers.

# Who connects for whom

A person does not connect to the bus; a **user agent** does, a client of the society that
`prov:actedOnBehalfOf` them — a phone, a terminal, an app — with a client id and a credential of its own,
as a board has. The agent in the chat publishes on its topic too, each message saying who said it, and
skips its own when the broker hands it back. On Telegram each agent speaks through a **bot** of its own,
`<agent> telegram:hasBot <bot>`, as a client is connected to a broker: where the bot answers is the
deployment's, its token a secret of the agent's; a person writes under a `telegram:userId`, which tells
who spoke in a group.

# What is derived from it

Onboarding names a chat's topic `chats/<chat>` and grants it to each agent in it and to every client
acting on behalf of a participant. [Requirements](/domain/onboarding/requirement.md) hold a chat to one
channel of a kind some transport carries, to a person and an agent in it, an agent in it to playing a
translator, and an agent in a chat on Telegram to a bot of its own.

# What its model may read

A chat says which kinds of graph the model speaking in it may read, `speech:reads`:

```turtle
:terrace_and_dmitrii a speech:Chat ;
    speech:participant :terrace_agent , :dmitrii ;
    speech:channel :sovereign_telegram ;
    speech:reads orexis:Graph , orexis:Event ;
    speech:allows rdf:Property .
```

The sovereign's chat reads everything; a broker's would read the market's kinds and no sensor. The
translator copies the graphs of those kinds, each under its name, when words arrive, and the model's
queries run over that copy and nothing else, whatever they say. A chat reading `orexis:Event` reads what
happened besides - the agent's [journal](/domain/kernel/journal.md) and its
[series](/domain/kernel/series.md), which are what events say - so what holds now is asked of the store
and what happened of the record. A chat stating no kind reads nothing
([the-model-queries-what-its-chat-may-read](/decisions/the-model-queries-what-its-chat-may-read.md)).

# What a person may state in it

A chat says which words a person may state in it, `speech:allows`: properties a vocabulary declares, or
`rdf:Property` for every one, as the sovereign's chat allows. What a person states is triples in those
words, each held to its property's domain and range, and believed as the world's word. A chat allowing
none hears questions alone, since a question writes nothing and what it may read is `speech:reads`
([a-person-states-what-the-chat-allows-in-the-worlds-words](/decisions/a-person-states-what-the-chat-allows-in-the-worlds-words.md)).
