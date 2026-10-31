---
type: Domain Concept
title: Account
description: >-
  What an agent says of itself for a person, in the dictionary's words - what it observes and when
  the next reading is due, what it is doing - as prose by templates, each part answering its own
  section, published retained on the agent's account topic every pass it changes. Telemetry, never a
  belief; the translator relays it on a command and answers a question from it.
---

# What it is

An **account** is what an agent says of itself for a person: what it observes, each reading with
when the next is due and whether the sensor is doubted; what it is doing, each intention standing
with the want it pursues and the step it is at. It is prose by templates, not a document, and a
person reads it as it is. Each [part](/domain/kernel/part.md) answers its own section, `account()`,
duck-typed as `link`, `start` and `stop` are: sensing answers for its observations, execution for its
intentions, and a part with nothing to say has no such method. Planning's wants are owed and not yet
answered, since no world that chats holds a planner yet.

The account is **telemetry and never a belief**: no plan branches on what the agent said of itself,
so it is written nowhere in the store, and the package that gives it imports no package's words, as
history and metrics import none
([an-agent-gives-an-account-of-itself-and-the-model-only-reads-it](/decisions/an-agent-gives-an-account-of-itself-and-the-model-only-reads-it.md)).

# How it travels

An agent that is a [reporter](/domain/account/reporter.md) `account:accountsOn` a topic of the bus,
named `agents/<id>/account` by onboarding's rule and granted to the agent to write. The account part
hears the runtime's pass end, asks every part, and publishes the text **retained** when it differs
from the last — so a quiet agent costs the bus nothing, and a reader that restarts finds every
agent's latest without asking anybody. The payload is `{"account": text, "at": instant}`.

The [translator](/domain/speech/translator.md) standing in a [chat](/domain/speech/chat.md) with
the agent reads its account topic and keeps the latest. A person's words that state no sayable are a
question about the agent: `/account` is answered with the account as published, for nothing; any
other question goes to the model with the account and the question, to answer from the account
alone and say where it does not say. An agent that has given no account is said so, and no model is
asked.
