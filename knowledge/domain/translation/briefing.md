---
type: Domain Concept
title: Briefing
description: >-
  What a translator hands the model before a person's words - who the agent is, what the chat lets the
  model read, by the vocabularies it may load, and the words a person may state in it - small on purpose,
  since the model loads and queries only what a question needs.
---

# What it is

A **briefing** is the context a [translator](/domain/translation/translator.md) gives the model ahead of
a person's words, as the system prompt of the one conversation that answers them. It says:

- **who the agent is** - its name, and its self graph where the [chat](/domain/speech/chat.md) reads it,
  with the label and comment of each [role](/domain/kernel/role.md) it plays, in its package's words;
- **what the chat lets the model read** - the kinds of graph the chat reads, and each vocabulary among
  them by the name the model loads it by, with its size; or, where the chat reads nothing, that it reads
  nothing;
- **what a person may state** - each word the chat allows, with what its domain says it is said of and
  what its range says it takes, and, where the chat reads nothing, the things of each domain by their
  labels, since the model can look none up; every word, where the chat allows `rdf:Property`; or that a
  person states nothing there.

All three change when a document does, so they are one block the model's provider may cache; what holds
now is the model's to query. Each turn of the conversation marks its last block for the
cache too, so the next turn pays in full only for what it adds. A name in the self graph, a vocabulary or a
query's rows is written with a prefix - the store's, a vocabulary's own, and one named for the agent's world by its namespace's last word - since
whole IRIs were most of what a turn re-sent.

# What it is not

It carries no vocabulary and no world. The model loads a vocabulary when a question needs its terms and
queries what the chat reads for the rest, so a message pays for what it asks about, and nothing in the
briefing is a list of what the agent can answer
([the-model-queries-what-its-chat-may-read](/decisions/the-model-queries-what-its-chat-may-read.md)).
