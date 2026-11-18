---
type: Domain Concept
title: Style
term: http://example.org/orexis/translation#Style
description: >-
  How the agent writes to a person on a chat - what the model is told of writing there and how many
  messages one answer may be - translation's, since translation writes the words and a carrier only
  carries them. A chat may name its own; otherwise its channel's kind's holds.
---

# What it is

A style is a `translation:Style` with what the model is told of writing in it, `translation:guidance`, beside what
it is told of every answer, and how many messages one answer may be sent as, `translation:messagesAtMost`, one where
it says none. A chat is written in the style it names, `translation:writtenAs`, which the world states of a
`speech:Chat` for that chat alone; where it names none, in the style of its channel's kind, which translation's
ontology states of each kind of channel a member carries:

| A channel that is | Is written as | |
|---|---|---|
| a `telegram:Chat` | `translation:Chatty` | short lines as a person types on a phone, a long answer as a few messages, three at most |
| a topic of the bus, `mqtt4ssn:Topic` | `translation:Chatty` | |
| a `schema:ContactPoint`, a mailbox | `translation:Letter` | one message, a greeting by name, whole sentences, a closing signed by the agent |

So the carrier is the [chat](/domain/speech/chat.md)'s channel's type and the style follows it, and nothing below
translation learns a word of either: [speech](/domain/speech/speech.md) carries each message translation kept as
words of their own, through the one member API every carrier answers.

# What translation does with it

The [translator](/domain/translation/translator.md) reads each chat's style with the chat and hands the model the
guidance as a block of its own, before the instant, both when it answers a person and when it renders what the agent
says to one. Where the style lets an answer be several messages, the model is told to part them by a line holding
`---` alone; the answer is parted there, the empty parts dropped and the last taking what is past the style's most,
and each part is kept as a prose graph of its own and carried in turn, the first replying to what it answers. Where it
lets an answer be one, the words are sent as the model wrote them.
