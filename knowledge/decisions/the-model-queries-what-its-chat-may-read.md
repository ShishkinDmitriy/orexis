---
type: Decision
title: The model queries what its chat may read, and the chat says what that is
status: accepted
timestamp: 2026-11-02T12:00:00Z
description: >-
  The sovereign's complaint of 2026-11-02 that the terrace answered which plant it watches, how often it
  hears from its sensors and when the bed needs water with its latest readings alike, and the ruling
  that what an agent can answer must not be a hardcoded list of questions, nor a chat with a broker
  read like a chat with an admin. Decided - a chat states the kinds of graph its model may read; the
  model loads the vocabularies it needs and writes SELECT and ASK queries over a copy of those graphs,
  reversing the refusal of the model writing SPARQL on three answers to its three premises. Refused - an
  askable per question, a briefing of every common belief, and the model choosing graphs.
---

# The question

[a-question-is-answered-and-every-other-act-is-kept](/decisions/a-question-is-answered-and-every-other-act-is-kept.md)
offered a person's words to the model in one call, which called one askable or said none fitted. The
terrace held two askables, so "which plant do you watch", "how often do you hear from the probe" and "how
is the bed" were all answered with the latest readings - though the world says the bed is watched and not
cared for, each cadence, and the soil's bounds and drying rate. A first answer briefed the model with every
common belief: 70,000 characters a question, most of it unread. The sovereign asked for the opposite - the
model choosing what to load and what to ask - and for the scope to differ by chat: a broker may not read what
the sovereign may.

# What was decided

**A chat says what its model may read.** `speech:reads` on a `speech:Chat` names kinds of graph, as an
askable's does: the terrace's chat with its sovereign reads `orexis:Graph`, everything; a broker's would read
the market's. The translator copies every graph of those kinds, in every store the agent holds, into one
default graph on the runtime's thread when the words arrive. A chat stating none reads nothing, and its model
has the askables alone; one stating some is offered only the askables reading within them.

**The model loads and queries.** The [briefing](/domain/translation/briefing.md) names the vocabularies the
chat may read and nothing more; `vocabulary` hands the model one as a glossary, a line per class and property with
the first sentence of its comment (whole Turtle was most of what a forecast question spent), and `query` runs
its SELECT or ASK over the copy, rows capped. It converses, calling as many tools over as many turns as the
message needs, and answers in words. The askables stay as the questions a package answers well.

# The refusal reversed

[an-agent-gives-an-account-of-itself-and-the-model-only-reads-it](/decisions/an-agent-gives-an-account-of-itself-and-the-model-only-reads-it.md)
refused the model writing SPARQL on three premises, each answered here:

- **Free text to action.** A SELECT or an ASK is no action. A text is parsed first, and anything else - an
  update, a CONSTRUCT - is refused before it runs; nothing the model reads becomes a belief.
- **The `GRAPH` trap.** The model never chooses a graph: the chat's graphs are merged into the copy's one
  default graph, and a `GRAPH`, `SERVICE` or `FROM` anywhere in the text is refused with the reason, so the
  model may write it again.
- **An unbounded cost.** The query runs on the model's thread over the copy, so a slow one never stalls a
  pass; its rows are capped at fifty; a conversation is `TURNS` turns at most.

The boundary is the chat's reads, which the world states and the code applies: whatever the model writes,
it reads nothing the chat does not.

# What was refused

- **An askable per question.** A select some package ships for "which bed", another for "how often" - a
  select per sentence of the world, and an agent that answers only what was foreseen.
- **A briefing of every common belief.** Built first, the same day: correct, and paid for by every message
  whether the question needed the climate vocabulary or not.
- **The model choosing graphs.** A `GRAPH` clause or a list of graphs to read would make the chat's reads a
  suggestion; merged into one copy, they are a wall.

# Seams left open

- **No timeout.** The engine takes none, so a pathological query occupies the model's thread until it ends; a
  pass is never held, but the person waits.
- **What a sovereign keeps private.** A chat reading everything reads the terrace's location, a belief under
  `secrets/`, and hands it to the model's provider if the model asks for it.
- **A copy per message.** Cheap at the terrace's size; an agent whose readable graphs run to millions of quads
  would want the copy kept between messages, or a view.
