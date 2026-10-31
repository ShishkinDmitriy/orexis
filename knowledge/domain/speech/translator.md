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

**Who it speaks for is the world's to say.** A person is a `schema:Person` in the society with the
`schema:email` the carrier reaches them at, the agent they `speech:speaksTo`, and the topic they
`mqtt4ssn:listensToTopic`: their inbox, where the agent's MQTT member publishes what the agent says to
them as it publishes to any peer. Nothing here is a name in the code.

# The two directions

- **Heard.** The carrier polls the person's address; their words go to the model with every
  [sayable](/domain/speech/sayable.md) the world declares as a tool, and the translator makes a
  statement of the one it filled and publishes it on the inbox of the agent the person speaks to.
  There the agent's own transport hears it, [speech](/domain/speech/speech.md) keeps it as any peer's
  document, and the domain's [extraction](/domain/speech/extraction.md) makes the belief. The agent's
  [journal](/domain/kernel/journal.md) keeps the statement whole, the prose and who said it inside it.
- **Said.** What arrives on the person's inbox is the TriG an `execution:Saying` made. The translator
  finds the sayable it is a statement of, hands the model its fields and who it is for, and sends the
  words the model renders to the person's address. A statement of no sayable's class is not rendered:
  the agent said something the world gave no words for, said in the log.

# What the model may and may not do

It fills a sayable's fields, or says none fits; it writes the words a statement is sent as. It authors
no belief, names no step, runs no query and reaches no agent but by a statement of a declared shape
marked another party's word. Which model and where is environment (`MODEL_NAME`, `MODEL_API_KEY`,
`MODEL_URL`), the key the installation's secret reaching this process alone; `tests/test_layout.py`
keeps the tree out of the agent image as it keeps onboarding out, and the import linter keeps the
agent from reaching for it.

# How it is onboarded

By the client hosting its people, and nothing listed by hand. Onboarding's topic rule names a
person's inbox `people/<person>/inbox`; `orexis-mqtt` grants that client, off the wiring, to read each
person's inbox and to write the inbox of the agent each `speech:speaksTo`, and grants the agent to
write the inbox of whoever speaks to it; `orexis-compose` writes one `translation` service connected
as the client, which mounts this tree, the only one the image does not carry. Where the model answers
is the installation's word ([deployment](/domain/onboarding/deployment.md)); which model and its key
are a secret of the installation's, the mailbox one of the world's, `secrets/mail-<client>.env`,
written by hand. What a person must state for all of that to be derived is the transport's
[requirement](/domain/onboarding/requirement.md).

# What stays open

Which person spoke is the carrier's word about an address, `speech:saidBy`, unsigned; signing is
speech's seam. The words the agent's statement was sent as are in this process's log and not in the
agent's journal.
