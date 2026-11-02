---
type: Domain Concept
title: Briefing
description: >-
  What a translator hands the model before a person's words - its self graph, the common beliefs with
  the vocabularies' comments, and its status - so a question is answered by an agent that knows what it
  is, what it watches and what each word means, and the askables are asked only for what it holds now.
---

# What it is

A **briefing** is the context a [translator](/domain/translation/translator.md) gives the model ahead of
a person's words, as the system prompt of the one conversation that answers them. It has three parts:

- **who the agent is** - its self graph: the roles it plays and what each is over, the sensors an
  observer reads;
- **the world as the agent believes it** - every common belief, in Turtle with the store's prefixes:
  the world's places, devices and what each is mounted on, the society, and the vocabularies of the
  domains and packages it speaks, whose `rdfs:comment` says what each term means;
- **what it holds now** - its status, the rows of every [askable](/domain/speech/askable.md) that
  takes no field.

The first two change when a document does, so they are one block the model's provider may cache; the
status follows it and changes with every reading.

# What it is for

With it the model answers a question about what the agent IS - which bed it watches, what it can and
cannot do, what a sensor measures - without an askable for each, and calls the askables only for what
the agent holds now, as many as the question needs, over as many turns as it needs them.

# What it is not

It is read, never written back: the model writes no query and nothing it says is a belief, which is
the line [an-agent-gives-an-account-of-itself-and-the-model-only-reads-it](/decisions/an-agent-gives-an-account-of-itself-and-the-model-only-reads-it.md)
drew. It holds no percept, prediction or intention - those grow with time and are the askables' to
answer - and none of the agent's program: its actions, drifts, desires and rules.
