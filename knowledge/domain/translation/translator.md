---
type: Role
title: Translator
term: http://example.org/orexis/translation#Translator
description: >-
  An agent that speaks with the people of its chats itself - the role beneath the speaker whose part
  is the translation package's. A person's words reach it through a transport member as prose and
  become a statement of a sayable or the question of an askable, answered from its store; a statement the
  agent says to a person is rendered by the model and sent back on the chat's channel.
---

# What it is

```turtle
:seeker a orexis:Self ;
    orexis:plays [ a translation:Translator ] , [ a belief:Deliberator ] .
:seeker telegram:hasBot :seeker_bot .
```

A **translator** is an agent that stands in its own [chats](/domain/speech/chat.md), declared in its
self graph as any [role](/domain/kernel/role.md) is. It is a [speaker](/domain/speech/speaker.md)
too, so what a person states is kept as any peer's document. Its part, `agent/translation/create.py`,
is linked to every transport member that says `prose` and to speech's `told`, and holds the language
model at the one run-time edge where a model translates
([an-agent-translates-for-itself](/decisions/an-agent-translates-for-itself.md)). The model's call
runs on a thread of its own, and what comes of it is submitted back as a job.

# Heard

A person's words arrive as `prose` from the member carrying the chat's channel — its bot, its
mailbox, the chat's topic — with the sender where the channel tells one. In the chat whose channel
they came on, the part:

- answers `/status` with the rows of every [askable](/domain/speech/askable.md) that takes no field,
  and asks no model;
- passes over words that name another agent of the chat and not this one;
- offers any other words to the model once, with every [sayable](/domain/speech/sayable.md) the world
  declares and every askable the agent holds as tools: a statement of the sayable filled is handed to
  speech's `heard`, and the domain's [extraction](/domain/speech/extraction.md) makes the belief; the
  askable called is answered from the store on the runtime's thread, and its rows phrased by the model;
- and, where nothing fits, answers from the status. Unaddressed in a group, the model is offered the
  askables alone and told to say nothing where the rows do not answer, so the agent that knows is the
  one heard.

# Said

A document the agent says to a person — the TriG an `execution:Saying` made — reaches the part by
speech's `told`. It finds the sayable the document is a statement of, hands the model its fields and
who it is for, and sends the words through the person's own chat with the agent, or a group they are
in where they have none. A statement of no sayable's class is not rendered, and is said in the log.

# What it needs

A chat it is in, of which onboarding's [requirement](/domain/onboarding/requirement.md) holds a
translator; a model the installation names ([deployment](/domain/onboarding/deployment.md)), its key
mounted into this agent's container alone; and each carrier's secret where a chat goes through it —
`secrets/telegram-<agent>.env` for its bot, `secrets/mail-<agent>.env` for its mailbox.
