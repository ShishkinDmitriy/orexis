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
- passes over words that are someone else's and not this agent's: words that name another agent of
  the chat, by its id or the name it goes by, or that the carrier says tagged or replied to someone
  else; words the carrier says tagged or replied to this agent's own account are this agent's, as if
  they named it;
- opens a conversation with the model on any other words, briefed first with a
  [briefing](/domain/translation/briefing.md) - who the agent is, what the chat lets it read, and its
  status - and offered every [sayable](/domain/speech/sayable.md) the world declares, every askable the
  chat admits, and, where the chat reads anything, a vocabulary to load and a query to run over what it
  reads: a statement of the sayable filled is handed to speech's `heard`, and the domain's
  [extraction](/domain/speech/extraction.md) makes the belief; each askable called is answered from the
  store on the runtime's thread; each query runs over the chat's copy; the model calls as many as the
  message needs, then answers in words. Unaddressed in a group, the model is offered no sayable and told to
  say nothing where what the agent holds does not answer, so the agent that knows is the
  one heard. An answer replies to the words it answers, where the carrier threads.

From the words heard to the answer said, every member carrying the chat's channel is asked to show the
agent writing (`writing_in`, Telegram's `typing`), and again every few seconds while the model thinks;
unaddressed in a group, where the agent may well keep silent, it shows nothing. A model that fails is
said in the chat where the agent was addressed, so the person is not left waiting on nothing.

# Said

A document the agent says to a person — the TriG an `execution:Saying` made — reaches the part by
speech's `told`. It finds the sayable the document is a statement of, hands the model its fields and
who it is for, and sends the words through the person's own chat with the agent, or a group they are
in where they have none. A statement of no sayable's class is not rendered, and is said in the log.

# What it needs

A chat it is in, of which onboarding's [requirement](/domain/onboarding/requirement.md) holds a
translator; a model the installation names ([deployment](/domain/onboarding/deployment.md)), its key
mounted into this agent's container alone; and each carrier's secret where a chat goes through it —
`secrets/<agent>/telegram.env` for its bot, `secrets/<agent>/mail.env` for its mailbox.

# What it spends

Each use of the model - a message answered over a conversation's requests, a statement rendered in one - is
said as `Translated`, tagged by the act, how it ended and the model, with the requests and the tokens it spent
by the API's own names. Where the world is monitored the metrics part tallies it, and `orexis-dashboards` draws
it on the package's health dashboard, so what an agent's chats cost is watched beside its other figures.
