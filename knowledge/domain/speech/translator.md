---
type: Service
title: Translator
description: >-
  A process of the world standing between the people it names and its agents, with a language model
  at the edge and nowhere else - a person's prose made a statement of a sayable and published on their
  agent's inbox, a statement the agent says to them rendered as prose and sent to their address. It
  holds the model's key, which no agent image carries; the agent is unchanged, hearing the statement as
  any peer's document.
---

# What it is

`translation/` is a process of a world as the simulator is, `python -m translation <world>`: it reads
the world as an agent boots it, connects to the world's broker as the client the society names — the
one that `mqtt4ssn:hosts` the people it speaks for — and stands at the one run-time edge where a
model translates ([the-model-compiles-a-routine-and-is-called-back-at-its-edges](/decisions/the-model-compiles-a-routine-and-is-called-back-at-its-edges.md)).

**Who speaks with whom, through what, is the world's to say.** A [chat](/domain/speech/chat.md) names
an agent, a person and the channel their prose goes through; the translator stands in every chat the
client it connects as `translation:translates`. A person in a chat `mqtt4ssn:listensToTopic` an inbox,
where the agent's MQTT member publishes its statements to them as it publishes to any peer, and where
the translator reads them. Nothing here is a name in the code.

# A channel is what a chat goes through

The channel's type picks the carrier, and the translator knows none by name. Three kinds:

- **a topic of the bus**, `mqtt4ssn:Topic` — the person's user agent and the translator both publish
  prose on it; a message carries its speaker, so the translator drops what it said itself. The bus
  needs no service outside the world, so it is the channel a test walks end to end on the bench;
- **an email**, a `schema:ContactPoint` with a `schema:email` — polled and sent to over the standard
  library (`translation/carrier.py`), the mailbox being the translator's own;
- **a Telegram chat**, a `telegram:Chat` with the id the Bot API names it by and the bot it goes
  through — polled by `getUpdates` and sent to by `sendMessage` over the standard library, where the
  bot answers a deployment fact told as `TELEGRAM_URL` and its token the one secret, `TELEGRAM_BOT_TOKEN`. A person opens the chat by
  writing to the bot once; the id is then in `getUpdates`, and the sovereign states it in the world.

Each carrier's secret reaches the translator's container only where some chat goes through it.

# The two directions

- **Heard.** A person's words arrive — polled from their address, or as a message on the chat's
  topic, through the one door every message off the bus takes (`Translator.receive`); they go to the
  model with every [sayable](/domain/speech/sayable.md) the world declares as a tool, and the
  translator makes a statement of the one it filled and publishes it on the inbox of the chat's agent. There the agent's own transport hears it, [speech](/domain/speech/speech.md) keeps
  it as any peer's document, and the domain's [extraction](/domain/speech/extraction.md) makes the
  belief. The agent's [journal](/domain/kernel/journal.md) keeps the statement whole, the prose and
  who said it inside it.
- **Said.** What arrives on the person's inbox is the TriG an `execution:Saying` made. The translator
  finds the sayable it is a statement of, hands the model its fields and who it is for, and tells the
  words the model renders through the chat's channel — the mail carrier for an email, the bot for a
  Telegram chat, a publish on the topic for the bus. A statement of no sayable's class is not rendered: the agent said something the
  world gave no words for, said in the log.

# A question is answered from the account

Where the agent in a chat is a [reporter](/domain/account/reporter.md), the translator keeps its
latest [account](/domain/account/account.md) off the bus, and treats words that fill no sayable as
a question: the account page says what is relayed for nothing and what costs one model call. A
world that declares no sayable, the terrace, makes every message a question.

# What the model may and may not do

It fills a sayable's fields, or says none fits; it writes the words a statement is sent as; it
answers a question from an account it is handed. It authors
no belief, names no step, runs no query and reaches no agent but by a statement of a declared shape
marked another party's word. Which model and where is environment (`MODEL_NAME`, `MODEL_API_KEY`,
`MODEL_URL`), the key the installation's secret reaching this process alone; `tests/test_layout.py`
keeps the tree out of the agent image as it keeps onboarding out, and the import linter keeps the
agent from reaching for it.

# How it is onboarded

By the chats, and nothing listed by hand. Onboarding's topic rule names a person's inbox
`people/<person>/inbox` and a chat's topic `chats/<chat>`; `orexis-mqtt` grants the translating client,
off the chats, to read each person's inbox, write each agent's and read and write each topic, grants a
user agent the topics of whom it acts for, and grants the agent to write the inboxes of the people it
chats with; `orexis-compose` writes one `translation` service connected as the client, which mounts
this tree, the only one the image does not carry. Where the model answers is the installation's word
([deployment](/domain/onboarding/deployment.md)); which model and its key are a secret of the
installation's, each carrier's — the mailbox, `secrets/mail-<client>.env`, the bot's token,
`secrets/telegram-<client>.env` — one of the world's, written by hand and mounted only where a chat goes
through that carrier. What a
chat must state for all of that to be derived is the translator's own
[requirement](/domain/onboarding/requirement.md), `translation/requirements.ttl`.

# What stays open

Which person spoke is the carrier's word about an address, `speech:saidBy`, unsigned; signing is
speech's seam. The words the agent's statement was sent as are in this process's log and not in the
agent's journal.
