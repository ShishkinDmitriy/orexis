---
type: Decision
title: The model is briefed with the world the agent believes, and converses over its askables
status: accepted
timestamp: 2026-11-02T09:00:00Z
description: >-
  The sovereign's complaint of 2026-11-02, asking the terrace in its chat what plant it watches, how often
  it hears from its sensors and when the bed needs water - each answered with the latest readings, since
  the model could call one askable and the terrace held two. Decided - the model is briefed before the
  person's words with the self graph, the common beliefs with their vocabularies' comments and the status,
  and converses, calling as many askables over as many turns as the question needs. Refused - an askable
  per question, the whole store, and again the model writing the query.
---

# The question

[a-question-is-answered-and-every-other-act-is-kept](/decisions/a-question-is-answered-and-every-other-act-is-kept.md)
offered a person's words to the model in one call: it called the one sayable or askable the words made, or
said none fitted, and a second call phrased the rows. On the terrace that answered "which plant do you watch",
"how often do you hear from the probe" and "how is the bed" with the same thing, the latest reading of each
sensor, because sensing's askable was the one that took no field and the status was the fallback. The
answers were in the agent all along: the world says the bed is watched and not cared for, what each sensor is
mounted on, each cadence, the dry and wet bounds of the soil and how fast it dries. The model was simply
never shown them.

# What was decided

**The model is briefed.** Before the person's words it is handed a [briefing](/domain/translation/briefing.md):
the self graph, every common belief as Turtle with the store's prefixes - the world, the society, and the
vocabularies of the domains and packages, whose comments say what each term means - and the status. The first
two are cached together by the provider; the status follows them.

**And it converses.** The sayables and the askables are its tools, it calls as many as the question needs,
each askable answered from the store on the runtime's thread and its rows handed back as the call's result,
and it answers in words, the last of `TURNS` turns offering no tool. `nothing_fits` goes: a model that needs
no tool answers. The group's rule stands - unaddressed, the askables alone, and silence where they do not
answer.

The line of [an-agent-gives-an-account-of-itself-and-the-model-only-reads-it](/decisions/an-agent-gives-an-account-of-itself-and-the-model-only-reads-it.md)
holds: the model reads what the agent believes and what a package's select answers, and writes nothing the
agent reads.

# What was refused

- **An askable per question.** "Which bed", "how often", "what may a reading be" would each be a select some
  package ships, read off documents that do not change while the agent runs. A select to hand the model a
  sentence of `world.ttl` is a select for every sentence of it. The askables stay for what the agent holds
  NOW, which only the store answers.
- **The whole store.** Percepts, predictions and intentions grow with time and are what an askable bounds;
  the program - actions, drifts, desires, rules - is the agent's to run, not a belief about the world.
- **The model writing the query**, refused again for the reasons that record gave: free text to a query over
  the store, the `GRAPH` trap and an unbounded cost. A briefing hands the model the text a query would have
  read.

# What it costs

The terrace's briefing is some 70,000 characters, under 20,000 tokens, written to the provider's cache once
and read from it at a tenth of the price by every turn and question of the next minutes. A question costs one
turn more than its askables.

# Seams left open

- **What the world holds that the person keeps private** reaches the provider: the terrace's location is a
  belief in a document under `secrets/`, kept out of git and not out of the briefing.
- **A briefing that outgrows a prompt.** A world of many agents or domains would need the briefing narrowed to
  what the agent's own roles read; nothing measures where that is.
